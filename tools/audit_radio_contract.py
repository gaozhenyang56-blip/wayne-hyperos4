#!/usr/bin/env python3
"""Radio material gate; a comparison vendor is not the current China wayne vendor."""
import hashlib
import json
import pathlib


def assess(paths,china_wayne_vendor_verified=False,modem_delivery_partition_verified=False,interface_binding_verified=False):
    flags=(china_wayne_vendor_verified,modem_delivery_partition_verified,interface_binding_verified)
    if any(type(x) is not bool for x in flags):raise ValueError('Evidence flags must be explicit booleans')
    hal=[p for p in paths if pathlib.PurePosixPath(p).name.startswith(('android.hardware.radio','radio.','libril','libqcril')) and p.endswith(('.so','-service'))]
    config=[p for p in paths if ('radio' in pathlib.PurePosixPath(p).parts or 'ril' in pathlib.PurePosixPath(p).name.lower()) and p.endswith(('.conf','.xml','.db','.json'))]
    missing=[]
    if not hal:missing.append('radio_hal_or_ril_binary')
    if not config:missing.append('ril_configuration')
    for verified,label in zip(flags,('current_china_wayne_vendor_provenance','modem_delivery_and_actual_partition_inventory','actual_rmnet_ipa_qrtr_remoteproc_or_other_binding')):
        if not verified:missing.append(label)
    return {'missing_evidence':missing,'evidence_gate_rejected':bool(missing),'contract_verified':False,'hardware_tested':False,
            'calls_verified':False,'sms_verified':False,'data_verified':False,'volte_verified':False,
            'scope':'Candidate filenames and explicit evidence claims only; no HAL version, modem ABI or runtime validation'}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent;base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text());rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(base/'selected-vendor'/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Changed sample: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        rows.append({'path':path,'sha256':item['sha256'],'lines':[{'line':n,'text':s} for n,s in enumerate(data.decode(errors='replace').splitlines(),1) if any(w in s.lower() for w in ('radio','ril','modem','rmnet','qrtr','remoteproc','qmi','/dev/ipa'))]})
    report={'sample_role':'Non-Miku wayne comparison only; current China vendor unknown','contract':assess([x['path'] for x in manifest['extracted']]),'text_evidence':rows,'absence_meaning':'Not selected/extracted; not proof of absent full-vendor files or unsupported hardware'}
    out=root/'research/radio-contract-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
