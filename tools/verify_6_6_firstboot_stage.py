#!/usr/bin/env python3
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_6_6_firstboot'))
if not r.wasSuccessful():raise SystemExit(1)
cli=subprocess.run([sys.executable,'tools/audit_6_6_firstboot.py'],cwd=root);assert cli.returncode==2
checks=[]
for p in ('research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','config/sdm660-xiaomi-wayne-6.6.dts','config/kernel-6.6-experiment.json','config/wayne-stock-static.json','research/boot-static-stage/audit.json'):
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','bb6dba9:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_bb6dba9':True})
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'bb6dba9','tests_passed':r.testsRun,'sample_exit':cli.returncode,'preservation':checks,'hardware_tested':False,'kernel_rebuilt':False,'new_flashable_package':False,'next':'Obtain actual China wayne DTB/partition/boot/vendor provenance, then board-specific DT differences before packaging; no register guesses','quota':'Realtime unavailable; user snapshot 89%/93%; no precise control claim'}
(root/'research/firstboot-6.6-stage/checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print('2 tests passed; current 6.6 board rejected 2; 8 baseline files preserved')
