#!/usr/bin/env python3
"""Read-only OTA inspection using HTTP ranges. Never flashes or patches images."""
import argparse
import io
import json
import pathlib
import struct
import urllib.request
import zipfile
import hashlib
import concurrent.futures


class RemoteFile(io.RawIOBase):
    def __init__(self, url):
        self.url = url
        self.pos = 0
        self.transferred = 0
        self.size = None
        self.range(0, 1)

    def range(self, start, length):
        if length > 1024 * 1024:
            spans = [(offset, min(1024 * 1024, start + length - offset))
                     for offset in range(start, start + length, 1024 * 1024)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                return b''.join(pool.map(lambda span: self.range(*span), spans))
        req = urllib.request.Request(self.url, headers={
            'Range': f'bytes={start}-{start + length - 1}',
            'Accept-Encoding': 'identity',
        })
        with urllib.request.urlopen(req, timeout=60) as response:
            if response.status != 206:
                raise ValueError('Server must honor Range; refusing whole-file fallback')
            content_range = response.headers.get('Content-Range', '')
            expected = f'bytes {start}-{start + length - 1}/'
            if not content_range.startswith(expected):
                raise ValueError(f'Unexpected Content-Range: {content_range}')
            size = int(content_range.split('/')[-1])
            if self.size is not None and self.size != size:
                raise ValueError('Remote file size changed')
            self.size = size
            data = response.read(length + 1)
        if len(data) != length:
            raise ValueError('Truncated or oversized HTTP range')
        self.transferred += length
        return data

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = [offset, self.pos + offset, self.size + offset][whence]
        if self.pos < 0:
            raise ValueError('Negative seek')
        return self.pos

    def read(self, length=-1):
        if length < 0:
            length = self.size - self.pos
        length = min(length, max(0, self.size - self.pos))
        if not length:
            return b''
        data = self.range(self.pos, length)
        self.pos += length
        return data


def varint(data, offset):
    value = 0
    for shift in range(0, 70, 7):
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, offset
    raise ValueError('Invalid protobuf varint')


def protobuf(data):
    """Decode wire fields, preserving repeated fields; schema stored in research/."""
    result = {}
    offset = 0
    while offset < len(data):
        key, offset = varint(data, offset)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, offset = varint(data, offset)
        elif wire == 2:
            length, offset = varint(data, offset)
            value = data[offset:offset + length]
            if len(value) != length:
                raise ValueError('Truncated protobuf field')
            offset += length
        elif wire in (1, 5):
            length = 8 if wire == 1 else 4
            value = data[offset:offset + length]
            if len(value) != length:
                raise ValueError('Truncated protobuf fixed field')
            offset += length
        else:
            raise ValueError(f'Unsupported protobuf wire type {wire}')
        result.setdefault(field, []).append(value)
    return result


def first(fields, number, default=None):
    return fields.get(number, [default])[0]


def inspect(url, output, extract_entries=()):
    output.mkdir(parents=True, exist_ok=True)
    remote = RemoteFile(url)
    report = {'url': url, 'zip_size': remote.size, 'status': 'inspection_only',
              'boot_tested': False, 'entries': [], 'metadata': {}}
    with zipfile.ZipFile(remote) as archive:
        for entry in archive.infolist():
            report['entries'].append({'name': entry.filename, 'size': entry.file_size,
                                      'compressed_size': entry.compress_size,
                                      'compression': entry.compress_type})
        for name in ('META-INF/com/android/metadata', 'payload_properties.txt',
                     'dynamic_partitions_op_list', 'META-INF/com/google/android/updater-script'):
            if name in archive.namelist():
                entry = archive.getinfo(name)
                if entry.file_size > 2 * 1024 * 1024:
                    raise ValueError('Metadata exceeds inspection limit')
                data = archive.read(name)
                (output / name.replace('/', '_')).write_bytes(data)
                report['metadata'][name] = data.decode('utf-8', errors='replace')
        for name in extract_entries:
            entry = archive.getinfo(name)
            if entry.file_size > 256 * 1024 * 1024:
                raise ValueError('ZIP extraction exceeds 256 MiB inspection limit')
            data = archive.read(name)  # zipfile verifies the entry CRC.
            target = output / pathlib.PurePosixPath(name).name
            target.write_bytes(data)
            report.setdefault('extracted', []).append({
                'entry': name, 'file': str(target), 'size': len(data),
                'sha256': hashlib.sha256(data).hexdigest(), 'zip_crc_verified': True})
        if 'payload.bin' in archive.namelist():
            entry = archive.getinfo('payload.bin')
            if entry.compress_type != zipfile.ZIP_STORED:
                raise ValueError('Range payload inspection needs ZIP_STORED')
            remote.seek(entry.header_offset)
            header = remote.read(30)
            name_length, extra_length = struct.unpack_from('<HH', header, 26)
            payload_offset = entry.header_offset + 30 + name_length + extra_length
            remote.seek(payload_offset)
            header = remote.read(24)
            magic, version, manifest_length, signature_length = struct.unpack('>4sQQI', header)
            if magic != b'CrAU' or version != 2:
                raise ValueError('Expected Android payload version 2')
            if manifest_length > 64 * 1024 * 1024:
                raise ValueError('Manifest exceeds inspection limit')
            raw = remote.read(manifest_length)
            properties = dict(line.split('=', 1) for line in
                              report['metadata'].get('payload_properties.txt', '').splitlines()
                              if '=' in line)
            import base64
            metadata_hash = hashlib.sha256(header + raw).digest()
            if int(properties.get('METADATA_SIZE', '-1')) != 24 + manifest_length:
                raise ValueError('Payload METADATA_SIZE mismatch')
            if properties.get('METADATA_HASH') != base64.b64encode(metadata_hash).decode():
                raise ValueError('Payload METADATA_HASH mismatch')
            (output / 'payload-manifest.pb').write_bytes(raw)
            fields = protobuf(raw)
            partitions = []
            for value in fields.get(13, []):
                part = protobuf(value)
                info = protobuf(first(part, 7, b''))
                operations = [protobuf(x) for x in part.get(8, [])]
                partitions.append({'name': first(part, 1).decode(),
                                   'size': first(info, 1),
                                   'sha256': first(info, 2, b'').hex(),
                                   'operation_count': len(operations),
                                   'operation_types': sorted({first(x, 1) for x in operations}),
                                   'payload_data_bytes': sum(first(x, 3, 0) for x in operations)})
            groups = []
            dynamic = protobuf(first(fields, 15, b''))
            for value in dynamic.get(1, []):
                group = protobuf(value)
                groups.append({'name': first(group, 1).decode(), 'size': first(group, 2),
                               'partitions': [x.decode() for x in group.get(3, [])]})
            report['payload'] = {'version': version, 'manifest_size': manifest_length,
                                 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                                 'metadata_hash_verified': True,
                                 'signature_verified': False,
                                 'metadata_signature_size': signature_length,
                                 'payload_offset_in_zip': payload_offset,
                                 'data_offset_in_zip': payload_offset + 24 + manifest_length + signature_length,
                                 'block_size': first(fields, 3, 4096),
                                 'dynamic_groups': groups, 'partitions': partitions,
                                 'snapshot_enabled': bool(first(dynamic, 2, 0)),
                                 'vabc_enabled': bool(first(dynamic, 3, 0)),
                                 'security_patch_level': first(fields, 18, b'').decode()}
    report['http_bytes_read'] = remote.transferred
    (output / 'inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: report[k] for k in ('zip_size', 'http_bytes_read', 'metadata')}, ensure_ascii=False, indent=2))
    if 'payload' in report:
        print(json.dumps(report['payload'], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('output', type=pathlib.Path)
    parser.add_argument('--extract-entry', action='append', default=[])
    args = parser.parse_args()
    inspect(args.url, args.output, args.extract_entry)
