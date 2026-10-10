#!/usr/bin/env python3
"""Read-only local static boot/fstab audit, never a boot/decryption verdict."""
import datetime
import hashlib
import json
import pathlib
import struct
from build_wayne_boot import cpio_records
from unpack_boot import decode_ramdisk
from static_wayne_layout import static_fstab,static_cmdline

ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/'research/boot-static-stage'


def evidence(path):
    data=path.read_bytes()
    return {'path':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(data).hexdigest(),
            'size':len(data)}


def rows(text):
    return [line.split() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]


def boot(path):
    data=path.read_bytes()
    if len(data)<1636 or data[:8]!=b'ANDROID!':raise ValueError('Invalid legacy boot')
    version=struct.unpack_from('<I',data,40)[0]
    if version not in (0,1):raise ValueError('Audit only supports local v0/v1 references')
    second_size=struct.unpack_from('<I',data,24)[0]
    if second_size:raise ValueError('Second payload outside local audit scope')
    recovery_dtbo_size=0
    if version==1:
        if len(data)<1648:raise ValueError('Truncated v1 header')
        recovery_dtbo_size=struct.unpack_from('<I',data,1632)[0]
        header_size=struct.unpack_from('<I',data,1644)[0]
        if recovery_dtbo_size or header_size!=1648:
            raise ValueError('Unexpected local v1 recovery DTBO/header size')
    if data[-64:-60]==b'AVBf':raise ValueError('AVB footer outside local audit scope')
    page=struct.unpack_from('<I',data,36)[0]
    if page!=4096:raise ValueError('Unexpected local reference page size')
    kernel_size=struct.unpack_from('<I',data,8)[0]
    ramdisk_size=struct.unpack_from('<I',data,16)[0]
    offset=page+((kernel_size+page-1)//page)*page
    if not kernel_size or not ramdisk_size or offset+ramdisk_size>len(data):raise ValueError('Truncated boot')
    entries={name:content for name,_,content in cpio_records(decode_ramdisk(data[offset:offset+ramdisk_size]))}
    cmd=(data[64:576].split(b'\0',1)[0]+data[608:1632].split(b'\0',1)[0]).decode()
    return {**evidence(path),'header_version':version,'page_size':page,'kernel_size':kernel_size,
            'ramdisk_size':ramdisk_size,'second_size':second_size,'recovery_dtbo_size':recovery_dtbo_size,
            'avb_footer_present':False,'ramdisk_compression':'gzip' if data[offset:offset+2]==b'\x1f\x8b' else 'legacy-lz4',
            'cmdline':cmd,'ramdisk_files':sorted(entries),
            'fstab':entries.get('fstab.qcom',b'').decode()},entries


def main():
    OUT.mkdir(exist_ok=True)
    native,_=boot(ROOT/'research/gpu-allocator-stage/lineage-wayne/boot.img')
    historical=ROOT/'research/base-miku-a15'
    candidate,entries=boot(ROOT/'artifacts/experimental/static/boot.img')
    original=(historical/'ramdisk/fstab.qcom').read_text()
    expected=static_fstab(original)
    assert candidate['fstab']==expected
    parsed=rows(expected)
    data_rows=[r for r in parsed if r[1]=='/data']
    assert data_rows==[r for r in rows(original) if r[1]=='/data']
    assert all('logical' not in r[4].split(',') and not r[0].endswith('/rawdump') for r in parsed)
    assert {r[1] for r in parsed if r[1] in ('/system','/vendor')}=={'/system','/vendor'}
    candidate_meta=json.loads((ROOT/'artifacts/experimental/static/boot.img.json').read_text())
    assert candidate['sha256']==candidate_meta['sha256']
    assert static_cmdline(candidate['cmdline'])==candidate['cmdline']
    donor=ROOT/'research/candidates/mi8937-os4'
    assert hashlib.sha256(entries['init']).hexdigest()==evidence(donor/'ramdisk/init')['sha256']
    metadata_refs=[r for r in parsed if '/metadata' in ' '.join(r) and r[1]!='/metadata']
    report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'target':'China Xiaomi Mi6X wayne/SDM660, stock static partitions',
        'native_sample_role':'non-Miku wayne comparison, not user current boot',
        'native_sample_boot':native,'preserved_historical_static_boot':candidate,
        'historical_role':'existing third-party artifact provenance ONLY, not device baseline',
        'data_rows_preserved':data_rows,'dangling_fstab_metadata_references':metadata_refs,
        'sources':[evidence(ROOT/'research/static-wayne/android_device_xiaomi_wayne-rootdir_etc_fstab.qcom'),
                   evidence(ROOT/'research/gpu-allocator-stage/lineage-wayne/selected-vendor/etc/fstab.qcom'),
                   evidence(historical/'ramdisk/fstab.qcom'),evidence(historical/'vendor/etc/init/hw/init.target.rc'),
                   evidence(donor/'system/system/etc/init/hw/init.rc'),evidence(donor/'system/system/etc/init/vold.rc')],
        'boot_builder_constraints':'explicit static mode required; builder v1/4096 only, no second/recovery DTBO/AVB footer; native sample v0 remains unsupported for rebuilding',
        'encryption_notes':['FBE fileencryption=ice present in fixed wayne config and preserved historical candidate',
                            'non-Miku vendor sample uses encryptable=ice instead; never infer current userdata mode',
                            'no metadata_encryption/keydirectory flag in preserved data rows; donor init still creates /metadata/vold and /metadata/apex paths',
                            'persistent metadata/checkpoint/APEX behavior and legacy ice parsing unverified',
                            'keymaster/TEE, fscrypt policy and rollback compatibility unverified; never format userdata as an audit fix'],
        'partition_capacities_verified':False,'bootloader_header_acceptance_verified':False,
        'init_runtime_verified':False,'vold_decryption_verified':False,
        'new_image_created':False,'hardware_tested':False,'bootable_verified':False}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Local existing boot SHA, ramdisk fstab/init and static cmdline checked; boot/decryption UNKNOWN.')


if __name__=='__main__':main()
