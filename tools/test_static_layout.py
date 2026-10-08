#!/usr/bin/env python3
"""Exercise transformations on real reference inputs and invalid fixtures."""
import pathlib
import unittest
from static_wayne_layout import static_fstab,static_cmdline,static_vendor_properties

ROOT=pathlib.Path(__file__).resolve().parent.parent
REFERENCE=ROOT/'research/base-miku-a15'

class StaticLayoutTests(unittest.TestCase):
    def test_physical_mounts_and_data_preserved(self):
        source=(REFERENCE/'ramdisk/fstab.qcom').read_text()
        actual=static_fstab(source)
        rows=[r.split() for r in actual.splitlines() if r and not r.startswith('#')]
        mounts={r[1]:r for r in rows if r[1] in ('/system','/vendor')}
        self.assertEqual(set(mounts),{'/system','/vendor'})
        for mount,row in mounts.items():
            self.assertEqual(row[0],'/dev/block/bootdevice/by-name/'+mount[1:])
            self.assertEqual(row[2],'erofs')
            self.assertIn('first_stage_mount',row[4].split(','))
        old_data=[r.split() for r in source.splitlines() if r.strip() and not r.lstrip().startswith('#') and r.split()[1]=='/data']
        self.assertEqual(old_data,[r for r in rows if r[1]=='/data'])
        for row in rows:
            self.assertNotIn(row[1],('/metadata','/product','/system_ext'))
            self.assertNotIn('logical',row[4].split(','))
            self.assertNotIn('formattable',row[4].split(','))
            self.assertFalse(row[0].endswith('/rawdump'))
    def test_bad_mounts_rejected(self):
        source=(REFERENCE/'ramdisk/fstab.qcom').read_text()
        for bad in [source+'malformed\n',source+'evil /evil ext4 ro wait,logical\n',source.replace('vendor                                                   /vendor','bogus                                                   /bogus')]:
            with self.assertRaises(ValueError):static_fstab(bad)
    def test_hardware_cmdline_tokens_preserved(self):
        source='androidboot.hardware=qcom foo=bar androidboot.super_partition=system'
        actual=static_cmdline(source)
        self.assertIn('androidboot.hardware=qcom',actual.split())
        self.assertIn('foo=bar',actual.split())
        self.assertNotIn('androidboot.super_partition=system',actual.split())
        self.assertIn('androidboot.dynamic_partitions=false',actual.split())
        with self.assertRaises(ValueError):static_cmdline('foo=bar')
    def test_dynamic_properties_only(self):
        source=(REFERENCE/'vendor/build.prop').read_text()
        actual=static_vendor_properties(source)
        before=dict(r.split('=',1) for r in source.splitlines() if '=' in r and not r.startswith('#'))
        after=dict(r.split('=',1) for r in actual.splitlines() if '=' in r and not r.startswith('#'))
        self.assertEqual({k for k in before if before[k]!=after[k]},
             {'ro.boot.dynamic_partitions','ro.boot.dynamic_partitions_retrofit'})
        with self.assertRaises(ValueError):static_vendor_properties('foo=bar')

if __name__=='__main__':unittest.main()
