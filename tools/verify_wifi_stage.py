#!/usr/bin/env python3
"""Short offline tests and evidence preservation, without a kernel build."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
out=root/'research/wifi-contract-stage';out.mkdir(parents=True,exist_ok=True)
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_wifi_contract'))
if not r.wasSuccessful():raise SystemExit(1)
cli=subprocess.run([sys.executable,'tools/audit_wifi_contract.py'],cwd=root);assert cli.returncode==2
paths=['research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','research/camera-contract-stage/checkpoint.json']
checks=[]
for p in paths:
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','4e2c24b:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_4e2c24b':True})
config=(root/paths[0]).read_text().splitlines()
rows=[{'line':n,'text':s} for n,s in enumerate(config,1) if s in ('CONFIG_CFG80211=y','# CONFIG_MAC80211 is not set','CONFIG_WLAN=y')]
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'4e2c24b','target':'China wayne/SDM660 stock static partitions','tests_passed':r.testsRun,'sample_cli_exit':cli.returncode,'preservation':checks,'historical_4_19':{'actual_build_configuration':False,'user_target_baseline':False,'lines':rows,'meaning':'Generic cfg80211/WLAN and disabled mac80211 do not establish fullmac/softmac implementation or runtime ability'},'kernel_6_6':'Saved reports: modules_built=false and early modules/firmware not integrated; actual wireless configuration and delivery unknown','hardware_tested':False,'full_kernel_rebuilt':False,'flashable_package_created':False,'next':'Collect actual current vendor Wi-Fi HAL/config, firmware and module/builtin inventories, actual kernel config/DTB and nl80211/service/AVC logs','quota':'Realtime usage unavailable; user snapshot 96%/37%; no precise control claim'}
(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n')
print('3 tests passed; sample exit 2; builtin/module distinction preserved; old evidence unchanged')
