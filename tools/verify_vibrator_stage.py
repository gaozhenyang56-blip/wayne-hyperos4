#!/usr/bin/env python3
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_vibrator_contract'))
if not r.wasSuccessful():raise SystemExit(1)
cli=subprocess.run([sys.executable,'tools/audit_vibrator_contract.py'],cwd=root);assert cli.returncode==2
checks=[]
for p in ('research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','research/input-contract-stage/checkpoint.json'):
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','4f45447:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_4f45447':True})
config=(root/'research/base-miku-a15/kernel.config').read_text().splitlines()
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'4f45447','target':'China wayne/SDM660 stock static partitions','tests_passed':r.testsRun,'sample_exit':cli.returncode,'preservation':checks,'historical_4_19':{'actual_build_configuration':False,'user_target_baseline':False,'lines':[{'line':n,'text':s} for n,s in enumerate(config,1) if s in ('CONFIG_ANDROID_TIMED_OUTPUT=y','CONFIG_LEDS_CLASS=y','# CONFIG_INPUT_FF_MEMLESS is not set')]},'kernel_6_6':'No audited actual vibrator HAL/backend/service-policy binding; generic configuration or module absence not hardware proof','hardware_tested':False,'kernel_rebuilt':False,'new_flashable_package':False,'next':'Collect actual China wayne vibrator HAL/service, driver/DTB/nodes and DAC/SELinux plus boot/call/AVC evidence without issuing haptic requests','quota':'Realtime unavailable; user snapshot 98%/94%; no precise control claim'}
(root/'research/vibrator-contract-stage/checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print('2 tests passed; sample refusal 2; 5 prior evidence files preserved')
