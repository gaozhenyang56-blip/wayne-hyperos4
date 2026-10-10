#!/usr/bin/env python3
"""An init permission request is not proof of the active Sensors transport."""
import hashlib
import json
import pathlib


def assess(paths,transport_binding_verified=False,calibration_delivery_verified=False):
    if any(type(x) is not bool for x in (transport_binding_verified,calibration_delivery_verified)):
        raise ValueError('Evidence flags must be explicit booleans')
    hal=[p for p in paths if pathlib.PurePosixPath(p).name.startswith(('sensors.','android.hardware.sensors')) and p.endswith(('.so','-service'))]
    config=[p for p in paths if ('sensors' in pathlib.PurePosixPath(p).parts or pathlib.PurePosixPath(p).name.startswith('sensors.')) and p.endswith(('.conf','.ini','.xml'))]
    missing=[]
    if not hal:missing.append('sensors_hal_or_vendor_library')
    if not config:missing.append('sensors_configuration')
    if not transport_binding_verified:missing.append('actual_transport_driver_binding_and_kernel_evidence')
    if not calibration_delivery_verified:missing.append('calibration_inventory_and_requirements')
    return {'missing_evidence':missing,'evidence_gate_rejected':bool(missing),'contract_verified':False,
            'hardware_tested':False,'sensors_verified':False,'sensors_function_verified':False,
            'scope':'Candidate filenames and explicit evidence claims only; no HAL version, transport, ioctl or runtime validation'}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent;base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text());rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(base/'selected-vendor'/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Sample hash changed: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        rows.append({'path':path,'sha256':item['sha256'],'lines':[{'line':n,'text':s} for n,s in enumerate(data.decode(errors='replace').splitlines(),1) if any(w in s.lower() for w in ('sensor','sns','boot_slpi','/dev/input','/dev/iio','/sys/bus/iio'))]})
    report={'sample_role':'Non-Miku wayne comparison only; current vendor unknown','contract':assess([x['path'] for x in manifest['extracted']]),'text_evidence':rows,'absence_meaning':'Not selected/extracted; not proof of absent full-vendor files or hardware','active_transport':'unknown; init requests do not select an IIO/input/sensor-hub binding'}
    out=root/'research/sensors-contract-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
