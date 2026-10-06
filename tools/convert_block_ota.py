#!/usr/bin/env python3
"""Reconstruct a v4 full block OTA image; never modifies device partitions."""
import argparse
import hashlib
import json
import pathlib
import brotli


def convert(data_file, transfer_file, size, target):
    lines = transfer_file.read_text().splitlines()
    if lines[0] != '4':
        raise ValueError('Only transfer-list version 4 supported')
    data = brotli.decompress(data_file.read_bytes())
    offset = 0
    temporary = target.with_suffix(target.suffix + '.part')
    with temporary.open('w+b') as out:
        out.truncate(size)
        for line in lines[4:]:
            command, encoded = line.split(' ', 1)
            ranges = [int(x) for x in encoded.split(',')]
            if ranges[0] != len(ranges) - 1 or ranges[0] % 2:
                raise ValueError('Invalid transfer ranges')
            if command not in ('new', 'zero', 'erase'):
                raise ValueError('Incremental OTA operations are unsupported')
            for start, end in zip(ranges[1::2], ranges[2::2]):
                if not 0 <= start <= end or end * 4096 > size:
                    raise ValueError('Extent exceeds image')
                length = (end - start) * 4096
                out.seek(start * 4096)
                if command == 'new':
                    block = data[offset:offset + length]
                    if len(block) != length:
                        raise ValueError('Truncated block data')
                    out.write(block)
                    offset += length
                else:
                    out.write(bytes(length))
        if offset != len(data):
            raise ValueError('Unconsumed block data')
        out.seek(0)
        sha256 = hashlib.file_digest(out, 'sha256').hexdigest()
    temporary.replace(target)
    record = {'size': size, 'sha256': sha256, 'source': str(data_file),
              'original_image_sha256_verified': False,
              'purpose': 'analysis_only'}
    target.with_suffix(target.suffix + '.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=pathlib.Path)
    parser.add_argument('transfer', type=pathlib.Path)
    parser.add_argument('size', type=int)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    convert(args.data, args.transfer, args.size, args.output)
