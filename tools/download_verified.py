#!/usr/bin/env python3
"""Bounded HTTP range download with complete-file SHA256 verification."""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import time
from inspect_ota import RemoteFile


def bounded(operation, label):
    for attempt in range(5):
        try:
            return operation()
        except (OSError, ValueError) as error:
            if attempt == 4:
                raise
            print(json.dumps({'retry':label,'attempt':attempt+1,'error':str(error)}),flush=True)
            time.sleep(min(2 ** attempt, 8))


def download(url, target, expected_hash):
    remote = bounded(lambda: RemoteFile(url), 'initial range probe')
    temporary = target.with_suffix(target.suffix + '.part')
    target.parent.mkdir(parents=True, exist_ok=True)
    step = 1024 * 1024
    count = (remote.size + step - 1) // step
    def fetch(span):
        return bounded(lambda: remote.range(*span), str(span[0]))
    with temporary.open('w+b') as output, concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        output.truncate(remote.size)
        for index in range(0, count, 16):
            spans = [(i * step, min(step, remote.size - i * step)) for i in range(index, min(count, index + 16))]
            blocks = pool.map(fetch, spans)
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
