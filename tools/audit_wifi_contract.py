#!/usr/bin/env python3
"""Read-only evidence gate; unknown driver delivery is not driver absence."""
import hashlib
import json
import pathlib


def assess(paths,delivery='unknown',config_verified=False,module_inventory_verified=False,firmware_inventory_verified=False):
    if delivery not in ('unknown','builtin','module'):raise ValueError('Explicit driver delivery required')
    if any(type(x) is not bool for x in (config_verified,module_inventory_verified,firmware_inventory_verified)):
        raise ValueError('Evidence flags must be JSON booleans')
    hal=[p for p in paths if pathlib.PurePosixPath(p).name.startswith(('wifi.','android.hardware.wifi')) and ('/hw/' in p or '/bin/' in p)]
    config=[p for p in paths if 'wifi' in pathlib.PurePosixPath(p).parts and p.endswith(('.conf','.ini','.xml'))]
    missing=[]
    if not hal:missing.append('wifi_hal')
    if not config:missing.append('wifi_config')
    if delivery=='unknown' or not config_verified:missing.append('driver_delivery_and_actual_kernel_config')
    if delivery=='module' and not module_inventory_verified:missing.append('module_inventory')
    if not firmware_inventory_verified:missing.append('firmware_inventory_and_load_requirements')
    return {'missing_evidence':missing,'driver_delivery':delivery,'evidence_gate_rejected':bool(missing),
            'contract_verified':False,'hardware_tested':False,'wifi_verified':False,'hotspot_verified':False,
            'scope':'Candidate filename inventory and explicit evidence claims only; no HAL/ioctl/firmware or runtime validation'}


def collect_text(root,manifest):
    rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Sample hash changed: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        rows.append({'path':path,'sha256':item['sha256'],'lines':[{'line':n,'text':s} for n,s in enumerate(data.decode(errors='replace').splitlines(),1) if any(w in s.lower() for w in ('wifi','wlan','cnss','80211'))]})
    return rows


def main():
    root=pathlib.Path(__file__).resolve().parent.parent
    base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text())
    text=collect_text(base/'selected-vendor',manifest)
    report={'sample_role':'Non-Miku wayne comparison only; current user vendor unknown','contract':assess([x['path'] for x in manifest['extracted']]),'text_evidence':text,'absence_meaning':'Not selected/extracted; no claim of missing full-vendor files or hardware absence','module_note':'modules_built=false cannot establish absence of builtin driver','kernel_6_6_delivery':'unknown'}
    out=root/'research/wifi-contract-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
