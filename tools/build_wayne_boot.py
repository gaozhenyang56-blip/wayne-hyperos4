#!/usr/bin/env python3
"""Build an untested wayne boot candidate, retaining its kernel, DTB and cmdline."""
import argparse
import gzip
import hashlib
import json
import pathlib
import struct
from unpack_boot import decode_ramdisk


def cpio_records(data):
    offset=0;result=[]
    while offset+110<=len(data):
        header=data[offset:offset+110];offset+=110
        if header[:6] not in (b'070701',b'070702'):raise ValueError('Unsupported CPIO')
        fields=[int(header[6+i*8:14+i*8],16) for i in range(13)]
        name=data[offset:offset+fields[11]-1].decode()
        offset=(offset+fields[11]+3)&~3
        content=data[offset:offset+fields[6]]
        if len(content)!=fields[6]:raise ValueError('Truncated CPIO')
        offset=(offset+fields[6]+3)&~3
        result.append((name,fields,content))
        if name=='TRAILER!!!':return result
    raise ValueError('Missing CPIO trailer')


def serialize(records):
    output=bytearray()
    for name,original,content in records:
        fields=original.copy();encoded=name.encode()+b'\0'
        fields[6]=len(content);fields[11]=len(encoded);fields[12]=0
        output.extend(b'070701'+''.join(f'{x:08x}' for x in fields).encode()+encoded)
        output.extend(bytes((-len(output))%4));output.extend(content)
        output.extend(bytes((-len(output))%4))
    return bytes(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=pathlib.Path)
    parser.add_argument('donor_init',type=pathlib.Path)
    parser.add_argument('output',type=pathlib.Path)
    parser.add_argument('--layout',choices=['miku-wayne-retrofit-dynamic','stock-size-static'],default='miku-wayne-retrofit-dynamic')
    args=parser.parse_args()
    requirements=pathlib.Path(__file__).resolve().parent.parent/'config/project-requirements.json'
    if requirements.exists() and json.loads(requirements.read_text()).get('target_device',{}).get('dynamic_partitions') is False and args.layout!='stock-size-static':
        raise ValueError('Static target requires explicit stock-size-static boot mode')
    original=args.base.read_bytes()
    if original[:8]!=b'ANDROID!':raise ValueError('Invalid boot magic')
    version=struct.unpack_from('<I',original,40)[0]
    page=struct.unpack_from('<I',original,36)[0]
    kernel_size=struct.unpack_from('<I',original,8)[0]
    ramdisk_size=struct.unpack_from('<I',original,16)[0]
    second_size=struct.unpack_from('<I',original,24)[0]
    if version!=1 or page!=4096 or second_size or struct.unpack_from('<I',original,1632)[0]:
        raise ValueError('Only reference v1/4096 boot without second or recovery DTBO supported')
    if original[-64:-60]==b'AVBf':raise ValueError('AVB footer not supported')
    kernel=original[page:page+kernel_size]
    ramdisk_offset=page+((kernel_size+page-1)//page)*page
    records=cpio_records(decode_ramdisk(original[ramdisk_offset:ramdisk_offset+ramdisk_size]))
    changes={};found=set();updated=[]
    for name,fields,content in records:
        replacement=content
        if name=='init':replacement=args.donor_init.read_bytes()
        elif name=='fstab.qcom' and args.layout=='stock-size-static':
            from static_wayne_layout import static_fstab
            replacement=static_fstab(content.decode()).encode()
        elif name=='fstab.qcom':
            replacement='\n'.join(row for row in content.decode().splitlines()
                                  if not row.split() or row.split()[0] not in ('system_ext','product'))+'\n'
            replacement=replacement.encode()
        elif name=='system/etc/ramdisk/build.prop':
            props={'ro.product.bootimage.name':'wayne_hyperos4',
                   'ro.bootimage.build.fingerprint':'Xiaomi/wayne_hyperos4/wayne:17/CP2A.260605.016/offline01:user/test-keys',
                   'ro.bootimage.build.id':'CP2A.260605.016','ro.bootimage.build.tags':'test-keys',
                   'ro.bootimage.build.version.incremental':'offline01',
                   'ro.bootimage.build.version.release':'17',
                   'ro.bootimage.build.version.release_or_codename':'17',
                   'ro.bootimage.build.version.sdk':'37'}
            replacement='\n'.join((row.split('=',1)[0]+'='+props[row.split('=',1)[0]])
                                  if '=' in row and row.split('=',1)[0] in props else row
                                  for row in content.decode().splitlines())+'\n'
            replacement=replacement.encode()
        if replacement!=content:
            found.add(name);changes[name]={'before':hashlib.sha256(content).hexdigest(),
                                          'after':hashlib.sha256(replacement).hexdigest()}
        updated.append((name,fields,replacement))
    if found!={'init','fstab.qcom','system/etc/ramdisk/build.prop'}:
        raise ValueError('Expected three ramdisk replacements')
    ramdisk=gzip.compress(serialize(updated),mtime=0)
    header=bytearray(original[:page])
    if args.layout=='stock-size-static':
        from static_wayne_layout import static_cmdline
        cmdline=(original[64:576].split(b'\0',1)[0]+original[608:1632].split(b'\0',1)[0]).decode()
        encoded=static_cmdline(cmdline).encode()
        if len(encoded)>=1536:raise ValueError('Cmdline too long')
        header[64:576]=encoded[:512].ljust(512,b'\0')
        header[608:1632]=encoded[512:].ljust(1024,b'\0')
    struct.pack_into('<I',header,16,len(ramdisk))
    struct.pack_into('<I',header,44,(17<<25)|((2026-2000)<<4)|8)
    identity=hashlib.sha1()
    for payload in [kernel,ramdisk,b'',b'']:
        identity.update(payload);identity.update(struct.pack('<I',len(payload)))
    header[576:608]=identity.digest()+bytes(12)
    output=bytes(header)+kernel+bytes((-len(kernel))%page)+ramdisk+bytes((-len(ramdisk))%page)
    if len(output)>64*1024*1024:raise ValueError('Boot exceeds reference partition limit')
    # Validate the emitted archive and ensure only the intended entries changed.
    emitted=cpio_records(decode_ramdisk(ramdisk))
    expected=[]
    for name,fields,content in updated:
        normalized=fields.copy();normalized[6]=len(content)
        normalized[11]=len(name.encode())+1;normalized[12]=0
        expected.append((name,normalized,content))
    if emitted!=expected:raise ValueError('CPIO roundtrip mismatch')
    if output[page:page+kernel_size]!=kernel:raise ValueError('Kernel changed')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(output)
    report={'output':str(args.output),'size':len(output),'sha256':hashlib.sha256(output).hexdigest(),
            'base':str(args.base),'base_sha256':hashlib.sha256(original).hexdigest(),
            'kernel_and_appended_dtb_sha256':hashlib.sha256(kernel).hexdigest(),
            'kernel_dtb_cmdline_preserved':args.layout!='stock-size-static',
            'kernel_and_appended_dtb_preserved':True,'cmdline_changed_for_static_layout':args.layout=='stock-size-static','cpio_metadata_roundtrip_verified':True,
            'ramdisk_changes':changes,'layout':args.layout,
            'status':'UNTESTED_BOOT_CANDIDATE_NOT_A_COMPLETE_ROM'}
    args.output.with_suffix('.img.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
