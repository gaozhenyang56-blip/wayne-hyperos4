#!/usr/bin/env python3
"""Input material gate; vendor-specific IDC is not universally required."""
import hashlib
import json
import pathlib


def assess(paths,current_device_identity_verified=False,event_config_binding_verified=False,policy_firmware_requirements_verified=False):
    flags=(current_device_identity_verified,event_config_binding_verified,policy_firmware_requirements_verified)
    if any(type(x) is not bool for x in flags):raise ValueError('Evidence flags must be explicit booleans')
    layouts=[p for p in paths if 'keylayout' in pathlib.PurePosixPath(p).parts and p.endswith('.kl')]
    optional=[p for p in paths if p.endswith(('.idc','.kcm'))]
    missing=[]
    if not layouts:missing.append('actual_keylayout_or_verified_system_fallback_inventory')
    for flag,label in zip(flags,('current_china_wayne_and_actual_touch_identity','actual_event_input_name_to_config_and_dtb_binding','actual_node_dac_selinux_and_firmware_requirements')):
        if not flag:missing.append(label)
    return {'keylayout_candidates':layouts,'optional_idc_kcm_candidates':optional,'missing_evidence':missing,'evidence_gate_rejected':bool(missing),
            'contract_verified':False,'hardware_tested':False,'touch_verified':False,'keys_verified':False,'gestures_verified':False,
            'scope':'Candidate inventory and explicit binding claims only; no layout semantics, coordinates, sensor identity or runtime validation'}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent;base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text());rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(base/'selected-vendor'/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Changed sample: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        rows.append({'path':path,'sha256':item['sha256'],'lines':[{'line':n,'text':s} for n,s in enumerate(data.decode(errors='replace').splitlines(),1) if any(w in s.lower() for w in ('touch','keylayout','keychars','/dev/input','/sys/class/input'))]})
    report={'sample_role':'Non-Miku wayne comparison only; current China vendor and touch identity unknown','contract':assess([x['path'] for x in manifest['extracted']]),'text_evidence':rows,'absence_meaning':'Not extracted; configurations may reside in system/product/odm/vendor; no claim of unsupported hardware','optional_config_note':'Missing IDC/KCM alone is not a compatibility failure; actual Android fallback and binding require evidence'}
    out=root/'research/input-contract-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
