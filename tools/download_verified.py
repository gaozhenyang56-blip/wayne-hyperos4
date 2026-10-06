#!/usr/bin/env python3
"""Bounded HTTP range download with complete-file SHA256 verification."""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
from inspect_ota import RemoteFile


def download(url, target, expected_hash):
    remote = RemoteFile(url)
    temporary = target.with_suffix(target.suffix + '.part')
    target.parent.mkdir(parents=True, exist_ok=True)
    step = 4 * 1024 * 1024
    count = (remote.size + step - 1) // step
    with temporary.open('w+b') as output, concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        output.truncate(remote.size)
        for index in range(0, count, 16):
            spans = [(i * step, min(step, remote.size - i * step)) for i in range(index, min(count, index + 16))]
            blocks = pool.map(lambda span: remote.range(*span), spans)
            for span, block in zip(spans, blocks):
                output.seek(span[0])
                output.write(block)
            written = min(remote.size, (index + len(spans)) * step)
            print(json.dumps({'downloaded': written, 'total': remote.size, 'percent': round(written / remote.size * 100, 1)}), flush=True)
        output.seek(0)
        actual_hash = hashlib.file_digest(output, 'sha256').hexdigest()
        if actual_hash.lower() != expected_hash.lower():
            raise ValueError('Complete ZIP SHA256 mismatch; keeping .part for investigation')
    temporary.replace(target)
    record = {'url': url, 'size': remote.size, 'sha256': actual_hash, 'complete_file_sha256_verified': True,
              'signature_verified': False, 'hash_source': 'user-supplied expected hash / public download-provider metadata'}
    target.with_suffix(target.suffix + '.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('output', type=pathlib.Path)
    parser.add_argument('sha256')
    args = parser.parse_args()
    download(args.url, args.output, args.sha256)
