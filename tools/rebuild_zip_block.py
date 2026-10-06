#!/usr/bin/env python3
"""Stream a full uncompressed block OTA ZIP member into an analysis image."""
import argparse
import hashlib
import json
import pathlib
import zipfile


def rebuild(archive_path, data_name, transfer_name, output):
    with zipfile.ZipFile(archive_path) as archive:
        text = archive.read(transfer_name).decode()
        rows = text.splitlines()
        if rows[0] != '4':
            raise ValueError('Only v4 full block OTA is supported')
        operations, occupied = [], []
        for row in rows[4:]:
            command, encoded = row.split()
            values = [int(v) for v in encoded.split(',')]
            if command not in ('new', 'zero', 'erase'):
                raise ValueError('Incremental commands unsupported')
            if values[0] != len(values) - 1 or values[0] % 2:
                raise ValueError('Invalid ranges')
            for start, end in zip(values[1::2], values[2::2]):
                if not 0 <= start < end:
                    raise ValueError('Invalid extent')
                operations.append((command, start, end))
                occupied.append((start, end))
        ordered = sorted(occupied)
        if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
            raise ValueError('Overlapping ranges unsupported')
        size = max(end for _, end in occupied) * 4096
        expected = sum((end-start)*4096 for op, start, end in operations if op == 'new')
        if expected != archive.getinfo(data_name).file_size:
            raise ValueError('Transfer list does not match data member size')
        output.parent.mkdir(parents=True, exist_ok=True)
        part = output.with_suffix(output.suffix + '.part')
        with archive.open(data_name) as source, part.open('w+b') as target:
            target.truncate(size)
            for op, start, end in operations:
                target.seek(start * 4096)
                remaining = (end-start)*4096
                while remaining:
                    length = min(remaining, 1024*1024)
                    block = source.read(length) if op == 'new' else bytes(length)
                    if len(block) != length:
                        raise ValueError('Truncated data member')
                    target.write(block)
                    remaining -= length
            if source.read(1):
                raise ValueError('Unconsumed data')
            target.seek(0)
            digest = hashlib.file_digest(target, 'sha256').hexdigest()
        part.replace(output)
        (output.parent / (output.stem + '.transfer.list')).write_text(text)
        report = {'archive': str(archive_path), 'data_member': data_name,
                  'transfer_member': transfer_name, 'size': size, 'sha256': digest,
                  'zip_member_crc_verified': True, 'original_image_hash_verified': False,
                  'usage': 'offline_analysis'}
        output.with_suffix('.img.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=pathlib.Path)
    parser.add_argument('data_member')
    parser.add_argument('transfer_member')
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    rebuild(args.archive, args.data_member, args.transfer_member, args.output)
