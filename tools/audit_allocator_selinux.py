#!/usr/bin/env python3
"""Record syntactic policy witnesses; never infer merged domain authorization."""
import datetime
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'research/selinux-allocator-stage'


def evidence(path, tokens):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest(),
            'lines': [{'line': number, 'text': line} for number, line in
                      enumerate(data.decode().splitlines(), 1) if any(t in line for t in tokens)]}


def main():
    platform = ROOT / 'downloads/verified-wayne-system/system/etc/selinux'
    raw = OUT / 'raw'
    context_tokens = ['/dev/dma_heap', '/dev/kgsl', '/dev/ion']
    policy_tokens = ['dmabuf_system_heap_device', 'ion_device', 'gpu_device']
    inputs = [evidence(platform/'plat_file_contexts', context_tokens),
              evidence(raw/'vendor_file_contexts', context_tokens)]
    for path in [platform/'plat_sepolicy.cil', raw/'vendor_sepolicy.cil', raw/'plat_pub_versioned.cil']:
        row = evidence(path, policy_tokens)
        row['lines'] = [r for r in row['lines'] if r['text'].startswith(
            ('(allow ', '(neverallow ', '(allowx ', '(neverallowx '))]
        inputs.append(row)
    # This is a direct rule witness, not attribute expansion or a policy merge.
    allocator = next(r for r in inputs[2]['lines'] if r['text'].startswith(
        '(allow hal_graphics_allocator dmabuf_system_heap_device (chr_file '))
    permissions = allocator['text'].split('(chr_file (', 1)[1].split(')', 1)[0].split()
    assert {'read', 'open', 'ioctl'} <= set(permissions) and 'write' not in permissions
    report = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'target': 'China Xiaomi Mi 6X wayne, static partitions; not jasmine or Miku UI',
              'evidence_scope': 'local experimental donor platform plus non-Miku wayne comparison vendor, NOT user current policy',
              'inputs': inputs, 'allocator_direct_rule': allocator,
              'fix': 'heap control FD O_RDONLY|O_CLOEXEC; allocation buffer fd_flags still O_RDWR|O_CLOEXEC',
              'required_control_permissions': ['read', 'open', 'ioctl'],
              'client_domain_known': False, 'current_vendor_policy_available': False,
              'avc_available': False, 'merged_neverallow_checked': False,
              'runtime_labels_verified': False, 'domain_access_verified': False,
              'historical_strict_policy_report': 'research/wayne-os4-policy/policy-check.json; unrelated historical pairing, still failed',
              'notes': ['system heap has an explicit platform dmabuf_system_heap_device label distinct from generic/secure heaps',
                        'comparison vendor explicitly labels kgsl-3d0 gpu_device; ION label unresolved in inspected context files',
                        'versioned 32.0 vendor attributes require matching platform mappings, not direct type substitution',
                        'neverallow/allowx and expanded attributes must be checked in an actual merged policy before authorization claims'],
              'policy_allows_added': False, 'permissive_enabled': False,
              'hardware_tested': False, 'bootable_verified': False}
    (OUT/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Policy witnesses saved; current client/domain and merged authorization remain UNKNOWN.')


if __name__ == '__main__':
    main()
