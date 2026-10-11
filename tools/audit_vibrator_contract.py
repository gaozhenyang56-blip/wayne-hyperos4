#!/usr/bin/env python3
"""Alternative haptic backends require evidence, not all interfaces at once."""
import hashlib
import json
import pathlib


def assess(paths,backend='unknown',current_device_driver_binding_verified=False,service_policy_binding_verified=False):
    if backend not in ('unknown','timed_output','led_class','input_ff','vendor'):raise ValueError('Explicit backend evidence required')
    if any(type(x) is not bool for x in (current_device_driver_binding_verified,service_policy_binding_verified)):
        raise ValueError('Evidence flags must be explicit booleans')
    hal=[p for p in paths if pathlib.PurePosixPath(p).name.startswith(('vibrator.','android.hardware.vibrator')) and p.endswith(('.so','-service'))]
    missing=[]
    if not hal:missing.append('vibrator_hal_or_legacy_library')
    if backend=='unknown':missing.append('actual_haptic_backend_requirements')
    if not current_device_driver_binding_verified:missing.append('current_china_wayne_driver_dtb_and_node_binding')
    if not service_policy_binding_verified:missing.append('actual_service_delivery_dac_selinux_binding')
    return {'backend_claim':backend,'missing_evidence':missing,'evidence_gate_rejected':bool(missing),
            'contract_verified':False,'hardware_tested':False,'vibration_verified':False,'haptic_effects_verified':False,
            'scope':'Candidate filenames and explicit evidence claims only; no HAL version, drive parameters or runtime validation'}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent;base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text());rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(base/'selected-vendor'/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Changed sample: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        rows.append({'path':path,'sha256':item['sha256'],'lines':[{'line':n,'text':s} for n,s in enumerate(data.decode(errors='replace').splitlines(),1) if any(w in s.lower() for w in ('vibrat','haptic','timed_output','force-feedback'))]})
    report={'sample_role':'Non-Miku wayne comparison only; current China vendor unknown','contract':assess([x['path'] for x in manifest['extracted']]),'text_evidence':rows,'absence_meaning':'Not extracted; not proof of missing full-vendor files or unsupported hardware','service_note':'Standalone service or legacy library integration must be evidenced; no HAL version assumption'}
    out=root/'research/vibrator-contract-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
