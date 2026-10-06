#!/usr/bin/env python3
"""Safety regressions for installation planning; never accesses a real device."""
import hashlib
import json
import pathlib
import tempfile
import unittest
from install_wayne import make_plan, verify_images


class DeviceFixture:
    def __init__(self, **changes):
        self.values = {'product':'wayne', 'is-userspace':'yes', 'super-partition-name':'system',
                       'is-logical:system':'yes', 'is-logical:vendor':'yes', 'is-logical:boot':'no',
                       'partition-size:boot':'0x4000000', 'partition-size:product':'344276992',
                       'partition-size:system_ext':'232849408'}
        self.values.update(changes)
        self.queries = []

    def getvar(self, name):
        self.queries.append(name)
        return self.values[name]

    def run(self, *args):
        raise AssertionError('Planning must not write to a device')


class InstallerChecks(unittest.TestCase):
    def setUp(self):
        self.manifest = {'images':{'boot.img':{'size':18755584},
                                   'system.img':{'size':2940682240},
                                   'vendor.img':{'size':209600512}}}

    def test_only_intended_partitions_are_written(self):
        fixture = DeviceFixture()
        plan = make_plan(fixture, self.manifest, pathlib.Path('/package'))
        self.assertEqual([row[1] for row in plan if row[0]=='flash'], ['system','vendor','boot'])
        self.assertIn('partition-size:system_ext', fixture.queries)

    def test_wrong_device_is_rejected(self):
        with self.assertRaises(ValueError):
            make_plan(DeviceFixture(product='dada'), self.manifest, pathlib.Path('/package'))

    def test_bootloader_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            make_plan(DeviceFixture(**{'is-userspace':'no'}), self.manifest, pathlib.Path('/package'))

    def test_non_retrofit_layout_is_rejected(self):
        with self.assertRaises(ValueError):
            make_plan(DeviceFixture(**{'super-partition-name':'super'}), self.manifest, pathlib.Path('/package'))

    def test_group_space_shortage_is_rejected(self):
        with self.assertRaises(ValueError):
            make_plan(DeviceFixture(**{'partition-size:product':'6000000000'}),
                      self.manifest, pathlib.Path('/package'))

    def test_actual_boot_size_is_checked(self):
        with self.assertRaises(ValueError):
            make_plan(DeviceFixture(**{'partition-size:boot':'0x1000'}),
                      self.manifest, pathlib.Path('/package'))

    def test_corrupted_image_is_rejected_before_device_access(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            manifest={'device':'wayne','layout':'miku-wayne-retrofit-dynamic','images':{}}
            for name in ('boot.img','system.img','vendor.img'):
                content=(name+' fixture').encode();(root/name).write_bytes(content)
                manifest['images'][name]={'size':len(content),'sha256':hashlib.sha256(content).hexdigest()}
            (root/'manifest.json').write_text(json.dumps(manifest))
            verify_images(root)
            original=(root/'system.img').read_bytes()
            (root/'system.img').write_bytes(b'X'+original[1:])
            with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
                verify_images(root)


if __name__=='__main__':
    unittest.main()
