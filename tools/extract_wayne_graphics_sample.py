#!/usr/bin/env python3
"""Reproduce selective OTA evidence; no mounts, partition writes or flashing."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import brotli
from inspect_ota import inspect
from unpack_boot import unpack

URL = 'https://downloads.sourceforge.net/project/lineageos-wayne/lineage-19.1-20251122-UNOFFICIAL-wayne.zip'


def restore_sparse(data_file, transfer_file, target):
    lines = transfer_file.read_text().splitlines()
    if lines[0] != '4':raise ValueError('Only v4 full OTA analysis supported')
    extents = []
    for line in lines[4:]:
        command, encoded = line.split(' ', 1);values = list(map(int, encoded.split(',')))
        if command not in ('new', 'zero', 'erase') or values[0] != len(values)-1 or values[0] % 2:
            raise ValueError('Unsupported OTA extent')
        for start, end in zip(values[1::2], values[2::2]):
            if not 0 <= start < end:raise ValueError('Invalid extent')
            extents.append((start, end, command))
    ordered = sorted(extents)
    if not ordered or any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('Overlapping/empty extents; sparse analysis forbidden')
    size = max(b for a, b, c in extents)*4096
    if size > 2*1024**3:raise ValueError('Analysis size limit exceeded')
    data = brotli.decompress(data_file.read_bytes())
    if sum((b-a)*4096 for a,b,c in extents if c=='new') != len(data):
        raise ValueError('Full OTA data length mismatch')
    temporary = target.with_suffix('.img.part')
    with temporary.open('w+b') as stream:
        stream.truncate(size);offset = 0
        for a,b,c in extents:
            if c=='new':
                length=(b-a)*4096;stream.seek(a*4096);stream.write(data[offset:offset+length]);offset+=length
        stream.seek(0);sha=hashlib.file_digest(stream,'sha256').hexdigest()
    temporary.replace(target)
    return {'size': size, 'sha256': sha, 'allocated_bytes': target.stat().st_blocks*512,
            'source': 'ZIP member CRC verified; whole archive signature/hash unverified',
            'restoration': 'non-overlapping v4 full OTA, sparse zero/erase extents', 'hardware_tested': False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--debugfs',type=pathlib.Path,required=True)
    p.add_argument('--library-dir',type=pathlib.Path)
    p.add_argument('--from-local',action='store_true');args=p.parse_args();root=args.output
    if not args.from_local:
        inspect(URL,root,['boot.img','vendor.new.dat.br','vendor.transfer.list'])
    report=json.loads((root/'inspection.json').read_text())
    if report['url']!=URL or 'pre-device=wayne' not in report['metadata']['META-INF/com/android/metadata']:
        raise ValueError('Wrong device/source metadata')
    for item in report['extracted']:
        if hashlib.sha256((root/pathlib.Path(item['entry']).name).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Changed ZIP member')
    image=root/'vendor.img';restoration=root/'vendor-restoration.json'
    if image.exists() and restoration.exists():
        with image.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
        if sha!=json.loads(restoration.read_text())['sha256']:raise ValueError('Changed restored image')
    else:
        restoration.write_text(json.dumps(restore_sparse(root/'vendor.new.dat.br',root/'vendor.transfer.list',image),indent=2)+'\n')
    if not (root/'boot/boot-inspection.json').exists():unpack(root/'boot.img',root/'boot')
    paths=[]
    for prefix in ['lib','lib64']:
        paths.extend(f'{prefix}/{x}' for x in ['libgsl.so','libion.so','libsdmcore.so','libsdmutils.so','libgrallocutils.so'])
        paths.extend(f'{prefix}/egl/{x}' for x in ['libEGL_adreno.so','libGLESv2_adreno.so'])
        paths.extend(f'{prefix}/hw/{x}' for x in ['gralloc.sdm660.so','hwcomposer.sdm660.so',
                     'android.hardware.graphics.allocator@2.0-impl.so','android.hardware.graphics.mapper@2.0-impl-2.1.so'])
    paths+=['etc/fstab.qcom','etc/vintf/manifest.xml','etc/manifest.xml','build.prop',
            'etc/init/android.hardware.graphics.allocator@2.0-service.rc',
            'etc/init/android.hardware.graphics.composer@2.1-service.rc','etc/init/hw/init.qcom.rc','etc/ueventd.rc']
    env=dict(os.environ)
    if args.library_dir:env['LD_LIBRARY_PATH']=str(args.library_dir.resolve())
    out=root/'selected-vendor';rows=[];missing=[]
    for name in paths:
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True)
        result=subprocess.run([str(args.debugfs.resolve()),'-R',f'dump /{name} {dest.resolve()}',str(image.resolve())],
                              env=env,text=True,capture_output=True)
        if result.returncode:raise ValueError('debugfs failed: '+result.stderr)
        if not dest.exists():
            if 'File not found' not in result.stderr:raise ValueError('Unexpected dump error: '+result.stderr)
            missing.append(name);continue
        rows.append({'path':name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'size':dest.stat().st_size})
    (root/'selected-files.json').write_text(json.dumps({'requested':paths,'extracted':rows,'missing':missing},indent=2)+'\n')
    print(json.dumps({'extracted_count':len(rows),'missing':missing,'hardware_tested':False}))


if __name__=='__main__':main()
