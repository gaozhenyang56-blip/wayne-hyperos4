#!/usr/bin/env python3
"""Install an experimental static wayne package; default is offline verify-only."""
import argparse
import hashlib
import json
import pathlib
import re
import struct
import subprocess
import time

STOCK={'system':3221225472,'vendor':2147483648,'boot':67108864}
ORDER=('vendor','system','boot')
LP_GEOMETRY_MAGIC=0x616c4467
EROFS_MAGIC=0xe0f5e1e2


def checked(*args):
    result=subprocess.run(list(args),capture_output=True,timeout=60)
    if result.returncode:raise ValueError(result.stderr.decode(errors='replace'))
    return result.stdout


def verify_images(folder):
    folder=folder.resolve();manifest=json.loads((folder/'manifest.json').read_text())
    if manifest.get('device')!='wayne' or manifest.get('layout')!='stock-size-static':
        raise ValueError('Package does not target static wayne')
    if set(manifest.get('images',{}))!={n+'.img' for n in STOCK}:raise ValueError('Unexpected flash targets')
    paths={}
    for name,limit in STOCK.items():
        filename=name+'.img';record=manifest['images'][filename];path=(folder/filename).resolve()
        if not path.is_relative_to(folder) or not path.is_file():raise ValueError('Invalid image path')
        size=path.stat().st_size
        if size!=record['size'] or not 0<size<=limit or size%4096:raise ValueError('Image size mismatch/overflow')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=record['sha256']:raise ValueError('Image hash mismatch')
        with path.open('rb') as stream:
            header=stream.read(4096)
        if name=='boot':
            if header[:8]!=b'ANDROID!':raise ValueError('Invalid boot magic')
        elif struct.unpack_from('<I',header,1024)[0]!=EROFS_MAGIC:raise ValueError('Expected EROFS image')
        paths[name]=path
    return manifest,paths


def validate_static_header(data):
    if len(data)!=12288:raise ValueError('Incomplete physical system header')
    if any(struct.unpack_from('<I',data,offset)[0]==LP_GEOMETRY_MAGIC for offset in (4096,8192)):
        raise ValueError('Dynamic super metadata detected; refusing physical overwrite')
    if struct.unpack_from('<I',data,1024)[0]!=EROFS_MAGIC and struct.unpack_from('<H',data,1080)[0]!=0xef53:
        raise ValueError('Physical system is not an existing static ext4/EROFS filesystem')


class Recovery:
    def __init__(self,serial):self.serial=serial
    def shell(self,*args):return checked('adb','-s',self.serial,'shell',*args).decode().strip()
    def header(self,path):return checked('adb','-s',self.serial,'exec-out','dd','if='+path,'bs=4096','count=3')
    def reboot_bootloader(self):checked('adb','-s',self.serial,'reboot','bootloader')


def check_recovery(device):
    if device.shell('getprop','ro.product.device')!='wayne':raise ValueError('Recovery device must be wayne')
    if device.shell('getprop','ro.bootmode')!='recovery':raise ValueError('Start in Recovery, not normal Android')
    if device.shell('id','-u')!='0':raise ValueError('Recovery ADB must be root')
    if device.shell('getprop','ro.boot.slot_suffix'):raise ValueError('A/B device rejected')
    paths={}
    for name,size in STOCK.items():
        path=device.shell('readlink','-f','/dev/block/bootdevice/by-name/'+name)
        if not re.fullmatch(r'/dev/block/mmcblk0p[0-9]+',path):raise ValueError('Not an eMMC physical partition: '+name)
        if int(device.shell('blockdev','--getsize64',path))!=size:raise ValueError('Partition size differs from stock reference: '+name)
        paths[name]=path
    if len(set(paths.values()))!=3:raise ValueError('Partition nodes overlap')
    validate_static_header(device.header(paths['system']))
    return paths


class Bootloader:
    def __init__(self,serial):self.serial=serial
    def variable(self,name):
        r=subprocess.run(['fastboot','-s',self.serial,'getvar',name],capture_output=True,text=True,timeout=60)
        output=r.stdout+r.stderr
        if r.returncode:raise ValueError('Cannot verify fastboot '+name+': '+output)
        for line in output.splitlines():
            line=line.strip().removeprefix('(bootloader)').strip()
            if line.startswith(name+':'):return line[len(name)+1:].strip()
        raise ValueError('Missing fastboot variable: '+name)
    def flash(self,name,path):
        subprocess.run(['fastboot','-s',self.serial,'-S','256M','flash',name,str(path)],check=True,timeout=900)


def check_bootloader(device):
    if device.variable('product')!='wayne':raise ValueError('Fastboot product mismatch')
    try:userspace=device.variable('is-userspace')
    except ValueError as error:
        if not any(x in str(error).lower() for x in ('unknown variable','variable not found','variable not supported')):raise
        version=device.variable('version-bootloader')
        if not version or version.lower()=='unknown':raise ValueError('Legacy bootloader identity unavailable')
        userspace='no'
    if userspace!='no':raise ValueError('Use bootloader fastboot, not fastbootd')
    if device.variable('unlocked')!='yes':raise ValueError('Bootloader unlock not verified')
    for name,size in STOCK.items():
        if int(device.variable('partition-size:'+name),16)!=size:raise ValueError('Bootloader partition size mismatch: '+name)


def install(paths,recovery,bootloader):
    check_recovery(recovery)
    recovery.reboot_bootloader()
    check_bootloader(bootloader)
    # All device/layout/capacity checks above complete before the first image write.
    for name in ORDER:bootloader.flash(name,paths[name])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--verify-only',action='store_true');mode.add_argument('--flash',action='store_true')
    p.add_argument('--serial');p.add_argument('--directory',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent)
    a=p.parse_args();manifest,paths=verify_images(a.directory)
    print('Image hashes and stock static partition limits verified. Hardware untested; strict SELinux check failed.')
    if not a.flash:return
    if not a.serial:p.error('--flash requires an explicit --serial')
    install(paths,Recovery(a.serial),Bootloader(a.serial))
    print('Images written; device remains in bootloader. No userdata/firmware/GPT writes or automatic system reboot.')

if __name__=='__main__':main()
