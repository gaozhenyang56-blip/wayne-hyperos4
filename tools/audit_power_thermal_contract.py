#!/usr/bin/env python3
"""Selected material gate, never a performance or thermal validation."""
import hashlib
import json
import pathlib


def assess(paths,node_binding_verified=False):
    if type(node_binding_verified) is not bool:raise ValueError('Node evidence must be an explicit boolean')
    groups={'power_hal':[],'thermal_hal':[],'powerhint_config':[],'thermal_config':[]}
    for path in paths:
        name=pathlib.PurePosixPath(path).name
        for kind in ('power','thermal'):
            if name.startswith((kind+'.','android.hardware.'+kind)) and name.endswith(('.so','-service')):groups[kind+'_hal'].append(path)
        if 'powerhint' in name.lower() and path.endswith(('.json','.xml','.conf')):groups['powerhint_config'].append(path)
        if name.lower().startswith('thermal') and path.endswith(('.conf','.json','.xml')):groups['thermal_config'].append(path)
    missing=[k for k,v in groups.items() if not v]
    if not node_binding_verified:missing.append('actual_sysfs_thermal_cpufreq_devfreq_binding')
    return {'candidate_inventory':groups,'missing_evidence':missing,'evidence_gate_rejected':bool(missing),
            'contract_verified':False,'hardware_tested':False,'performance_verified':False,'thermal_verified':False,'battery_life_verified':False,
            'scope':'Candidate filenames and explicit binding claim only; no HAL version, config semantics or runtime validation'}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent;base=root/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text());rows=[]
    for item in manifest['extracted']:
        path=item['path'];data=(base/'selected-vendor'/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Changed sample: '+path)
        if path not in ('build.prop','etc/init/hw/init.qcom.rc'):continue
        rows.append({'path':path,'sha256':item['sha256'],'lines':[{'line':n,'text':s} for n,s in enumerate(data.decode(errors='replace').splitlines(),1) if any(w in s.lower() for w in ('thermal','cpufreq','devfreq','powerhint'))]})
    report={'sample_role':'Non-Miku wayne comparison only; current vendor unknown','contract':assess([x['path'] for x in manifest['extracted']]),'text_evidence':rows,'absence_meaning':'Not selected/extracted; no claim of absent full-vendor files or unavailable hardware'}
    out=root/'research/power-thermal-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['contract'],indent=2))
    if report['contract']['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
