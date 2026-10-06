#!/usr/bin/env python3
"""Run a project command and retain UTC times, arguments, output and exit code."""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        parser.error('command required')
    root = pathlib.Path(__file__).resolve().parent.parent
    start = datetime.datetime.now(datetime.timezone.utc)
    safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in args.label)
    stem = start.strftime('%Y%m%dT%H%M%S%fZ') + '-' + safe
    output = root / 'logs' / (stem + '.log')
    output.parent.mkdir(exist_ok=True)
    with output.open('wb') as log:
        result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    report = {'label': args.label, 'started_utc': start.isoformat(),
              'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'cwd': str(root), 'command': command, 'exit_code': result.returncode,
              'output': str(output.relative_to(root)),
              'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
