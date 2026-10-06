#!/usr/bin/env python3
"""Inspect Android boot v0-v4 images and extract regular ramdisk files only."""
import argparse
import gzip
import hashlib
import json
import pathlib
import struct
import zlib


def decode_ramdisk(data):
    if data.startswith(b'\x1f\x8b'):
        return gzip.decompress(data)
    if data[:4] == bytes.fromhex('02214c18'):
        import lz4.block
        offset = 4
        result = bytearray()
        while offset + 4 <= len(data):
            length = struct.unpack_from('<I', data, offset)[0]
            offset += 4
            if not length:
                break
            if offset + length > len(data):
                raise ValueError('Truncated legacy LZ4 block')
            result.extend(lz4.block.decompress(data[offset:offset + length],
                                               uncompressed_size=8 * 1024 * 1024))
            offset += length
        return bytes(result)
    raise ValueError('Unsupported ramdisk compression')


def unpack(image, output):
    data = image.read_bytes()
    if data[:8] != b'ANDROID!':
        raise ValueError('Android boot magic missing')
    version = struct.unpack_from('<I', data, 40)[0]
    if version > 4:
        raise ValueError('Unsupported boot header')
    output.mkdir(parents=True, exist_ok=True)
    kernel_size = struct.unpack_from('<I', data, 8)[0]
    if version < 3:
        ramdisk_size = struct.unpack_from('<I', data, 16)[0]
        page = struct.unpack_from('<I', data, 36)[0]
    else:
        ramdisk_size = struct.unpack_from('<I', data, 12)[0]
        page = 4096
    if page not in (2048, 4096, 8192, 16384):
        raise ValueError('Unsupported page size')
    kernel = data[page:page + kernel_size]
    offset = page + ((kernel_size + page - 1) // page) * page
    ramdisk = data[offset:offset + ramdisk_size]
    if len(kernel) != kernel_size or len(ramdisk) != ramdisk_size:
        raise ValueError('Truncated boot image')
    report = {'image': str(image), 'sha256': hashlib.sha256(data).hexdigest(),
              'header_version': version, 'kernel_size': kernel_size,
              'ramdisk_size': ramdisk_size, 'page_size': page, 'entries': []}
    if kernel:
        (output / 'kernel.gz-dtb').write_bytes(kernel)
        uncompressed = zlib.decompress(kernel, 31)
        start = uncompressed.find(b'Linux version ')
        if start >= 0:
            report['kernel_banner'] = uncompressed[start:uncompressed.find(b'\0', start)].decode(errors='replace')
            (output / 'kernel-version.txt').write_text(report['kernel_banner'])
    (output / 'ramdisk.bin').write_bytes(ramdisk)
    archive = decode_ramdisk(ramdisk)
    offset = 0
    while offset + 110 <= len(archive):
        header = archive[offset:offset + 110]
        offset += 110
        if header[:6] not in (b'070701', b'070702'):
            raise ValueError('Unsupported CPIO format')
        fields = [int(header[6 + i * 8:14 + i * 8], 16) for i in range(13)]
        mode, size, name_size = fields[1], fields[6], fields[11]
        name = archive[offset:offset + name_size - 1].decode()
        offset = (offset + name_size + 3) & ~3
        content = archive[offset:offset + size]
        offset = (offset + size + 3) & ~3
        if name == 'TRAILER!!!':
            break
        if len(content) != size:
            raise ValueError('Truncated CPIO file')
        if name.startswith('/') or '..' in pathlib.PurePosixPath(name).parts:
            raise ValueError('Unsafe CPIO path')
        report['entries'].append({'name': name, 'mode': oct(mode), 'size': size})
        if mode & 0o170000 == 0o100000:
            target = output / 'ramdisk' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    (output / 'boot-inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'entries'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    unpack(args.image, args.output)
