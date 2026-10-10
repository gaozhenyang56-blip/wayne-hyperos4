#!/usr/bin/env python3
"""Reproduce a read-only comparison; no runtime or hardware compatibility claim."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
from audit_graphics_contract import assess, collect

ROOT=pathlib.Path(__file__).resolve().parent.parent

def main():
    out=ROOT/'research/display-contract-stage';out.mkdir(parents=True,exist_ok=True)
    base=ROOT/'research/gpu-allocator-stage/lineage-wayne'
    manifest=json.loads((base/'selected-files.json').read_text())
    vendor=base/'selected-vendor'
    rows=collect(vendor,manifest)
    profile=json.loads((ROOT/'config/kernel-6.6-graphics-profile.json').read_text())
    kernel=json.loads((ROOT/'artifacts/kernel-6.6-allocator-probe.json').read_text())
    if profile['provided_legacy_abis'] != kernel['provided_legacy_graphics_abis']:
        raise ValueError('Saved kernel report and profile capability claims disagree')
    assessment=assess(rows,profile)
    if not assessment['legacy_pairing_rejected']:
        raise ValueError('Reference vendor legacy ABI rejection disappeared')
    text_evidence=[]
    for entry in manifest['extracted']:
        path=entry['path']
        if path=='build.prop' or ('graphics.' in path and path.endswith('.rc')):
            data=(vendor/path).read_bytes()
            if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Changed '+path)
            lines=[]
            for number,line in enumerate(data.decode(errors='replace').splitlines(),1):
                if any(word in line for word in ('surface_flinger','display.','gralloc.','hardware.egl','service ','interface ','group ','user ','onrestart','writepid')):
                    lines.append({'line':number,'text':line})
            text_evidence.append({'path':path,'sha256':entry['sha256'],'lines':lines})
    old={ '__name__':'baseline_audit' }
    exec(subprocess.check_output(['git','show','18d4c6b:tools/audit_graphics_contract.py'],cwd=ROOT,text=True),old)
    malformed=json.loads(json.dumps(profile))
    malformed['provided_legacy_abis']={k:'false' for k in ('kgsl','ion','msm_fb')}
    old_bypass=not old['assess'](rows,malformed)['legacy_pairing_rejected']
    if not old_bypass:raise ValueError('Baseline regression not reproduced')
    try:assess(rows,malformed)
    except ValueError:fixed_reject=True
    else:raise ValueError('Malformed flags bypassed current audit')
    suite=unittest.defaultTestLoader.loadTestsFromName('test_display_contract_flags')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    command=[sys.executable,'tools/audit_graphics_contract.py',str(vendor),str(base/'selected-files.json'),'config/kernel-6.6-graphics-profile.json',str(out/'graphics-contract.json'),'--reject-legacy-pairing']
    refusal=subprocess.run(command,cwd=ROOT)
    if refusal.returncode!=2:raise ValueError('Expected fail-fast exit 2')
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'18d4c6b','target':'China wayne/SDM660 stock static partitions','sample_role':'non-Miku wayne comparison only; user current vendor unknown','text_evidence':text_evidence,'profile_matches_saved_kernel_claims':True,'contract':assessment,'tests':{'passed':result.testsRun,'baseline_false_string_bypass_reproduced':old_bypass,'fixed_malformed_flags_rejected':fixed_reject,'actual_sample_refusal_exit':refusal.returncode},'hardware_tested':False,'display_verified':False,'boot_verified':False,'next_evidence':['Current wayne vendor binaries and 32/64-bit dependency inventory with hashes','Actual wayne DTB and display/power/clock/IOMMU dependencies','Device nodes, DAC/SELinux labels, service registrations and properties','SurfaceFlinger/HWC logs, buffer handles, modifiers, sync/fence and relevant AVC evidence'],'remaining':['SELinux','display/GPU','camera','audio','encryption','boot']}
    (out/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['tests']))

if __name__=='__main__':main()
