#!/usr/bin/env python3
"""Inventory saved declarations, not runtime availability or firmware compatibility."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]

def main():
    tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_6_6_gate_integration'))
    if not tests.wasSuccessful():raise SystemExit(1)
    paths=['research/base-miku-a15/kernel.config','research/higher-kernel/6.6/arch/arm64/configs/sdm660_defconfig','research/higher-kernel/6.6/arch/arm64/boot/dts/qcom/sdm660-xiaomi-jasmine.dts','research/base-miku-a15/vendor/etc/ueventd.rc','research/base-miku-a15/system/system/etc/ueventd.rc','research/base-miku-a15/vendor/etc/init/hw/init.target.rc','research/gpu-allocator-stage/lineage-wayne/selected-vendor/etc/init/hw/init.qcom.rc','research/gpu-allocator-stage/lineage-wayne/selected-vendor/etc/fstab.qcom']
    pattern=re.compile(r'CONFIG_(?:REMOTEPROC|RPMSG|QCOM_(?:Q6|WCNSS|SMEM|GLINK|IPA)|MSM_(?:PIL|SUBSYSTEM)|FW_LOADER|EXTRA_FIRMWARE)|firmware-name|firmware_directories|boot_adsp|boot_slpi|/sys/module/(?:pil|peripheral|subsystem)|firmware_mnt|/vendor/dsp')
    sources=[]
    for name in paths:
        p=ROOT/name;blob=p.read_bytes();sources.append({'path':name,'sha256':hashlib.sha256(blob).hexdigest(),'scope':'saved source/reference only, NOT actual user board/runtime','matches':[{'line':n,'text':line} for n,line in enumerate(blob.decode().splitlines(),1) if pattern.search(line)]})
    lock=json.loads((ROOT/'config/kernel-6.6-experiment.json').read_text())
    comparisons=[]
    for relative in ('arch/arm64/configs/sdm660_defconfig','arch/arm64/boot/dts/qcom/sdm660-xiaomi-jasmine.dts'):
        expected=next(x['sha256'] for x in lock['files'] if x['path']==relative)
        actual=hashlib.sha256((ROOT/'research/higher-kernel/6.6'/relative).read_bytes()).hexdigest();comparisons.append({'path':relative,'matches_pinned_input':actual==expected,'sha256':actual})
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline':'9cc0173','tests_passed':tests.testsRun,'priority_gap':'Saved defconfig declares modular remoteproc/IPA dependencies while build delivers no modules; final config, firmware and actual wayne binding still absent','sources':sources,'pin_comparison':comparisons,'modules_built_recorded':json.loads((ROOT/'artifacts/kernel-6.6-allocator-probe.json').read_text())['modules_built'],'actual_board_firmware_verified':False,'hardware_tested':False,'preflight':{},'preservation':[],'next':'Collect real current DTB, firmware inventory/paths, generated config and remoteproc runtime/logs; do not translate foreign firmware-name into wayne requirements','quota':'Realtime unavailable; user snapshot 67%/82%; no precise control claim'}
    for tool in ('ci_kernel_66_probe.py','ci_allocator_implementation.py'):
        result=subprocess.run([sys.executable,str(ROOT/'tools'/tool),'--preflight'],cwd=ROOT,capture_output=True,text=True);report['preflight'][tool]=result.returncode
        if result.returncode!=2:raise ValueError('DTB gate unexpectedly unblocked')
    for e in json.loads((ROOT/'research/vendor-module-contract-stage/checkpoint.json').read_text())['preservation']:
        if hashlib.sha256((ROOT/e['path']).read_bytes()).hexdigest()!=e['sha256']:raise ValueError('Preserved material changed')
        report['preservation'].append(e)
    out=ROOT/'research/remoteproc-contract-stage';out.mkdir(parents=True,exist_ok=True);(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
