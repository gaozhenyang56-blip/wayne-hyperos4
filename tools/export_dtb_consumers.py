#!/usr/bin/env python3
"""Deterministic structural evidence, not authenticated device provenance."""
import argparse
import ctypes
from dataclasses import fields, is_dataclass
import json
import os
from pathlib import Path
import sys
import tempfile
from read_dtb_identity import read_tree, read_identity, MAX_SIZE
from dtb_consumer_evidence import collect_consumer_evidence

SCHEMA_VERSION = 'wayne.consumer-evidence.v1'
TOOL_VERSION = 'export-dtb-consumers/1'
MAX_EXPANDED_REG_TUPLES = 262144


def _plain(value):
    if is_dataclass(value):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, bytes): return value.hex()
    if isinstance(value, tuple): return [_plain(v) for v in value]
    return value


def canonical_bytes(blob):
    identity = read_identity(blob)
    normalized = identity['model'].lower().replace(' ', '')
    compatible = identity['compatible']
    if normalized not in ('mi6x', 'xiaomimi6x') or set(compatible) != {'xiaomi,wayne', 'qcom,sdm660'} or len(compatible) != 2:
        raise ValueError('root identity is not explicitly wayne/SDM660')
    tree = read_tree(blob)
    root = tree['nodes']['/']['properties']
    raw_identity = {name: {'structure_offset': root[name]['structure_offset'], 'value_offset': root[name]['value_offset'], 'length': root[name]['length'], 'hex': root[name]['hex'], 'decoded': identity[name]} for name in ('model','compatible')}
    consumers = collect_consumer_evidence(blob)
    if sum(len(target.reg) for consumer in consumers for target in consumer.targets) > MAX_EXPANDED_REG_TUPLES:
        raise ValueError('expanded reg evidence exceeds serialization limit')
    payload = {'schema_version': SCHEMA_VERSION, 'tool_version': TOOL_VERSION, 'input_sha256': tree['sha256'], 'root_identity': raw_identity, 'consumers': _plain(consumers), 'physical_source_authenticated': False, 'build_gate_authorization': False, 'hardware_tested': False}
    return (json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')


def _publish_no_replace(temp, output):
    # Linux atomic rename without overwriting a concurrently created evidence file.
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None: raise OSError('atomic no-replace rename unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(temp), -100, os.fsencode(output), 1):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def export(blob, output=None):
    payload = canonical_bytes(blob) # no filesystem write or stdout before complete validation
    if output is None: return payload
    output = Path(output)
    if output.is_symlink(): raise ValueError('symlink output refused')
    if output.exists():
        if output.read_bytes() != payload:
            raise ValueError('existing evidence differs; overwrite refused')
        return payload
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.'+output.name+'.', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        _publish_no_replace(temp, output)
    finally:
        if temp is not None: temp.unlink(missing_ok=True)
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dtb',type=Path); parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        with args.dtb.open('rb') as stream: blob=stream.read(MAX_SIZE+1)
        payload=export(blob,args.output)
        if args.output is None: sys.stdout.buffer.write(payload)
    except (ValueError,OSError) as error:
        parser.exit(2,'REJECT: '+str(error)+'\n')

if __name__=='__main__':main()
