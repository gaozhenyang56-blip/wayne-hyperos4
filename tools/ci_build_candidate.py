#!/usr/bin/env python3
"""Rebuild and publish the offline candidate on an ordinary GitHub runner."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import zipfile

ROOT=pathlib.Path(__file__).resolve().parent.parent
DONOR=ROOT/'research/candidates/mi8937-os4'
BASE=ROOT/'research/base-miku-a15'
BIN=ROOT/'tools/local/usr/bin'


def run(*args, **kwargs):
    subprocess.run([str(x) for x in args],check=True,**kwargs)


def sha(path):
    with pathlib.Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def clone(name,url,commit):
    path=ROOT/'sources'/name;path.mkdir(parents=True,exist_ok=True)
    run('git','init',path)
    run('git','-C',path,'fetch','--depth=1',url,commit)
    run('git','-C',path,'checkout','--detach','FETCH_HEAD')


def require_rdp_target():
    requirements=json.loads((ROOT/'config/project-requirements.json').read_text())
    target=requirements.get('target_device',{})
    if target.get('dynamic_partitions') is False:
        raise ValueError('Current target is stock-size static wayne; obsolete Miku RDP build/publish is disabled')


def stage(name):
    if name in ('build','package','publish'):require_rdp_target()
    if name=='tools':
        clone('erofs-ci','https://github.com/erofs/erofs-utils.git','e625150a387e8a5eb2faae649d6454fbe597d404')
        folder=ROOT/'sources/erofs-ci'
        run('./autogen.sh',cwd=folder)
        run('./configure','--prefix='+str(ROOT/'tools/local/usr'),cwd=folder)
        run('make','-j4',cwd=folder);run('make','install',cwd=folder)
    elif name=='download':
        path=ROOT/'downloads/mi8937-hyperos4.zip';path.parent.mkdir(exist_ok=True)
        from download_verified import download
        download('https://drive.usercontent.google.com/download?id=1_Tu-HcN1PIz4PItm5vvCuh5FrjJpfDTX&export=download&confirm=t',
                 path,'1a9a9eb684e1174455ae3a84524de2e4f309ddc62e7dacae6565aa8d2dd14c39')
        if sha(path)!='1a9a9eb684e1174455ae3a84524de2e4f309ddc62e7dacae6565aa8d2dd14c39':
            raise ValueError('Community source ZIP hash mismatch')
        from inspect_ota import inspect
        inspect('https://downloads.sourceforge.net/project/divarelease/wayne_Vampire_v0.6.0/MikuUI-Vampire_v2-wayne-25020901-OFFICIAL.zip',BASE,
                ['boot.img','vendor.new.dat.br','vendor.transfer.list'])
    elif name=='extract':
        archive=ROOT/'downloads/mi8937-hyperos4.zip'
        DONOR.mkdir(parents=True,exist_ok=True)
        run(sys.executable,ROOT/'tools/rebuild_zip_block.py',archive,'system.new.dat','vendor.transfer.list',DONOR/'system.img')
        run(sys.executable,ROOT/'tools/convert_block_ota.py',BASE/'vendor.new.dat.br',BASE/'vendor.transfer.list','209600512',BASE/'vendor.img')
        if sha(DONOR/'system.img')!='235c0104a84ac3a9e896c48c15b0e7a3033ef64ebd988f07ed0ef34a3ed0b137':
            raise ValueError('Original community system hash mismatch')
        with zipfile.ZipFile(archive) as source:(DONOR/'boot.img').write_bytes(source.read('boot.img'))
        run(sys.executable,ROOT/'tools/unpack_boot.py',DONOR/'boot.img',DONOR)
        run(BIN/'fsck.erofs','--extract='+str(DONOR/'system'),'--no-preserve-owner',DONOR/'system.img')
        run(BIN/'fsck.erofs','--extract='+str(BASE/'vendor'),'--no-preserve-owner',BASE/'vendor.img')
        runtime=ROOT/'downloads/native-apex-audit'
        runtime.mkdir(exist_ok=True)
        with zipfile.ZipFile(DONOR/'system/system/apex/com.android.runtime.apex') as apex:
            (runtime/'runtime.img').write_bytes(apex.read('apex_payload.img'))
        run(BIN/'fsck.erofs','--extract='+str(runtime/'runtime'),'--no-preserve-owner',runtime/'runtime.img')
        from erofs_metadata import inventory
        (DONOR/'inode-metadata.json').write_text(json.dumps(inventory(DONOR/'system.img',str(BIN/'dump.erofs')),indent=2)+'\n')
    elif name=='build':
        run(sys.executable,ROOT/'tools/build_system_overlay.py',DONOR/'system',ROOT/'config/compatibility_matrix.5.xml',
            ROOT/'artifacts/experimental/overlay.tar','--device-matrix',ROOT/'config/compatibility_matrix.device.wayne.xml',
            '--metadata',DONOR/'inode-metadata.json')
        run(sys.executable,ROOT/'tools/build_wayne_boot.py',BASE/'boot.img',DONOR/'ramdisk/init',ROOT/'artifacts/experimental/boot.img')
        run(sys.executable,ROOT/'tools/repack_system_metadata.py',DONOR/'system',DONOR/'inode-metadata.json',
            ROOT/'artifacts/experimental/overlay.tar',ROOT/'artifacts/experimental/system.img')
    elif name=='verify':
        from erofs_metadata import inventory
        from install_wayne import GROUP_LIMIT
        image=ROOT/'artifacts/experimental/system.img';verified=ROOT/'downloads/verified-wayne-system'
        run(BIN/'fsck.erofs','--extract='+str(verified),'--no-preserve-owner',image)
        run(sys.executable,ROOT/'tools/verify_system_contents.py',DONOR/'system',verified,DONOR/'inode-metadata.json',
            ROOT/'artifacts/experimental/overlay.tar',ROOT/'research/wayne-system-content-check.json')
        old=json.loads((DONOR/'inode-metadata.json').read_text());new=inventory(image,str(BIN/'dump.erofs'))
        differences=[p for p,r in old['paths'].items() if any(r[k]!=new['paths'].get(p,{}).get(k)
                     for k in ('mode','uid','gid','xattrs_base64'))]
        report={'original_paths':len(old['paths']),'rebuilt_paths':len(new['paths']),
                'differences':differences,'success':not differences}
        (ROOT/'research/wayne-system-metadata-check.json').write_text(json.dumps(report,indent=2)+'\n')
        if differences:raise ValueError('Filesystem metadata mismatch')
        if image.stat().st_size+(BASE/'vendor.img').stat().st_size>GROUP_LIMIT:raise ValueError('Group overflow')
        # Validate that inherited policy evidence covers exactly these downloaded inputs.
        for relative in ['research/wayne-os4-policy/policy-check.json','research/wayne-os4-policy/runtime/policy-check.json']:
            for source,digest in json.loads((ROOT/relative).read_text())['inputs'].items():
                if sha(ROOT/source)!=digest:raise ValueError('Policy evidence input changed: '+source)
        from build_wayne_boot import cpio_records
        from unpack_boot import decode_ramdisk
        import struct
        data=(ROOT/'artifacts/experimental/boot.img').read_bytes();original=(BASE/'boot.img').read_bytes()
        page=struct.unpack_from('<I',data,36)[0];ks=struct.unpack_from('<I',data,8)[0];rs=struct.unpack_from('<I',data,16)[0]
        offset=page+((ks+page-1)//page)*page;kernel=data[page:page+ks];ramdisk=data[offset:offset+rs]
        if kernel!=original[page:page+ks] or data[64:576]!=original[64:576]:raise ValueError('Target boot kernel/cmdline changed')
        identity=hashlib.sha1()
        for payload in (kernel,ramdisk,b'',b''):identity.update(payload);identity.update(struct.pack('<I',len(payload)))
        if data[576:596]!=identity.digest():raise ValueError('Invalid boot ID')
        entries={n:c for n,f,c in cpio_records(decode_ramdisk(ramdisk))}
        if entries['init']!=(DONOR/'ramdisk/init').read_bytes():raise ValueError('Init mismatch')
        (ROOT/'research/wayne-boot-check.json').write_text(json.dumps({'success':True,'hardware_tested':False,
             'kernel_and_appended_dtb_preserved':True,'cmdline_preserved':True,'boot_id_verified':True,
             'boot_size':len(data),'boot_sha256':hashlib.sha256(data).hexdigest()},indent=2)+'\n')
        origin=json.loads((ROOT/'research/community-framework-origin-check.json').read_text())
        for entry in origin['files']:
            if sha(DONOR/'system/system'/entry['path'])!=entry['community_sha256']:raise ValueError('Framework input mismatch')
        shutil.rmtree(verified)
        run(sys.executable,ROOT/'tools/test_installer_offline.py')
        run(sys.executable,ROOT/'tools/test_native_versions.py')
        run(sys.executable,ROOT/'tools/test_progress_sync.py')
        run(sys.executable,ROOT/'tools/audit_native_versions.py',DONOR/'system',BASE/'vendor',
            ROOT/'downloads/native-apex-audit/runtime',ROOT/'research/wayne-os4-native-versions.json')
    elif name=='vintf':
        pins=json.loads((ROOT/'sources.lock.json').read_text())
        for name in ('libvintf','libbase','logging','fmt','tinyxml2','system-core','hidl-tools'):
            clone(name,pins[name]['url'],pins[name]['commit'])
        run(sys.executable,ROOT/'tools/build_vintf_checker.py')
        args=[ROOT/'tools/local/vintf_pair_check',BASE/'vendor/etc/vintf/manifest.xml',
              *sorted((BASE/'vendor/etc/vintf/manifest').glob('*.xml')),ROOT/'config/compatibility_matrix.5.xml',
              ROOT/'config/compatibility_matrix.device.wayne.xml',
              *sorted(p for p in (DONOR/'system/system/etc/vintf').glob('compatibility_matrix*.xml')
                      if p.name!='compatibility_matrix.device.xml')]
        result=subprocess.run([str(x) for x in args],capture_output=True,text=True)
        print(result.stdout+result.stderr)
        (ROOT/'research/wayne-vintf-check.json').write_text(json.dumps({'check':{'exit_code':result.returncode,
              'output':result.stdout+result.stderr},'hardware_tested':False,'hidl_inheritance_metadata_provided':False,
              'not_covered':['actual kernel configuration','APEX runtime','linker namespaces','HAL functionality']},indent=2)+'\n')
        if result.returncode:raise ValueError('Target HAL declaration mismatch')
    elif name=='package':
        run(sys.executable,ROOT/'tools/package_candidate.py','--build-commit',os.environ['GITHUB_SHA'])
        parts=sorted((ROOT/'artifacts/releases').glob('*.zip.*'))
        run(sys.executable,ROOT/'tools/verify_split_zip.py',*parts,'--report',ROOT/'research/candidate-archive-check.json')
    elif name=='publish':
        repo=os.environ['GITHUB_REPOSITORY'];tag='offline-20261006'
        check=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True)
        if check.returncode:
            run('gh','release','create',tag,'--repo',repo,'--draft','--prerelease','--target',os.environ['GITHUB_SHA'],
                '--title','wayne HyperOS 4 离线实验包（未真机验证）','--notes',
                '无真机测试。仅供已采用 Miku retrofit 动态分区布局的 wayne 实验。严格 SELinux 检查仍失败，运行时问题未完全核验。')
        files=sorted((ROOT/'artifacts/releases').glob('*.zip.*'))+[ROOT/'artifacts/releases/SHA256SUMS',
              ROOT/'artifacts/releases/stage/INSTALL.txt',ROOT/'artifacts/releases/stage/manifest.json']
        run('gh','release','upload',tag,*files,'--repo',repo,'--clobber')
        releases=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/releases'],text=True))
        release=next(r for r in releases if r['tag_name']==tag)
        expected=json.loads((ROOT/'artifacts/candidate-package.json').read_text())['parts']
        assets={a['name']:a for a in release['assets']}
        for name,record in expected.items():
            asset=assets[name]
            if asset['size']!=record['size'] or asset.get('digest')!='sha256:'+record['sha256']:
                raise ValueError('Remote asset size/digest mismatch: '+name)
        run('gh','release','edit',tag,'--repo',repo,'--draft=false','--prerelease','--latest=false','--target',os.environ['GITHUB_SHA'])
        release=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/releases/tags/'+tag],text=True))
        if release['draft']:raise ValueError('Release is still a draft after publication')
        (ROOT/'artifacts/release-publication.json').write_text(json.dumps({'url':release['html_url'],
              'tag':tag,'draft':False,'prerelease':True,'build_commit':os.environ['GITHUB_SHA'],'assets_verified':True,'hardware_tested':False,
              'parts':expected},indent=2)+'\n')
    else:raise ValueError('Unknown stage: '+name)


STAGES=[('tools','编译固定版本的镜像工具','镜像工具准备完成。'),
        ('download','取得并校验社区供体和 wayne 原包材料','完整供体哈希和底包条目 CRC 校验通过。'),
        ('extract','重建系统与目标 vendor，提取原始 inode 元数据','原始镜像已正确重建，原始标签及权限已记录。'),
        ('build','生成保留 wayne 硬件支持的实验 boot/system','实验镜像已生成，没有真机启动结论。'),
        ('verify','核对镜像内容、元数据、boot 结构和策略证据输入','离线镜像检查通过，严格策略失败仍如实保留。'),
        ('vintf','使用固定 AOSP 代码检查目标 HAL 声明','HAL 声明匹配通过，不代表运行时功能通过。'),
        ('package','生成并完整读回分卷实验刷机包','ZIP CRC 和镜像哈希检查通过。'),
        ('publish','上传并核验 GitHub Releases 资产','资产大小和哈希已核验，实验预发布已公开。')]


def sync_progress():
    run('git','add',os.environ['WAYNE_PROGRESS_FILE'],'logs')
    for name in ['artifacts/candidate-package.json','artifacts/release-publication.json',
                 'artifacts/static-candidate-package.json','artifacts/static-release-publication.json',
                 'research/static-wayne',
                 'research/candidate-archive-check.json','research/wayne-boot-check.json',
                 'research/wayne-system-content-check.json','research/wayne-system-metadata-check.json',
                 'research/wayne-vintf-check.json','research/wayne-os4-native-versions.json']:
        if (ROOT/name).exists():run('git','add',name)
    if subprocess.run(['git','diff','--cached','--quiet']).returncode==0:return
    run('git','commit','-m','docs: update timestamped cloud build progress')
    push_progress()


def push_progress():
    # A concurrent plugin MD update can advance main between fetch and push.
    for attempt in range(5):
        run('git','fetch','origin','main')
        run('git','rebase','--autostash','origin/main')
        result=subprocess.run(['git','push','origin','HEAD:main'],text=True,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        print(result.stdout,flush=True)
        if result.returncode==0:return
        if not any(marker in result.stdout.lower() for marker in
                   ('[rejected]','[remote rejected]','non-fast-forward','cannot lock ref')):
            raise subprocess.CalledProcessError(result.returncode,result.args,output=result.stdout)
        if attempt==4:
            raise subprocess.CalledProcessError(result.returncode,result.args,output=result.stdout)
        print('Progress push raced with another update; refetching without force.',flush=True)
        time.sleep(min(attempt+1,3))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage');args=parser.parse_args()
    os.chdir(ROOT)
    if args.stage:stage(args.stage);return
    require_rdp_target()
    for index,(name,action,outcome) in enumerate(STAGES):
        next_step=STAGES[index+1][1] if index+1<len(STAGES) else '在仓库提供成品链接；继续依据真实启动反馈处理运行时问题。'
        progress=ROOT/os.environ['WAYNE_PROGRESS_FILE'];progress.parent.mkdir(parents=True,exist_ok=True)
        with progress.open('a') as stream:
            stream.write('## '+datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n\n做了什么：开始'+action+'。\n\n发生了什么：云端任务已进入本阶段。\n\n下一步：完成本阶段后，'+next_step+'。\n\n')
        sync_progress()
        command=[sys.executable,'tools/record_step.py','--action',action+'。','--outcome',outcome,
                 '--failure-note','本阶段失败；原始日志已保留，不把失败记为通过。','--next',next_step,
                 'cloud-'+name,'--',sys.executable,'tools/ci_build_candidate.py','--stage',name]
        result=subprocess.run(command)
        sync_progress()
        if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
