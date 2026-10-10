#!/usr/bin/env python3
"""Bounded offline tests and preservation check; no kernel build."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
root=pathlib.Path(__file__).resolve().parent.parent
out=root/'research/bluetooth-contract-stage';out.mkdir(parents=True,exist_ok=True)
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_bluetooth_contract'))
if not r.wasSuccessful():raise SystemExit(1)
cli=subprocess.run([sys.executable,'tools/audit_bluetooth_contract.py'],cwd=root);assert cli.returncode==2
paths=['research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','research/wifi-contract-stage/checkpoint.json']
checks=[]
for p in paths:
    data=(root/p).read_bytes();assert data==subprocess.check_output(['git','show','471f71d:'+p],cwd=root)
    checks.append({'path':p,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_471f71d':True})
lines=(root/paths[0]).read_text().splitlines()
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'471f71d','target':'China wayne/SDM660 stock static partitions','tests_passed':r.testsRun,'sample_cli_exit':cli.returncode,'preservation':checks,'historical_4_19':{'actual_build_configuration':False,'user_target_baseline':False,'lines':[{'line':n,'text':s} for n,s in enumerate(lines,1) if s in ('CONFIG_BT=y','# CONFIG_BT_HCIUART is not set','CONFIG_MSM_BT_POWER=y')],'meaning':'Not proof of active HCI/UART transport or runtime conflict'},'kernel_6_6':'modules_built=false and early modules/firmware loading not integrated; actual Bluetooth configuration/transport unknown, builtin or userspace path not ruled out','hardware_tested':False,'full_kernel_rebuilt':False,'flashable_package_created':False,'next':'Collect actual current HAL/config and dependencies, firmware delivery, module/builtin inventory, DTB, transport binding and Bluetooth/AVC logs','quota':'Realtime usage unavailable; user snapshot 88%/35%; no precise control claim'}
(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print('3 tests passed; sample refusal 2; prior evidence preserved')
