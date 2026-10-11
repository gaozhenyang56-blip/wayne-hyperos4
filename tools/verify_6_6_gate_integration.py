#!/usr/bin/env python3
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(['test_6_6_gate_integration','test_6_6_firstboot']))
if not r.wasSuccessful():raise SystemExit(1)
exits={}
for script in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
    p=subprocess.run([sys.executable,'tools/'+script,'--preflight'],cwd=root);assert p.returncode==2;exits[script]=p.returncode
checks=[]
for p in ('artifacts/kernel-6.6-probe.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/static-candidate-package.json','config/sdm660-xiaomi-wayne-6.6.dts','research/base-miku-a15/kernel.config'):
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','b11efe4:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_b11efe4':True})
out=root/'research/dt-gate-integration-stage';out.mkdir(parents=True,exist_ok=True)
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'b11efe4','tests_passed':r.testsRun,'actual_preflight_exit':exits,'preservation':checks,'kernel_rebuilt':False,'hardware_tested':False,'new_flashable_package':False,'next':'Obtain actual China wayne board reference before changing scaffold or gate; preflight has no bypass','quota':'Realtime unavailable; user snapshot 77%/91%; no precise control claim'}
(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print('5 tests passed; two real preflight entries rejected 2; no build or package')
