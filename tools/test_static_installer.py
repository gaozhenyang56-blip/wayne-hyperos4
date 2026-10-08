#!/usr/bin/env python3
"""No device access: verify image checks and ordering of real installer guards."""
import hashlib
import json
import pathlib
import struct
import tempfile
import unittest
from install_static_wayne import STOCK,EROFS_MAGIC,LP_GEOMETRY_MAGIC,verify_images,install

class RecoveryFixture:
    def __init__(self):
        self.product='wayne';self.mode='recovery';self.uid='0';self.slot=''
        self.nodes={n:'/dev/block/mmcblk0p'+str(i) for i,n in enumerate(STOCK,20)}
        self.sizes=dict(STOCK);self.data=bytearray(12288);struct.pack_into('<I',self.data,1024,EROFS_MAGIC)
        self.reboots=0
    def shell(self,*args):
        if args==('getprop','ro.product.device'):return self.product
        if args==('getprop','ro.bootmode'):return self.mode
        if args==('id','-u'):return self.uid
        if args==('getprop','ro.boot.slot_suffix'):return self.slot
        if args[0]=='readlink':return self.nodes[args[-1].split('/')[-1]]
        if args[0]=='blockdev':return str(self.sizes[next(n for n,p in self.nodes.items() if p==args[-1])])
        raise AssertionError(args)
    def header(self,path):return bytes(self.data)
    def reboot_bootloader(self):self.reboots+=1

class BootloaderFixture:
    def __init__(self):
        self.values={'product':'wayne','is-userspace':'no','unlocked':'yes',
            **{'partition-size:'+n:hex(s) for n,s in STOCK.items()}}
        self.writes=[]
    def variable(self,name):return self.values[name]
    def flash(self,name,path):self.writes.append(name)

class StaticInstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        images={}
        for name in STOCK:
            b=bytearray(4096)
            if name=='boot':b[:8]=b'ANDROID!'
            else:struct.pack_into('<I',b,1024,EROFS_MAGIC)
            p=self.root/(name+'.img');p.write_bytes(b)
            images[p.name]={'size':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        self.manifest={'device':'wayne','layout':'stock-size-static','images':images}
        self.write_manifest()
        self.paths={n:self.root/(n+'.img') for n in STOCK}
    def write_manifest(self):(self.root/'manifest.json').write_text(json.dumps(self.manifest))
    def assert_recovery_rejects(self,r):
        b=BootloaderFixture()
        with self.assertRaises(ValueError):install(self.paths,r,b)
        self.assertEqual(b.writes,[]);self.assertEqual(r.reboots,0)
    def test_valid_offline_images_and_corrupt_hash(self):
        verify_images(self.root)
        with (self.root/'boot.img').open('r+b') as stream:stream.write(b'BADIMAGE')
        with self.assertRaises(ValueError):verify_images(self.root)
    def test_wrong_package_layout(self):
        self.manifest['layout']='miku-wayne-retrofit-dynamic';self.write_manifest()
        with self.assertRaises(ValueError):verify_images(self.root)
    def test_lp_primary_and_backup_rejected_before_reboot(self):
        for offset in (4096,8192):
            r=RecoveryFixture();struct.pack_into('<I',r.data,offset,LP_GEOMETRY_MAGIC)
            self.assert_recovery_rejects(r)
    def test_wrong_recovery_identity_state_and_sizes(self):
        for attr,value in [('product','jasmine_sprout'),('mode','normal'),('uid','2000'),('slot','_a')]:
            r=RecoveryFixture();setattr(r,attr,value);self.assert_recovery_rejects(r)
        r=RecoveryFixture();r.sizes['vendor']-=4096;self.assert_recovery_rejects(r)
    def test_mapper_or_invalid_filesystem_rejected(self):
        r=RecoveryFixture();r.nodes['system']='/dev/block/dm-0';self.assert_recovery_rejects(r)
        r=RecoveryFixture();r.data=bytearray(12288);self.assert_recovery_rejects(r)
    def test_bootloader_checks_finish_before_first_write(self):
        for name,value in [('product','jasmine_sprout'),('is-userspace','yes'),('unlocked','no'),('partition-size:boot','0x1000')]:
            r=RecoveryFixture();b=BootloaderFixture();b.values[name]=value
            with self.assertRaises(ValueError):install(self.paths,r,b)
            self.assertEqual(b.writes,[])
    def test_legacy_bootloader_unknown_userspace_variable(self):
        r=RecoveryFixture();b=BootloaderFixture();original=b.variable
        def legacy(name):
            if name=='is-userspace':raise ValueError('unknown variable')
            if name=='version-bootloader':return 'sdm660-legacy'
            return original(name)
        b.variable=legacy;install(self.paths,r,b)
        self.assertEqual(b.writes,['vendor','system','boot'])
    def test_positive_writes_exactly_three_images(self):
        r=RecoveryFixture();b=BootloaderFixture();install(self.paths,r,b)
        self.assertEqual(r.reboots,1);self.assertEqual(b.writes,['vendor','system','boot'])

if __name__=='__main__':unittest.main()
