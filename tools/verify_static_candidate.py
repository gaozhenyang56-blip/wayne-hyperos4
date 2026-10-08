#!/usr/bin/env python3
"""Offline checks for stock-size wayne boot/vendor and merged system."""
import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import sys
from erofs_metadata import inventory
from build_wayne_boot import cpio_records
from unpack_boot import decode_ramdisk
from static_wayne_layout import static_fstab,static_cmdline,static_vendor_properties

ROOT=pathlib.Path(__file__).resolve().parent.parent
BASE=ROOT/'research/base-miku-a15'
DONOR=ROOT/'research/candidates/mi8937-os4'
BIN=ROOT/'tools/local/usr/bin'
OUT=ROOT/'artifacts/experimental/static'
REPORT=ROOT/'research/static-wayne'


def run(*args):subprocess.run([str(a) for a in args],cwd=ROOT,check=True)

def save(name,value):(REPORT/name).write_text(json.dumps(value,indent=2)+'\n')


def verify_fs(label,original,metadata,overlay,image):
    extracted=ROOT/'downloads'/('verified-static-'+label)
    run(BIN/'fsck.erofs','--extract='+str(extracted),'--no-preserve-owner',image)
    run(sys.executable,ROOT/'tools/verify_system_contents.py',original,extracted,metadata,overlay,
        REPORT/(label+'-content-check.json'))
    old=json.loads(metadata.read_text());new=inventory(image,str(BIN/'dump.erofs'))
    differences=[p for p,r in old['paths'].items() if any(r[k]!=new['paths'].get(p,{}).get(k)
                 for k in ('mode','uid','gid','xattrs_base64'))]
    save(label+'-metadata-check.json',{'original_paths':len(old['paths']),
        'rebuilt_paths':len(new['paths']),'differences':differences,'success':not differences})
    if differences:raise ValueError('Metadata mismatch: '+label)
    return extracted


def main():
    p=argparse.ArgumentParser();p.add_argument('--skip-system-recheck',action='store_true');a=p.parse_args()
    REPORT.mkdir(exist_ok=True)
    profile=json.loads((ROOT/'config/wayne-stock-static.json').read_text())
    for name in ('boot','system','vendor'):
        image=OUT/(name+'.img')
        if not image.exists() or image.stat().st_size>profile['partition_sizes'][name]:
            raise ValueError('Static partition overflow/missing: '+name)
    data=(OUT/'boot.img').read_bytes();reference=(BASE/'boot.img').read_bytes()
    page=struct.unpack_from('<I',data,36)[0];ks=struct.unpack_from('<I',data,8)[0];rs=struct.unpack_from('<I',data,16)[0]
    off=page+((ks+page-1)//page)*page;kernel=data[page:page+ks];ramdisk=data[off:off+rs]
    if kernel!=reference[page:page+ks]:raise ValueError('Kernel/DTB changed')
    cmd=lambda b:(b[64:576].split(b'\0',1)[0]+b[608:1632].split(b'\0',1)[0]).decode()
    if cmd(data)!=static_cmdline(cmd(reference)):raise ValueError('Static cmdline mismatch')
    identity=hashlib.sha1()
    for payload in (kernel,ramdisk,b'',b''):identity.update(payload);identity.update(struct.pack('<I',len(payload)))
    if data[576:596]!=identity.digest():raise ValueError('Invalid boot ID')
    entries={n:c for n,f,c in cpio_records(decode_ramdisk(ramdisk))}
    expected=static_fstab((BASE/'ramdisk/fstab.qcom').read_text()).encode()
    if entries['fstab.qcom']!=expected:raise ValueError('Boot fstab mismatch')
    if entries['init']!=(DONOR/'ramdisk/init').read_bytes():raise ValueError('Init changed')
    save('boot-check.json',{'success':True,'kernel_and_appended_dtb_preserved':True,
         'cmdline_changed_for_static_layout':True,'boot_id_verified':True,
         'fstab_uses_physical_nodes':True,'rawdump_repurposed':False,'hardware_tested':False,
         'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    vendor=verify_fs('vendor',BASE/'vendor',OUT/'vendor-inode-metadata.json',OUT/'vendor-overlay.tar',OUT/'vendor.img')
    try:
        if (vendor/'etc/fstab.qcom').read_bytes()!=expected:raise ValueError('Vendor/boot fstab mismatch')
        props=static_vendor_properties((BASE/'vendor/build.prop').read_text()).encode()
        if (vendor/'build.prop').read_bytes()!=props:raise ValueError('Vendor layout properties mismatch')
        run(sys.executable,ROOT/'tools/audit_native_versions.py',DONOR/'system',vendor,
            ROOT/'downloads/native-apex-audit/runtime',REPORT/'native-versions.json')
        native=json.loads((REPORT/'native-versions.json').read_text())
        if len(native['results'])!=4 or any(r['missing_dependency_files'] or r['unresolved_required_symbols_in_selected_scope'] for r in native['results']):
            raise ValueError('Native version inventory failed')
    finally:shutil.rmtree(vendor)
    if not a.skip_system_recheck:
        system=verify_fs('system',DONOR/'system',DONOR/'inode-metadata.json',OUT/'system-overlay.tar',OUT/'system.img')
        shutil.rmtree(system)
    for relative in ('research/wayne-os4-policy/policy-check.json','research/wayne-os4-policy/runtime/policy-check.json'):
        for source,digest in json.loads((ROOT/relative).read_text())['inputs'].items():
            with (ROOT/source).open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual!=digest:raise ValueError('Policy evidence input changed: '+source)
    save('image-check.json',{'success':True,'layout':'stock-size-static','hardware_tested':False,
         'system_full_recheck_performed':not a.skip_system_recheck,'preserve_partition_table':True,
         'rawdump_repurposed':False,'partition_sizes':profile['partition_sizes']})
    print('PASS: static boot, vendor content/metadata, native inventories and partition bounds; hardware untested.')

if __name__=='__main__':main()
