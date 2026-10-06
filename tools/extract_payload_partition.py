#!/usr/bin/env python3
"""Extract a full-OTA partition for analysis; verify operation and image hashes."""
import argparse
import bz2
import hashlib
import json
import lzma
import pathlib
import concurrent.futures
from inspect_ota import RemoteFile, protobuf, first


def extract(inspection, name, target):
    report = json.loads((inspection / 'inspection.json').read_text())
    manifest = protobuf((inspection / 'payload-manifest.pb').read_bytes())
    matches = [protobuf(x) for x in manifest.get(13, [])
               if first(protobuf(x), 1).decode() == name]
    if len(matches) != 1:
        raise ValueError('Partition not uniquely present')
    part = matches[0]
    info = protobuf(first(part, 7))
    size = first(info, 1)
    operations = [protobuf(x) for x in part.get(8, [])]
    if any(first(x, 1) not in (0, 1, 6, 7, 8) for x in operations):
        raise ValueError('Only full-image REPLACE/BZ/XZ/ZERO/DISCARD are supported')
    block_size = first(manifest, 3, 4096)
    remote = RemoteFile(report['url'])
    payload = report['payload']
    temporary = target.with_suffix(target.suffix + '.part')
    target.parent.mkdir(parents=True, exist_ok=True)
    def decode(operation):
        kind = first(operation, 1)
        extents = [protobuf(x) for x in operation.get(6, [])]
        expected_size = sum(first(x, 2) * block_size for x in extents)
        if kind in (6, 7):
            data = bytes(expected_size)
        else:
            offset = payload['data_offset_in_zip'] + first(operation, 2, 0)
            encoded = remote.range(offset, first(operation, 3))
            expected_hash = first(operation, 8)
            if expected_hash is not None and hashlib.sha256(encoded).digest() != expected_hash:
                raise ValueError('Operation data SHA256 mismatch')
            data = bz2.decompress(encoded) if kind == 1 else lzma.decompress(encoded) if kind == 8 else encoded
        if len(data) != expected_size:
            raise ValueError('Extent size mismatch')
        return extents, data
    with temporary.open('w+b') as out:
        out.truncate(size)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            # Submit in bounded batches to avoid buffering an entire large image.
            for start_operation in range(0, len(operations), 16):
                for extents, data in pool.map(decode, operations[start_operation:start_operation + 16]):
                    position = 0
                    for extent in extents:
                        start = first(extent, 1) * block_size
                        length = first(extent, 2) * block_size
                        if start + length > size:
                            raise ValueError('Extent exceeds target image')
                        out.seek(start)
                        out.write(data[position:position + length])
                        position += length
        out.seek(0)
        digest = hashlib.file_digest(out, 'sha256').digest()
        if digest != first(info, 2):
            raise ValueError('Final partition SHA256 mismatch')
    temporary.replace(target)
    record = {'partition': name, 'size': size, 'sha256': digest.hex(),
              'payload_operation_hashes_verified': True, 'partition_hash_verified': True,
              'ota_signature_verified': False, 'http_bytes_read': remote.transferred,
              'source_url': report['url'], 'purpose': 'analysis_only_do_not_flash'}
    target.with_suffix(target.suffix + '.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inspection', type=pathlib.Path)
    parser.add_argument('partition')
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    extract(args.inspection, args.partition, args.output)
