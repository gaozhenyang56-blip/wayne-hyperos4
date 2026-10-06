#!/usr/bin/env python3
"""Reproducible static checks on the downloaded wayne/HyperOS4 material."""
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET


def audit(root):
    research = root / 'research'
    donor = json.loads((research / 'donor-dada-os4/inspection.json').read_text())
    base = json.loads((research / 'base-miku-a15/inspection.json').read_text())
    boot = json.loads((research / 'base-miku-a15/boot-inspection.json').read_text())
    vendor = research / 'base-miku-a15/vendor'
    system = research / 'donor-dada-os4/system/system'
    fcm = int(ET.parse(vendor / 'etc/vintf/manifest.xml').getroot().get('target-level'))
    matrices = {}
    for filename in (system / 'etc/vintf').glob('compatibility_matrix.*.xml'):
        matrix = ET.parse(filename).getroot()
        if matrix.get('level'):
            matrices[int(matrix.get('level'))] = sorted({k.get('version') for k in matrix.findall('kernel')})
    size_lines = base['metadata']['dynamic_partitions_op_list'].splitlines()
    group_size = int(next(line for line in size_lines if line.startswith('add_group ')).split()[2])
    vendor_size = int(next(line for line in size_lines if line.startswith('resize vendor ')).split()[2])
    parts = {x['name']: x for x in donor['payload']['partitions']}
    transplanted_names = ['system', 'system_ext', 'product', 'mi_ext']
    total = sum(parts[n]['size'] for n in transplanted_names) + vendor_size
    verified = []
    for name in ('init_boot', 'system', 'system_ext'):
        image = research / 'donor-dada-os4' / (name + '.img')
        with image.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != parts[name]['sha256'] or image.stat().st_size != parts[name]['size']:
            raise ValueError(f'{name} image failed SHA256/size verification')
        verified.append({'partition': name, 'size': image.stat().st_size, 'sha256': digest})
    policy_version = (vendor / 'etc/selinux/plat_sepolicy_vers.txt').read_text().strip()
    mapping_exists = (system / 'etc/selinux/mapping' / (policy_version + '.cil')).exists()
    result = {
        'status': 'NOT_PORTED', 'flashable_package_created': False,
        'real_device_testing': False, 'user_kernel_constraint': '4.19',
        'reference_kernel_banner': boot['kernel_banner'],
        'donor_build_metadata': donor['metadata']['META-INF/com/android/metadata'],
        'verified_donor_partition_hashes': verified,
        'fcm': {'vendor_target_level': fcm, 'donor_framework_levels': matrices,
                'vendor_level_matrix_present': fcm in matrices},
        'boot': {'reference_header_version': boot['header_version'],
                 'donor_init_boot_header_version': 4,
                 'donor_boot_partition_size': parts['boot']['size'],
                 'reference_boot_partition_max': 67108864},
        'capacity': {'reference_group_upper_bound': group_size,
                     'retained_vendor_size': vendor_size,
                     'proposed_donor_partitions': transplanted_names,
                     'unmodified_image_total': total,
                     'excess_bytes': max(0, total - group_size),
                     'actual_device_geometry_verified': False},
        'selinux': {'vendor_policy_version': policy_version,
                    'matching_platform_mapping_present': mapping_exists,
                    'combined_policy_compile_verified': False},
        'unresolved': [
            'FCM 5 support and legacy HAL compatibility in Android 17 framework',
            'Rebuild wayne boot v1 using the 4.19 device kernel and adapted Android 17 ramdisk',
            'Trim/rebuild product and mi_ext while retaining required framework and signed app dependencies',
            'Linker namespace access, exported symbols, graphics and camera ABI compatibility',
            'Compile merged SELinux policy and verify init services, encryption, APEX and BPF requirements',
        ],
        'limits': [
            'No full ROM ZIP downloaded or whole-ROM hash/signature verified; required entries/partitions were fetched by ranges',
            'Manifest metadata hash and extracted donor partition hashes verified, but OTA cryptographic signature not verified',
            'Library file existence is not proof of namespace, exported symbol or runtime compatibility',
            'FCM mismatch does not prove all possible 4.19 ports impossible; it rejects an unchanged image swap',
        ],
    }
    (root / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({key: result[key] for key in ('status', 'fcm', 'capacity', 'selinux')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    audit(pathlib.Path(__file__).resolve().parents[1])
