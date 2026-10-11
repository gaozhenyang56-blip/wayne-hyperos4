#!/usr/bin/env python3
"""Build fingerprints and generic TEE directories are not sensor evidence."""
import hashlib
import json
import pathlib


def relevant_text(line):
    text=line.lower()
    return ('fingerprint' in text and 'build.fingerprint' not in text) or any(x in text for x in ('qtee','qsee'))


def assess(paths,device_sensor_identity_verified=False,node_policy_binding_verified=False,tee_delivery_binding_verified=False):
    flags=(device_sensor_identity_verified,node_policy_binding_verified,tee_delivery_binding_verified)
    if any(type(x) is not bool for x in flags):raise ValueError('Evidence flags must be explicit booleans')
    hal=[p for p in paths if pathlib.PurePosixPath(p).name.startswith(('fingerprint.','android.hardware.biometrics.fingerprint')) and p.endswith(('.so','-service'))]
    service=[p for p in paths if 'init' in pathlib.PurePosixPath(p).parts and 'fingerprint' in pathlib.PurePosixPath(p).name and p.endswith('.rc')]
    missing=[]
    if not hal:missing.append('fingerprint_hal')
    if not service:missing.append('fingerprint_service_declaration')
    for flag,label in zip(flags,('current_china_wayne_and_sensor_identity','actual_irq_input_spi_power_node_dac_selinux_binding','actual_tee_delivery_and_protocol_requirements')):
        if not flag:missing.append(label)
    return {'missing_evidence':missing,'evidence_gate_rejected':bool(missing),'contract_verified':False,'hardware_tested':False,'enrollment_verified':False,'recognition_verified':False,'unlock_verified':False,'scope':'Candidate filenames and explicit evidence claims only; no HAL version, TEE protocol or runtime validation'}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent;base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text());rows=[];excluded=[]
    for item in manifest['extracted']:
        path=item['path'];data=(base/'selected-vendor'/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Changed sample: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        lines=[]
        for n,s in enumerate(data.decode(errors='replace').splitlines(),1):
            if 'build.fingerprint' in s.lower():excluded.append({'path':path,'line':n,'reason':'Build identifier, not biometric sensor evidence'})
            if relevant_text(s):lines.append({'line':n,'text':s})
        rows.append({'path':path,'sha256':item['sha256'],'lines':lines})
    report={'sample_role':'Non-Miku wayne comparison only; current China vendor unknown','contract':assess([x['path'] for x in manifest['extracted']]),'text_evidence':rows,'excluded_metadata':excluded,'generic_tee_context':'QTEE/QSEE text is not fingerprint binding or protocol proof','absence_meaning':'Not extracted; not proof of absent full-vendor files or unsupported hardware'}
    out=root/'research/fingerprint-contract-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
