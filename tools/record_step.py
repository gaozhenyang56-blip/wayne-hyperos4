#!/usr/bin/env python3
"""Run a project command and retain UTC times, arguments, output and exit code."""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import shlex
import os
from zoneinfo import ZoneInfo


def append_markdown(root, report, imported=False):
    """Every operation gets a human-readable timestamped entry as well as JSON."""
    start=datetime.datetime.fromisoformat(report['started_utc'])
    end=datetime.datetime.fromisoformat(report.get('finished_utc',report['started_utc']))
    display_zone=os.environ.get('WAYNE_PROGRESS_TIMEZONE','Asia/Shanghai')
    local=start.astimezone(ZoneInfo(display_zone))
    folder=root/'docs/operations';folder.mkdir(parents=True,exist_ok=True)
    target=root/os.environ['WAYNE_PROGRESS_FILE'] if os.environ.get('WAYNE_PROGRESS_FILE') else folder/(local.strftime('%Y-%m-%d')+'.md')
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():target.write_text('# 逐次操作日志\n\n时间显示为 '+display_zone+'，同时保留 UTC 审计时间。\n\n')
    if 'UTC 起始：'+start.isoformat() in target.read_text():
        return
    with target.open('a') as stream:
        stream.write('## '+local.isoformat()+' — '+report['label']+'\n\n')
        if imported:stream.write('依据已有 JSON 日志追记；以下为原始执行时间。\n\n')
        stream.write('UTC 起始：'+start.isoformat()+'；结束：'+end.isoformat()+'。\n\n')
        stream.write('做了什么：'+report.get('action', report['label'])+'\n\n')
        outcome=report.get('outcome') if report.get('exit_code')==0 else report.get('failure_note')
        stream.write('发生了什么：'+(outcome or ('该项操作完成。' if report.get('exit_code')==0 else '该项操作未完成，需要先定位失败原因。'))+'\n\n')
        stream.write('下一步：'+report.get('next_step','根据本项结果继续验证或修复；具体安排见最新进展。')+'\n\n')
        if report.get('output'):stream.write('证据：[原始日志](../../'+report['output']+')。\n\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--show-output', action='store_true')
    parser.add_argument('--action', help='Chinese description of what was done; required for new operations')
    parser.add_argument('--outcome', help='Observed result when the operation succeeds')
    parser.add_argument('--failure-note', help='Observed result when the operation fails')
    parser.add_argument('--next', dest='next_step', help='Concrete next step; required for new operations')
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
    for key in ('action','outcome','failure_note','next_step'):
        value=getattr(args,key,None)
        if value:report[key]=value
    output.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    append_markdown(root,report)
    if args.show_output:
        print(output.read_text(errors='replace')[-12000:])
    print(json.dumps(report, ensure_ascii=False))
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
