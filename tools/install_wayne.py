#!/usr/bin/env python3
"""Verify or install the explicitly untested wayne retrofit-dynamic candidate."""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys


GROUP_LIMIT = 6241120256


def verify_images(root):
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('device') != 'wayne' or manifest.get('layout') != 'miku-wayne-retrofit-dynamic':
        raise ValueError('This package is not a supported wayne retrofit-dynamic package')
    images = manifest.get('images', {})
    if set(images) != {'boot.img', 'system.img', 'vendor.img'}:
        raise ValueError('Expected exactly boot, system and target vendor images')
    for name, record in images.items():
        path = root/name
        if path.stat().st_size != record['size']:
            raise ValueError('Wrong image size: '+name)
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != record['sha256']:
            raise ValueError('SHA-256 mismatch: '+name)
    if images['boot.img']['size'] > 67108864:
        raise ValueError('Boot image exceeds the reference wayne boot partition')
    if images['system.img']['size']+images['vendor.img']['size'] > GROUP_LIMIT:
        raise ValueError('Images exceed the reference dynamic partition group')
    return manifest


class Fastboot:
    def __init__(self, binary, serial):
        self.command = [binary]+(['-s', serial] if serial else [])

    def run(self, *args):
        result = subprocess.run(self.command+list(args), capture_output=True, text=True,
                                timeout=900)
        output = result.stdout+result.stderr
        if result.returncode:
            raise RuntimeError('fastboot '+ ' '.join(args)+' failed:\n'+output)
        return output

    def getvar(self, name):
        output = self.run('getvar', name)
        match = re.search(r'(?m)^\s*(?:\(bootloader\)\s*)?'+re.escape(name)+r':\s*([^\r\n]+)', output)
        if not match:
            raise RuntimeError('Missing fastboot variable: '+name)
        return match.group(1).strip()


def number(value):
    return int(value, 16) if value.lower().startswith('0x') else int(value, 10)


def make_plan(fastboot, manifest, root):
    expected = {'product': 'wayne', 'is-userspace': 'yes', 'super-partition-name': 'system',
                'is-logical:system': 'yes', 'is-logical:vendor': 'yes', 'is-logical:boot': 'no'}
    for name, value in expected.items():
        actual = fastboot.getvar(name)
        if actual != value:
            raise ValueError(f'Unsupported device/layout: {name}={actual}, expected {value}')
    images = manifest['images']
    if number(fastboot.getvar('partition-size:boot')) < images['boot.img']['size']:
        raise ValueError('Actual boot partition is too small')
    # Keep existing product/system_ext allocations; the new boot mounts merged copies.
    existing_other = sum(number(fastboot.getvar('partition-size:'+name))
                         for name in ('product', 'system_ext'))
    if images['system.img']['size']+images['vendor.img']['size']+existing_other > GROUP_LIMIT:
        raise ValueError('Existing product/system_ext allocations leave insufficient group space')
    # No mutation occurs before all local checks and every device query have passed.
    return [('resize-logical-partition', 'system', str(images['system.img']['size'])),
            ('resize-logical-partition', 'vendor', str(images['vendor.img']['size'])),
            ('flash', 'system', str(root/'system.img')),
            ('flash', 'vendor', str(root/'vendor.img')),
            ('flash', 'boot', str(root/'boot.img'))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true', help='Only verify package images; no device needed')
    parser.add_argument('--flash', action='store_true', help='Install the explicitly untested candidate in fastbootd')
    parser.add_argument('--serial', help='Target fastboot serial number')
    parser.add_argument('--fastboot', default='fastboot')
    args = parser.parse_args()
    if args.flash and args.verify_only:
        parser.error('--flash and --verify-only are mutually exclusive')
    root = pathlib.Path(__file__).resolve().parent
    manifest = verify_images(root)
    print('Package SHA-256 checks passed. Status: offline experimental, no device boot test.')
    if not args.flash:
        return
    fastboot = Fastboot(args.fastboot, args.serial)
    plan = make_plan(fastboot, manifest, root)
    for command in plan:
        print('Running:', ' '.join(command), flush=True)
        print(fastboot.run(*command), flush=True)
    print('Images written. Device remains in fastbootd; boot and hardware behavior are unverified.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
