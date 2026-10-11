#!/usr/bin/env python3
"""Short offline verification and preservation check."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_fingerprint_contract'))
if not r.wasSuccessful():raise SystemExit(1)
cli=subprocess.run([sys.executable,'tools/audit_fingerprint_contract.py'],cwd=root);assert cli.returncode==2
checks=[]
for p in ('research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','research/radio-contract-stage/checkpoint.json'):
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','4efaf4c:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_4efaf4c':True})
config=(root/'research/base-miku-a15/kernel.config').read_text().splitlines()
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'4efaf4c','target':'China wayne/SDM660 stock static partitions','tests_passed':r.testsRun,'sample_exit':cli.returncode,'preservation':checks,'historical_4_19':{'actual_build_configuration':False,'user_target_baseline':False,'lines':[{'line':n,'text':s} for n,s in enumerate(config,1) if s in ('CONFIG_QSEECOM=y','CONFIG_SPI=y','CONFIG_INPUT_EVDEV=y')]},'kernel_6_6':'No audited fingerprint/TEE/device binding; generic configs or module absence do not establish sensor compatibility','hardware_tested':False,'kernel_rebuilt':False,'new_flashable_package':False,'next':'Collect actual China wayne HAL/service, sensor identity and DTB, DAC/SELinux/AVC and TEE delivery requirements','quota':'Realtime unavailable; user snapshot 81%/97%; no precise control claim'}
(root/'research/fingerprint-contract-stage/checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print('3 tests passed; sample refusal 2; 5 prior evidence files preserved')
