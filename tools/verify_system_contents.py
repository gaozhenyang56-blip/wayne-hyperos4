#!/usr/bin/env python3
"""Compare all regular files and symlink targets after a rootless image rebuild."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import stat
import tarfile


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'rebuilt', 'metadata', 'overlay', 'report'):
        parser.add_argument(name, type=pathlib.Path)
    args = parser.parse_args()
    records = json.loads(args.metadata.read_text())['paths']
    with tarfile.open(args.overlay) as archive:
        patches = {entry.name: hashlib.sha256(archive.extractfile(entry).read()).hexdigest()
                   for entry in archive if entry.isfile()}

    def compare(pair):
        name, record = pair
        source, rebuilt = args.source/name, args.rebuilt/name
        try:
            if stat.S_IFMT(rebuilt.lstat().st_mode) != stat.S_IFMT(record['mode']):
                return {'path': name, 'error': 'type mismatch'}
            if stat.S_ISREG(record['mode']):
                expected = patches.get(name) or digest(source)
                if digest(rebuilt) != expected:
                    return {'path': name, 'error': 'content mismatch'}
            elif stat.S_ISLNK(record['mode']) and os.readlink(source) != os.readlink(rebuilt):
                return {'path': name, 'error': 'symlink target mismatch'}
        except OSError as error:
            return {'path': name, 'error': str(error)}
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        failures = [result for result in pool.map(compare, records.items()) if result]
    added = sorted(set(patches)-set(records))
    for name in added:
        if digest(args.rebuilt/name) != patches[name]:
            failures.append({'path': name, 'error': 'new overlay content mismatch'})
    report = {'checked_original_paths': len(records), 'expected_modified_files': sorted(patches),
              'added_paths': added, 'failures': failures, 'success': not failures}
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['success'] else 1)


if __name__ == '__main__':
    main()
