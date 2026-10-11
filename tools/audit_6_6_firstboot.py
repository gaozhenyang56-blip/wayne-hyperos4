#!/usr/bin/env python3
"""Board evidence gate, not a boot qualification or device-tree parser."""
import hashlib
import json
import pathlib
import re


def assess_board(dts,probe,evidence=None):
    foreign=[m.group(1) for m in re.finditer(r'^\s*#include\s+["<]([^">]*jasmine[^">]*)[">]',dts,re.M)]
    dtbs=[x for x in probe.get('outputs',[]) if x['path'].endswith('/sdm660-xiaomi-wayne.dtb')]
    reasons=[]
    if foreign:reasons.append('Direct jasmine board inheritance remains; compatible rename is not wayne binding evidence')
    if len(dtbs)!=1:reasons.append('Exactly one saved wayne DTB artifact hash required')
    source_hash=hashlib.sha256(dts.encode()).hexdigest()
    e=evidence if isinstance(evidence,dict) else {}
    bound=(e.get('target')=='China wayne/SDM660' and e.get('scope')=='board_bindings_against_actual_wayne_reference'
           and e.get('source_dts_sha256')==source_hash and len(dtbs)==1
           and e.get('artifact_dtb_sha256')==dtbs[0]['sha256']
           and isinstance(e.get('reference_sha256'),str) and re.fullmatch('[0-9a-f]{64}',e['reference_sha256']) is not None)
    if not bound:reasons.append('No artifact-bound current China wayne board/reference evidence')
    return {'priority_blocker':'Actual wayne board DT binding before boot packaging','foreign_includes':foreign,'source_dts_sha256':source_hash,
            'reasons':reasons,'evidence_gate_rejected':bool(reasons),'compiled_claim':probe.get('compiled'),
            'scope':'Direct include and artifact/reference provenance checks only; not full DTS/DTB semantics',
            'hardware_tested':False,'boot_verified':False,'flashable_qualified':False}


def main():
    root=pathlib.Path(__file__).resolve().parent.parent
    dts=(root/'config/sdm660-xiaomi-wayne-6.6.dts').read_text()
    probe=json.loads((root/'artifacts/kernel-6.6-allocator-probe.json').read_text())
    result=assess_board(dts,probe)
    out=root/'research/firstboot-6.6-stage/audit.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if result['evidence_gate_rejected']:raise SystemExit(2)

if __name__=='__main__':main()
