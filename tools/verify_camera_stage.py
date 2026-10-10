#!/usr/bin/env python3
"""Bounded offline verification; no kernel build or device access."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest
ROOT=pathlib.Path(__file__).resolve().parent.parent
out=ROOT/'research/camera-contract-stage'
suite=unittest.defaultTestLoader.loadTestsFromName('test_camera_contract')
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():raise SystemExit(1)
cmd=[sys.executable,'tools/audit_camera_contract.py','research/gpu-allocator-stage/lineage-wayne/selected-vendor','research/gpu-allocator-stage/lineage-wayne/selected-files.json',str(out/'audit.json')]
refusal=subprocess.run(cmd,cwd=ROOT);assert refusal.returncode==2
paths=['research/base-miku-a15/kernel.config','research/base-miku-a15/kernel-config.json','artifacts/kernel-6.6-allocator-probe.json','artifacts/kernel-6.6-probe.json','research/audio-contract-stage/checkpoint.json']
checks=[]
for path in paths:
    data=(ROOT/path).read_bytes();assert data==subprocess.check_output(['git','show','5ad1636:'+path],cwd=ROOT)
    checks.append({'path':path,'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_5ad1636':True})
config=(ROOT/paths[0]).read_text().splitlines()
keys=('CONFIG_MEDIA_SUPPORT=','CONFIG_MEDIA_CAMERA_SUPPORT=','CONFIG_MEDIA_CONTROLLER=','CONFIG_VIDEO_DEV=','CONFIG_VIDEO_V4L2_SUBDEV_API=','CONFIG_MSM_CAMERA=')
report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'5ad1636','target':'China wayne/SDM660 stock static partitions','tests_passed':result.testsRun,'actual_sample_gate_exit':refusal.returncode,'preservation':checks,'kernel_4_19':{'actual_build_configuration':False,'user_target_baseline':False,'historical_embedded_config_only':True,'lines':[{'line':n,'text':s} for n,s in enumerate(config,1) if s.startswith(keys)]},'kernel_6_6':'Saved reports explicitly mark downstream camera ABI unverified; no audited media/video/subdev topology','hardware_tested':False,'full_kernel_rebuilt':False,'flashable_package_created':False,'next':'Obtain actual current wayne vendor HAL/config and dependencies, DTB, node labels and media graph, camera service and AVC logs','quota':'Realtime usage unavailable; user snapshot 44%/38%; no precise control or assumed reset'}
(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n')
print('3 tests passed; actual sample gate exit 2; prior evidence unchanged')
