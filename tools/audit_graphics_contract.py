#!/usr/bin/env python3
"""Read-only graphics ABI evidence. A clean scan is never a boot verdict."""
import argparse
import hashlib
import io
import json
import pathlib
import re
from elftools.elf.elffile import ELFFile


def collect(root, manifest):
    rows = []
    for item in manifest['extracted']:
        path = root / item['path']
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Sample hash changed: ' + item['path'])
        if not data.startswith(b'\x7fELF'):
            continue
        elf = ELFFile(io.BytesIO(data))
        dynamic = elf.get_section_by_name('.dynamic')
        needed = [t.needed for t in dynamic.iter_tags() if t.entry.d_tag == 'DT_NEEDED'] if dynamic else []
        refs = sorted({x.decode(errors='replace') for x in re.findall(rb'/(?:dev|sys)/[^\x00\s]{1,150}', data)
                       if any(k in x for k in (b'kgsl', b'/ion', b'dma_heap', b'/dri/', b'graphics/fb'))})
        rows.append({**item, 'elf_class': elf.elfclass, 'machine': elf['e_machine'],
                     'needed': needed, 'device_path_strings': refs})
    if not rows:
        raise ValueError('No ELF graphics evidence')
    return rows


def assess(rows, profile):
    findings = []
    patterns = {'kgsl': 'kgsl', 'ion': '/dev/ion', 'msm_fb': 'graphics/fb'}
    for abi, pattern in patterns.items():
        witnesses = [r['path'] for r in rows if any(pattern in x for x in r['device_path_strings'])]
        if witnesses and not profile['provided_legacy_abis'].get(abi, False):
            findings.append({'abi': abi, 'files': witnesses, 'status': 'requires_port_or_replacement'})
    return {'profile': profile['id'], 'findings': findings,
            'legacy_pairing_rejected': bool(findings),
            'evidence_kind': 'ELF strings and dynamic dependencies; no ioctl execution',
            'compatible_verified': False, 'hardware_tested': False,
            'remaining': ['gralloc buffer-handle layout and modifiers', 'fences and cache coherency',
                          'secure/protected heaps', 'SELinux device and service policy',
                          '32/64-bit graphics loading', 'wayne-specific display/boot bringup']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('vendor', type=pathlib.Path)
    p.add_argument('manifest', type=pathlib.Path)
    p.add_argument('profile', type=pathlib.Path)
    p.add_argument('output', type=pathlib.Path)
    p.add_argument('--reject-legacy-pairing', action='store_true')
    args = p.parse_args()
    rows = collect(args.vendor, json.loads(args.manifest.read_text()))
    report = {'sample_role': 'non-Miku wayne ROM comparison only; not user current vendor',
              'graphics_files': rows,
              'contract': assess(rows, json.loads(args.profile.read_text()))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['contract'], indent=2))
    if args.reject_legacy_pairing and report['contract']['legacy_pairing_rejected']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
