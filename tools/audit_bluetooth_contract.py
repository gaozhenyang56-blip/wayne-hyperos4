#!/usr/bin/env python3
"""An init permission request is not proof of the active Bluetooth transport."""
import hashlib
import json
import pathlib


def assess(paths,transport_binding_verified=False,firmware_delivery_verified=False):
    if any(type(x) is not bool for x in (transport_binding_verified,firmware_delivery_verified)):
        raise ValueError('Evidence flags must be explicit booleans')
    hal=[p for p in paths if pathlib.PurePosixPath(p).name.startswith(('bluetooth.','android.hardware.bluetooth','libbt-vendor.')) and p.endswith(('.so','-service'))]
    config=[p for p in paths if 'bluetooth' in pathlib.PurePosixPath(p).parts and p.endswith(('.conf','.ini','.xml'))]
    missing=[]
    if not hal:missing.append('bluetooth_hal_or_vendor_library')
    if not config:missing.append('bluetooth_configuration')
    if not transport_binding_verified:missing.append('actual_transport_driver_binding_and_kernel_evidence')
    if not firmware_delivery_verified:missing.append('firmware_delivery_inventory_and_requirements')
    return {'missing_evidence':missing,'evidence_gate_rejected':bool(missing),'contract_verified':False,
            'hardware_tested':False,'bluetooth_verified':False,'calls_verified':False,
            'scope':'Candidate filenames and explicit evidence claims only; no HAL version, transport, ioctl or runtime validation'}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent;base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text());rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(base/'selected-vendor'/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Sample hash changed: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        rows.append({'path':path,'sha256':item['sha256'],'lines':[{'line':n,'text':s} for n,s in enumerate(data.decode(errors='replace').splitlines(),1) if any(w in s.lower() for w in ('bluetooth','hci_','rfkill','ttyhs','msm_serial_hs','/sys/module/sco'))]})
    report={'sample_role':'Non-Miku wayne comparison only; current vendor unknown','contract':assess([x['path'] for x in manifest['extracted']]),'text_evidence':rows,'absence_meaning':'Not selected/extracted; not proof of absent full-vendor files or hardware','active_transport':'unknown; init permission requests do not select a UART/HCI/shared path'}
    out=root/'research/bluetooth-contract-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
