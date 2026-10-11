#!/usr/bin/env python3
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_usb_charging_contract'))
if not r.wasSuccessful():raise SystemExit(1)
cli=subprocess.run([sys.executable,'tools/audit_usb_charging_contract.py'],cwd=root);assert cli.returncode==2
checks=[]
for p in ('research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','research/fingerprint-contract-stage/checkpoint.json'):
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','b936d04:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_b936d04':True})
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'b936d04','target':'China wayne/SDM660 stock static partitions','tests_passed':r.testsRun,'sample_exit':cli.returncode,'preservation':checks,'historical_4_19':'Embedded defconfig only, not generated .config or current user baseline','kernel_6_6':'No audited actual USB/charging HAL-to-node binding; compiled prerequisites do not establish hardware bringup','hardware_tested':False,'kernel_rebuilt':False,'new_flashable_package':False,'next':'Obtain missing imported configs plus actual vendor health/USB HAL, charging config, DTB, nodes and boot/cable/AVC logs','quota':'Realtime unavailable; user snapshot 75%/96%; no precise control claim'}
(root/'research/usb-charging-stage/checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print('2 tests passed; sample refusal 2; 5 prior evidence files preserved')
