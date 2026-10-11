#!/usr/bin/env python3
"""Read existing evidence only; no module copying/loading/signing/building."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

def main():
    tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_6_6_gate_integration'))
    if not tests.wasSuccessful():raise SystemExit(1)
    config=ROOT/'research/base-miku-a15/kernel.config'
    symbols=('MODULES','MODVERSIONS','MODULE_SIG','MODULE_SIG_FORCE','MODULE_SIG_ALL','MODULE_SIG_HASH','MODULE_SIG_KEY','LOCALVERSION')
    declarations={}
    for symbol in symbols:
        lines=[line for line in config.read_text().splitlines() if line.startswith('CONFIG_'+symbol+'=') or line=='# CONFIG_'+symbol+' is not set']
        declarations[symbol]=lines or ['not recorded']
    roots=('research/base-miku-a15','research/gpu-allocator-stage/lineage-wayne/selected-vendor')
    inventory={}
    for name in roots:
        folder=ROOT/name
        inventory[name]={'scope':'local extracted material only, not full actual-device vendor','module_files':[str(p.relative_to(ROOT)) for p in folder.rglob('*.ko')], 'dependency_files':[str(p.relative_to(ROOT)) for p in folder.rglob('modules.*')]}
    refs=[]
    for name in ('research/base-miku-a15/vendor/etc/init','research/gpu-allocator-stage/lineage-wayne/selected-vendor/etc/init'):
        for file in (ROOT/name).rglob('*.rc'):
            for number,line in enumerate(file.read_text(errors='replace').splitlines(),1):
                stripped=line.strip()
                if stripped.startswith(('insmod ', 'modprobe ')) or ('/vendor/bin/modprobe' in stripped and not stripped.startswith('#')):
                    refs.append({'path':str(file.relative_to(ROOT)),'line':number,'text':stripped,'runtime_execution_verified':False})
    probe=json.loads((ROOT/'artifacts/kernel-6.6-allocator-probe.json').read_text())
    provenance=json.loads((ROOT/'research/base-miku-a15/kernel-config.json').read_text())
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'5b20e27','tests_passed':tests.testsRun,'priority_gap':'No actual-current-wayne module inventory/vermagic/symbol CRC/signature evidence; 6.6 modules not built and ABI not established','historical_config_declarations':declarations,'historical_config_provenance':provenance,'historical_config_is_actual_build_config':False,'kernel_66_release_recorded':probe['kernel_release'],'kernel_66_modules_built_recorded':probe['modules_built'],'kernel_66_local_generated_config_available':(ROOT/'sources/kernel-6.6-probe/out/.config').exists(),'kernel_66_local_symvers_available':(ROOT/'sources/kernel-6.6-probe/out/Module.symvers').exists(),'inventories':inventory,'historical_load_requests':refs,'actual_user_vendor_available':False,'vendor_dlkm_actual_presence':'unknown; no actual mount/partition inventory','gki_kmi_qualified':False,'module_abi_verified':False,'hardware_tested':False,'preflight':{},'preservation':[],'next':'Collect actual-device UTS/config/modules/dep/symbols/signature and loader logs; keep DTB block and boot-contract gap unresolved','quota':'Realtime unavailable; user snapshot 89%/85%; no precise control claim'}
    for name in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
        result=subprocess.run([sys.executable,str(ROOT/'tools'/name),'--preflight'],cwd=ROOT,capture_output=True,text=True)
        report['preflight'][name]=result.returncode
        if result.returncode!=2:raise ValueError('DT identity gate unexpectedly unblocked')
    for item in json.loads((ROOT/'research/boot-contract-6.6-stage/checkpoint.json').read_text())['preservation']:
        if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Preserved result changed')
        report['preservation'].append(item)
    out=ROOT/'research/vendor-module-contract-stage';out.mkdir(parents=True,exist_ok=True)
    (out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
