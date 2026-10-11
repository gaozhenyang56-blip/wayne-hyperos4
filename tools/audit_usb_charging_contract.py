#!/usr/bin/env python3
"""Reject missing USB init imports; closure is not charging or gadget validation."""
import hashlib
import json
import pathlib
import re


def assess_imports(text,selected_paths):
    selected=set(selected_paths);rows=[]
    for line_number,line in enumerate(text.splitlines(),1):
        match=re.match(r'^\s*import\s+(\S+)',line)
        if not match or 'usb' not in match[1].lower():continue
        target=match[1]
        literal=target.startswith('/vendor/') and not any(x in target for x in ('*','?','[','$','..'))
        relative=target[len('/vendor/'):] if literal else None
        rows.append({'line':line_number,'import':target,'selected_path':relative,'available':literal and relative in selected})
    missing=[row for row in rows if not row['available']]
    return {'usb_imports':rows,'missing_or_unresolved_imports':missing,'evidence_gate_rejected':not rows or bool(missing),
            'scope':'Direct USB init import availability only; not recursive runtime imports or HAL/kernel compatibility',
            'contract_verified':False,'hardware_tested':False,'charging_verified':False,'usb_data_verified':False,'adb_verified':False,'otg_verified':False}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent;base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text());rows=[];init=None
    for item in manifest['extracted']:
        path=item['path'];data=(base/'selected-vendor'/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Changed sample: '+path)
        if path=='etc/init/hw/init.qcom.rc':init=data.decode(errors='replace')
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        rows.append({'path':path,'sha256':item['sha256'],'lines':[{'line':n,'text':s} for n,s in enumerate(data.decode(errors='replace').splitlines(),1) if any(w in s.lower() for w in ('usb','charger','charging','power_supply','extcon','configfs','udc'))]})
    if init is None:raise ValueError('No reference init source')
    report={'sample_role':'Non-Miku wayne comparison only; current China vendor unknown','contract':assess_imports(init,[x['path'] for x in manifest['extracted']]),'text_evidence':rows,'remaining':['Actual China vendor USB/health HAL, service and charging configuration','Imported USB configs and any further imports','Actual DTB and UDC/configfs/power_supply/extcon/role binding, DAC/SELinux/AVC','Boot/cable logs; no protocol or power claims'],'absence_meaning':'Not selected/extracted, not absent from full vendor'}
    out=root/'research/usb-charging-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
