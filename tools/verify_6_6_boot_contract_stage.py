#!/usr/bin/env python3
"""Snapshot existing boot evidence only; never pack or qualify a boot image."""
import datetime
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

def main():
    suite = unittest.TestSuite()
    for name in ('test_6_6_gate_integration', 'test_static_boot_header'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful(): raise SystemExit(1)
    report = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'baseline':'8b1a43a', 'tests_passed':result.testsRun, 'reference_boots':[], 'preflight':{}, 'preservation':[], 'priority_gap':'No actual-current-wayne boot contract or 6.6 packaging integration; separate Image.gz/DTB cannot inherit old kernel payload packaging', 'current_device_boot_parameters_verified':False, 'hardware_tested':False, 'new_image_created':False, 'next':'Collect actual-current boot/header and partition size, signing/bootloader evidence; resolve DTB binding independently before any future packaging'}
    for name in ('research/gpu-allocator-stage/lineage-wayne/boot.img', 'artifacts/experimental/static/boot.img'):
        path=ROOT/name
        if not path.exists():
            report['reference_boots'].append({'path':name, 'available':False});continue
        blob=path.read_bytes()
        if len(blob)<1648 or blob[:8]!=b'ANDROID!':raise ValueError('Unexpected preserved legacy reference')
        words=struct.unpack_from('<10I',blob,8)
        kernel_size,kaddr,ramdisk_size,raddr,second_size,saddr,taddr,page,version,os_version=words
        if version not in (0,1) or page!=4096 or second_size:raise ValueError('Reference outside existing audit scope')
        ramdisk_offset=page+((kernel_size+page-1)//page)*page
        if ramdisk_offset+ramdisk_size>len(blob):raise ValueError('Truncated reference')
        prefix=blob[page:page+4].hex()
        report['reference_boots'].append({'path':name,'available':True,'role':'comparison or preserved historical experiment, NOT current user boot','sha256':hashlib.sha256(blob).hexdigest(),'size':len(blob),'header_version':version,'pagesize':page,'kernel_size':kernel_size,'ramdisk_size':ramdisk_size,'second_size':second_size,'kernel_file_offset':page,'ramdisk_file_offset':ramdisk_offset,'load_addresses':{'kernel':kaddr,'ramdisk':raddr,'second':saddr,'tags':taddr},'base_and_offsets_verified':False,'kernel_prefix_hex':prefix,'kernel_compression':'gzip' if prefix.startswith('1f8b') else 'unknown/not decoded','ramdisk_prefix_hex':blob[ramdisk_offset:ramdisk_offset+4].hex(),'cmdline':(blob[64:576].split(b'\0',1)[0]+blob[608:1632].split(b'\0',1)[0]).decode(),'avb_footer_magic_observed':blob[-64:-60]==b'AVBf','signature_policy_verified':False,'dtb_layout_verified':False})
    for tool in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
        result=subprocess.run([sys.executable,str(ROOT/'tools'/tool),'--preflight'],cwd=ROOT,capture_output=True,text=True)
        report['preflight'][tool]=result.returncode
        if result.returncode!=2:raise ValueError('Existing DT gate no longer blocked')
    old=json.loads((ROOT/'research/dtb-reader-stage/checkpoint.json').read_text())
    for item in old['preservation']:
        if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Preserved evidence changed')
        report['preservation'].append(item)
    report['quota']='Realtime unavailable; user snapshot 57%/87%, no precise control claim'
    out=ROOT/'research/boot-contract-6.6-stage';out.mkdir(parents=True,exist_ok=True)
    (out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
