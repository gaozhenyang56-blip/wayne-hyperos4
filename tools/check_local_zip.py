#!/usr/bin/env python3
"""Hash a local ZIP and check every member CRC before extracting a boot sample."""
import argparse
import hashlib
import json
import pathlib
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    digest = hashlib.sha256()
    with args.zip.open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    with zipfile.ZipFile(args.zip) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError('ZIP CRC failure: ' + bad)
        args.output.mkdir(parents=True, exist_ok=True)
        if 'boot.img' in archive.namelist():
            (args.output / 'boot.img').write_bytes(archive.read('boot.img'))
        report = {'file': str(args.zip), 'size': args.zip.stat().st_size,
                  'sha256': digest.hexdigest(), 'all_entries_crc_verified': True,
                  'publisher_hash_verified': False, 'signature_verified': False,
                  'entries': len(archive.infolist())}
        (args.output / 'local-zip-check.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report))


if __name__ == '__main__':
    main()
