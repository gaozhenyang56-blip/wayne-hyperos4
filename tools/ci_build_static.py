#!/usr/bin/env python3
"""Rebuild the stock-size static wayne experiment; never convert partitions."""
import argparse
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys
import ci_build_candidate as ci
from install_static_wayne import STOCK
from package_static_candidate import NAME

ROOT=ci.ROOT
OUT=ROOT/'artifacts/experimental/static'
REPORT=ROOT/'research/static-wayne'
TAG='offline-static-20261009'

def stage(name):
    target=json.loads((ROOT/'config/project-requirements.json').read_text())['target_device']
    profile=json.loads((ROOT/'config/wayne-stock-static.json').read_text())
    if target['dynamic_partitions'] is not False or target['partition_conversion_authorized'] or profile['partition_sizes']!=STOCK:
        raise ValueError('Static target/unchanged partition requirement violated')
    OUT.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
    def python(tool,*args):ci.run(sys.executable,ROOT/'tools'/tool,*args)
    if name in ('tools','download','extract'):
        ci.stage(name)
        if name=='extract':python('unpack_boot.py',ci.BASE/'boot.img',ci.BASE)
    elif name=='build':
        python('build_system_overlay.py',ci.DONOR/'system',ROOT/'config/compatibility_matrix.5.xml',
               OUT/'system-overlay.tar','--device-matrix',ROOT/'config/compatibility_matrix.device.wayne.xml',
               '--metadata',ci.DONOR/'inode-metadata.json')
        python('repack_system_metadata.py',ci.DONOR/'system',ci.DONOR/'inode-metadata.json',OUT/'system-overlay.tar',OUT/'system.img')
        python('build_wayne_boot.py',ci.BASE/'boot.img',ci.DONOR/'ramdisk/init',OUT/'boot.img','--layout','stock-size-static')
        python('build_static_vendor.py',ci.BASE/'vendor',ci.BASE/'vendor.img',OUT/'vendor.img')
    elif name=='verify':
        for tool in ('test_static_layout.py','test_static_installer.py','test_static_package.py','test_native_versions.py','test_progress_sync.py'):
            python(tool)
        python('verify_static_candidate.py')
        for entry in json.loads((ROOT/'research/community-framework-origin-check.json').read_text())['files']:
            if ci.sha(ci.DONOR/'system/system'/entry['path'])!=entry['community_sha256']:
                raise ValueError('Framework input mismatch: '+entry['path'])
    elif name=='vintf':
        ci.stage('vintf')
        shutil.copyfile(ROOT/'research/wayne-vintf-check.json',REPORT/'vintf-check.json')
    elif name=='package':
        python('package_static_candidate.py','--build-commit',os.environ['GITHUB_SHA'])
        python('verify_split_zip.py',*sorted((ROOT/'artifacts/releases/static').glob('*.zip.*')),
               '--base',NAME+'/','--report',REPORT/'archive-check.json')
    elif name=='publish':
        repo=os.environ['GITHUB_REPOSITORY'];folder=ROOT/'artifacts/releases/static'
        check=subprocess.run(['gh','release','view',TAG,'--repo',repo],capture_output=True)
        if check.returncode:
            ci.run('gh','release','create',TAG,'--repo',repo,'--draft','--prerelease','--target',os.environ['GITHUB_SHA'],
                   '--title','wayne 原版静态分区 HyperOS 4 离线实验包（未真机验证）','--notes',
                   '适用于原版容量静态分区的 wayne 离线实验：不转换分区，不要求预装 Miku UI。boot/vendor 参考材料经过静态适配。必须先在 root ADB Recovery 检查实际分区，再进入 bootloader；安装器拒绝容量或布局不符。严格 SELinux 检查仍失败，启动、加密和硬件功能未知。分卷须合并后解压，详见 INSTALL.txt。')
        files=sorted(folder.glob('*.zip.*'))+[folder/'SHA256SUMS',folder/'stage/INSTALL.txt',folder/'stage/manifest.json']
        ci.run('gh','release','upload',TAG,*files,'--repo',repo,'--clobber')
        release=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/releases/tags/'+TAG],text=True))
        expected={p.name:{'size':p.stat().st_size,'sha256':ci.sha(p)} for p in files}
        assets={a['name']:a for a in release['assets']}
        for name,record in expected.items():
            asset=assets[name]
            if asset['size']!=record['size'] or asset.get('digest')!='sha256:'+record['sha256']:
                raise ValueError('Public asset size/digest mismatch: '+name)
        ci.run('gh','release','edit',TAG,'--repo',repo,'--draft=false','--prerelease','--latest=false','--target',os.environ['GITHUB_SHA'])
        release=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/releases/tags/'+TAG],text=True))
        if release['draft']:raise ValueError('Static release still a draft')
        (ROOT/'artifacts/static-release-publication.json').write_text(json.dumps({
            'url':release['html_url'],'tag':TAG,'draft':False,'prerelease':True,
            'build_commit':os.environ['GITHUB_SHA'],'assets_verified':True,'assets':expected,
            'layout':'stock-size-static','requires_miku_installed':False,'hardware_tested':False},indent=2)+'\n')
    else:raise ValueError('Unknown stage: '+name)

STAGES=[('tools','编译固定版本镜像工具','镜像工具准备完成。'),
        ('download','下载并校验供体和 wayne 参考材料','供体完整哈希和目标材料条目校验通过。'),
        ('extract','重建原始镜像并记录权限标签','原始镜像、inode 元数据和 runtime APEX 已提取。'),
        ('build','生成保持原版容量的静态 boot/system/vendor','三张静态镜像已生成，没有修改 GPT 或使用 rawdump。'),
        ('verify','完整核对静态镜像内容、元数据与安装拒绝条件','完整 system/vendor 和 boot 核验通过；硬件未测试，严格策略失败仍保留。'),
        ('vintf','核验目标 HAL 声明匹配','限定范围的 VINTF 核验通过，不代表 HAL 功能正常。'),
        ('package','生成静态分卷刷机包并完整读回','所有 ZIP 条目 CRC 和镜像哈希核验通过。'),
        ('publish','发布静态实验包并核验全部资产','五项 Release 资产的大小和哈希已核验，预发布已公开。')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage');a=p.parse_args();os.chdir(ROOT)
    if a.stage:stage(a.stage);return
    for i,(name,action,outcome) in enumerate(STAGES):
        following=STAGES[i+1][1] if i+1<len(STAGES) else '提供实验成品链接，保留未真机测试和运行时问题说明。'
        progress=ROOT/os.environ['WAYNE_PROGRESS_FILE'];progress.parent.mkdir(parents=True,exist_ok=True)
        with progress.open('a') as stream:
            stream.write('## '+datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n\n做了什么：开始'+action+'。\n\n发生了什么：云端进入本阶段。\n\n下一步：'+following+'。\n\n')
        ci.sync_progress()
        result=subprocess.run([sys.executable,'tools/record_step.py','--action',action+'。','--outcome',outcome,
            '--failure-note','本阶段失败，日志已保留；没有将失败记为通过。','--next',following,
            'cloud-static-'+name,'--',sys.executable,'tools/ci_build_static.py','--stage',name])
        ci.sync_progress()
        if result.returncode:raise SystemExit(result.returncode)

if __name__=='__main__':main()
