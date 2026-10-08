#!/usr/bin/env python3
"""Package a static wayne experiment only after full offline image verification."""
import argparse
import datetime
import json
import pathlib
import shutil
import zipfile
from package_candidate import SplitWriter,hash_file
from install_static_wayne import STOCK

ROOT=pathlib.Path(__file__).resolve().parent.parent
NAME='wayne-hyperos4-static-20261009'

def check_reports(root):
    folder=root/'research/static-wayne'
    names=['image-check.json','boot-check.json','system-content-check.json','system-metadata-check.json',
           'vendor-content-check.json','vendor-metadata-check.json','native-versions.json','vintf-check.json']
    reports={n:json.loads((folder/n).read_text()) for n in names}
    for name in names[:6]:
        if not reports[name]['success']:raise ValueError('Failed static check: '+name)
    if not reports['image-check.json'].get('system_full_recheck_performed'):raise ValueError('Full system recheck required')
    if reports['vintf-check.json']['check']['exit_code']!=0:raise ValueError('HAL check failed')
    targets={'lib/hw/camera.sdm660.so','lib/hw/android.hardware.camera.provider@2.4-impl.so',
             'bin/hw/android.hardware.camera.provider@2.4-service','bin/hw/android.hardware.graphics.composer@2.1-service'}
    native=reports['native-versions.json']['results']
    if len(native)!=4 or {r['target'] for r in native}!=targets or any(r['inspected_libraries']<=0 or r['missing_dependency_files'] or r['unresolved_required_symbols_in_selected_scope'] for r in native):
        raise ValueError('Native inventory incomplete or unresolved')
    return reports


def main():
    p=argparse.ArgumentParser();p.add_argument('--build-commit',required=True);a=p.parse_args()
    if json.loads((ROOT/'config/project-requirements.json').read_text())['target_device']['dynamic_partitions'] is not False:
        raise ValueError('Project target must explicitly be static')
    reports=check_reports(ROOT);images={n+'.img':ROOT/'artifacts/experimental/static'/(n+'.img') for n in STOCK}
    for name,path in images.items():
        if path.stat().st_size>STOCK[name.split('.')[0]]:raise ValueError('Stock partition overflow')
    strict=json.loads((ROOT/'research/wayne-os4-policy/policy-check.json').read_text())
    runtime=json.loads((ROOT/'research/wayne-os4-policy/runtime/policy-check.json').read_text())
    if not runtime['success']:raise ValueError('Runtime policy compilation failed')
    manifest={'device':'wayne','layout':'stock-size-static','android_sdk':37,
        'declared_hyperos':'4.0.0.16.XPCCNXM','kernel':'4.19.315-Miku-Vampire_v2-g3a74d7',
        'kernel_vendor_material_origin':'Miku wayne reference, adapted to static physical mounts',
        'requires_miku_installed':False,'build_commit':a.build_commit,
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'offline-static-experimental-unbooted','hardware_tested':False,
        'strict_neverallow_passed':strict['success'],'runtime_mode_policy_compiled':runtime['success'],
        'native_symbol_version_inventory_checked':True,'linker_namespaces_verified':False,
        'preserve_partition_table':True,'partition_sizes':STOCK,'rawdump_repurposed':False,
        'unresolved':['Boot and hardware behavior','Runtime linker/APEX compatibility',
                      'Strict SELinux neverallow conflicts','Data encryption compatibility with previous ROM',
                      'Core framework changes not fully audited'],
        'images':{n:{'size':p.stat().st_size,'sha256':hash_file(p)} for n,p in images.items()}}
    output=ROOT/'artifacts/releases/static';output.mkdir(parents=True,exist_ok=True)
    stage=output/'stage';stage.mkdir(exist_ok=True)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copyfile(ROOT/'tools/install_static_wayne.py',stage/'install.py')
    instructions="""Xiaomi 6X / wayne STOCK-SIZE STATIC experimental package.
No dynamic partition conversion and no Miku installation prerequisite.
The boot/vendor material originates from a Miku wayne reference but is adapted
for physical stock-size system/vendor partitions and contains no rawdump mount.

UNTESTED ON HARDWARE. Strict SELinux checking fails; boot, encryption, radio,
camera and other hardware functions remain unverified. Back up data and original
boot/system/vendor images. Only for unlocked wayne with original partition sizes.

Download both ZIP parts and SHA256SUMS. Verify hashes, concatenate parts in
numeric order, and extract the resulting ZIP. Linux/macOS: cat; Windows: copy /b.
Do not flash one part by itself. Python 3.11+ and current adb/fastboot required.
Run python install.py --verify-only for offline checks (also the default).

For explicit installation, start in TWRP/OrangeFox or another compatible Recovery
with root ADB, then run python install.py --flash --serial DEVICE_SERIAL.
It reads physical nodes, exact partition sizes and the system header first;
dynamic metadata, a different device, wrong sizes or a normal Android session
are rejected. It then reboots to BOOTLOADER fastboot, checks product/unlock/sizes,
and writes vendor, system and boot using 256 MiB sparse transfer chunks.
It leaves the phone in the bootloader and does not boot Android automatically.
No GPT, userdata, firmware, cust, cache or rawdump writes or formatting.
Previous-ROM encryption compatibility is unknown; no data reset is performed.

Reports describe limited offline checks; they do not prove the ROM boots.
"""
    (stage/'INSTALL.txt').write_text(instructions)
    files={**images,'manifest.json':stage/'manifest.json','install.py':stage/'install.py','INSTALL.txt':stage/'INSTALL.txt'}
    files.update({'reports/'+n:ROOT/'research/static-wayne'/n for n in reports})
    files.update({'reports/'+n:ROOT/'research/wayne-os4-policy'/p for n,p in
                  [('strict-policy.json','policy-check.json'),('runtime-policy.json','runtime/policy-check.json')]})
    prefix=output/(NAME+'.zip')
    if list(output.glob(prefix.name+'.*')):raise ValueError('Existing parts: refusing overwrite')
    writer=SplitWriter(prefix)
    try:
        with zipfile.ZipFile(writer,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
            for name,path in sorted(files.items()):
                info=zipfile.ZipInfo(NAME+'/'+name,(2009,1,1,0,0,0));info.external_attr=(0o100755 if name=='install.py' else 0o100644)<<16
                with path.open('rb') as source,archive.open(info,'w',force_zip64=True) as target:shutil.copyfileobj(source,target,8*1024*1024)
    finally:writer.close()
    parts={p.name:{'size':p.stat().st_size,'sha256':hash_file(p)} for p in writer.paths}
    (output/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+n+'\n' for n,r in parts.items()))
    (ROOT/'artifacts/static-candidate-package.json').write_text(json.dumps({'manifest':manifest,'parts':parts,'archive_entries':sorted(files)},indent=2)+'\n')
    print(json.dumps({'parts':parts,'hardware_tested':False},indent=2))

if __name__=='__main__':main()
