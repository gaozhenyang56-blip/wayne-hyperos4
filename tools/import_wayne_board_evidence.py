#!/usr/bin/env python3
"""Validate local evidence claims; never authorize a build or authenticate hardware."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from read_dtb_identity import MAX_SIZE, read_identity


def validate(manifest):
    manifest = Path(manifest).resolve()
    data = json.loads(manifest.read_text())
    source = data['source']
    if data.get('role') not in ('actual_device_capture', 'synthetic_fixture'):
        raise ValueError('unknown evidence role/source')
    for key in ('description', 'collection_command', 'collected_at'):
        if not isinstance(source.get(key), str) or source[key].strip().lower() in ('', 'unknown', 'n/a'):
            raise ValueError('unknown source: ' + key)
    stamp = datetime.datetime.fromisoformat(source['collected_at'])
    if stamp.tzinfo is None:
        raise ValueError('collection timestamp needs timezone')
    if source.get('device') != 'wayne' or source.get('region') != 'China' or source.get('partition_layout') != 'stock_static':
        raise ValueError('source target mismatch')
    if not isinstance(data.get('files'), list) or not data['files']:
        raise ValueError('missing evidence files')
    records = []
    for item in data['files']:
        path = (manifest.parent / item['path']).resolve()
        if not path.is_relative_to(manifest.parent) or not path.is_file():
            raise ValueError('missing file or path escapes evidence directory')
        if item["kind"] == "dtb" and path.stat().st_size > MAX_SIZE:
            raise ValueError("DTB exceeds bounded size")
        if item["kind"] == "dtb":
            with path.open("rb") as stream:
                blob = stream.read(MAX_SIZE + 1)
            if len(blob) > MAX_SIZE:
                raise ValueError("DTB exceeds bounded size")
        else:
            blob = path.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        if not blob or item.get('sha256') != digest:
            raise ValueError('empty file or hash mismatch')
        if item['kind'] == 'getprop':
            fields = {}
            for line in blob.decode('utf-8').splitlines():
                match = re.fullmatch(r'\[([^]]+)\]: \[(.*)\]', line)
                if match:
                    if match[1] in fields:
                        raise ValueError('duplicate property')
                    fields[match[1]] = match[2]
            if fields.get('ro.product.device') != 'wayne':
                raise ValueError('device mismatch')
            model = fields.get('ro.product.model', '')
            identity = [value for key, value in fields.items() if key.endswith('.device') or key.endswith('.model') or key.endswith('.fingerprint')]
            if any('jasmine' in v.lower() or 'mi a2' in v.lower() for v in identity):
                raise ValueError('foreign identity/masquerade')
            for key, value in fields.items():
                if key.startswith('ro.product.') and key.endswith('.device') and value != 'wayne':
                    raise ValueError('inconsistent product device identities')
        elif item['kind'] == 'dtb':
            tool = shutil.which('fdtget')
            if tool:
                def prop(name):
                    result = subprocess.run([tool, '-t', 's', str(path), '/', name], capture_output=True, text=True, check=True, timeout=5)
                    return result.stdout.strip()
                fields = {'model': prop('model'), 'compatible': prop('compatible').split(), 'identity_reader': 'fdtget'}
            else:
                fields = read_identity(blob)
                fields['identity_reader'] = 'bounded_python_v17'
            model = fields['model']
            if 'xiaomi,wayne' not in fields['compatible'] or 'qcom,sdm660' not in fields['compatible'] or any('jasmine' in c.lower() for c in fields['compatible']):
                raise ValueError('compatible mismatch/foreign identity')
        else:
            raise ValueError('unsupported evidence kind; boot/DTBO not yet parsed')
        if model.lower().replace(' ', '') not in ('mi6x', 'xiaomimi6x'):
            raise ValueError('model inconsistent with wayne')
        records.append({'path': item['path'], 'kind': item['kind'], 'sha256': digest, 'size': len(blob), 'parsed_fields': fields})
    return {'source': source, 'role': data['role'], 'files': records, 'scope': 'local_claim_consistency_only', 'physical_identity_verified': False, 'board_bindings_verified': False, 'build_gate_authorization': False, 'hardware_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.manifest), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        parser.exit(2, 'REJECT: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
