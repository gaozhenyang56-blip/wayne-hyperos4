#!/usr/bin/env python3
"""Short offline verification with preserved baseline evidence."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_radio_contract'))
if not r.wasSuccessful():raise SystemExit(1)
cli=subprocess.run([sys.executable,'tools/audit_radio_contract.py'],cwd=root);assert cli.returncode==2
checks=[]
for p in ('research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','research/power-thermal-stage/checkpoint.json'):
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','1858697:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_1858697':True})
config=(root/'research/base-miku-a15/kernel.config').read_text().splitlines()
rows=[{'line':n,'text':s} for n,s in enumerate(config,1) if s.startswith(('CONFIG_QRTR=','CONFIG_QRTR_SMD=','CONFIG_QCOM_Q6V5_MSS=','CONFIG_RMNET','CONFIG_IPA=','CONFIG_REMOTEPROC='))]
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'1858697','target':'China wayne/SDM660 stock static partitions','tests_passed':r.testsRun,'sample_exit':cli.returncode,'preservation':checks,'historical_4_19':{'actual_build_configuration':False,'user_target_baseline':False,'lines':rows},'kernel_6_6':'No audited current Radio/vendor/modem binding; modules_built=false does not exclude builtin drivers; early module/firmware delivery not integrated','hardware_tested':False,'kernel_rebuilt':False,'new_flashable_package':False,'next':'Collect actual China wayne vendor HAL/RIL/config, modem delivery and partition inventory, actual DTB and boot/radio/AVC evidence','quota':'Realtime unavailable; user snapshot 93%/99%; no precise control claim'}
(root/'research/radio-contract-stage/checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print('2 tests passed; sample refusal 2; 5 prior evidence files preserved')
