#!/usr/bin/env python3
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_input_contract'))
if not r.wasSuccessful():raise SystemExit(1)
cli=subprocess.run([sys.executable,'tools/audit_input_contract.py'],cwd=root);assert cli.returncode==2
checks=[]
for p in ('research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','research/usb-charging-stage/checkpoint.json'):
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','c077544:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_c077544':True})
config=(root/'research/base-miku-a15/kernel.config').read_text().splitlines()
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'c077544','target':'China wayne/SDM660 stock static partitions','tests_passed':r.testsRun,'sample_exit':cli.returncode,'preservation':checks,'historical_4_19':{'actual_build_configuration':False,'user_target_baseline':False,'lines':[{'line':n,'text':s} for n,s in enumerate(config,1) if s in ('CONFIG_INPUT=y','CONFIG_INPUT_EVDEV=y','CONFIG_KEYBOARD_GPIO=y')]},'kernel_6_6':'No audited actual touch/GPIO/event firmware and config binding; generic configuration does not establish hardware bringup','hardware_tested':False,'kernel_rebuilt':False,'new_flashable_package':False,'next':'Collect actual China wayne touch identity, input layouts/fallback, DTB, event/driver/permissions and firmware delivery plus boot/AVC evidence','quota':'Realtime unavailable; user snapshot 68%/95%; no precise control claim'}
(root/'research/input-contract-stage/checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print('2 tests passed; sample refusal 2; 5 prior evidence files preserved')
