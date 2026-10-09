#!/usr/bin/env python3
"""Compile a pinned SDM660 6.6 tree. Never create or publish a flashable boot."""
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'sources/kernel-6.6-probe'
OUT = SOURCE / 'out'
REPORT = ROOT / 'artifacts/kernel-6.6-probe.json'


def run(*args, **kwargs):
    subprocess.run([str(x) for x in args], check=True, **kwargs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    lock = json.loads((ROOT / 'config/kernel-6.6-experiment.json').read_text())
    SOURCE.mkdir(parents=True, exist_ok=True)
    run('git', 'init', SOURCE)
    run('git', '-C', SOURCE, 'fetch', '--depth=1', lock['repository'], lock['commit'])
    run('git', '-C', SOURCE, 'checkout', '--detach', 'FETCH_HEAD')
    actual = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != lock['commit']:
        raise ValueError('Source revision mismatch')
    for item in lock['files']:
        if digest(SOURCE / item['path']) != item['sha256']:
            raise ValueError('Pinned evidence mismatch: ' + item['path'])
    dts = SOURCE / 'arch/arm64/boot/dts/qcom/sdm660-xiaomi-wayne.dts'
    shutil.copyfile(ROOT / 'config/sdm660-xiaomi-wayne-6.6.dts', dts)
    with (dts.parent / 'Makefile').open('a') as stream:
        stream.write('\ndtb-$(CONFIG_ARCH_QCOM) += sdm660-xiaomi-wayne.dtb\n')
    common = ['make', '-C', str(SOURCE), 'O=' + str(OUT), 'ARCH=arm64',
              'CROSS_COMPILE=aarch64-linux-gnu-']
    run(*common, 'sdm660_defconfig')
    run('bash', SOURCE / 'scripts/kconfig/merge_config.sh', '-m', '-O', OUT,
        OUT / '.config', ROOT / 'config/kernel-6.6-android.fragment', cwd=SOURCE)
    run(*common, 'olddefconfig')
    config = (OUT / '.config').read_text()
    required = ['ANDROID_BINDER_IPC', 'ANDROID_BINDERFS', 'SECURITY_SELINUX',
                'FS_ENCRYPTION', 'EXT4_FS', 'EROFS_FS', 'DEVTMPFS', 'BLK_DEV_INITRD', 'COMPAT',
                'DMABUF_HEAPS', 'DMABUF_HEAPS_SYSTEM', 'DMA_CMA', 'DMABUF_HEAPS_CMA', 'SYNC_FILE']
    for symbol in required:
        if 'CONFIG_' + symbol + '=y\n' not in config:
            raise ValueError('Required Android prerequisite missing: ' + symbol)
    if 'selinux' not in next((x for x in config.splitlines() if x.startswith('CONFIG_LSM=')), ''):
        raise ValueError('SELinux absent from LSM list')
    run(*common, '-j' + str(min(os.cpu_count() or 2, 4)),
        'Image.gz', 'qcom/sdm660-xiaomi-wayne.dtb')
    dtb = OUT / 'arch/arm64/boot/dts/qcom/sdm660-xiaomi-wayne.dtb'
    compatible = subprocess.check_output(['fdtget', str(dtb), '/', 'compatible'], text=True).strip()
    if compatible.split() != ['xiaomi,wayne', 'qcom,sdm660']:
        raise ValueError('Built DTB is not identified as wayne')
    release = (OUT / 'include/config/kernel.release').read_text().strip()
    if not release.startswith('6.6.9'):
        raise ValueError('Unexpected kernel version: ' + release)
    files = [OUT / '.config', OUT / 'arch/arm64/boot/Image.gz', dtb]
    report = {
        'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit': actual, 'repository': lock['repository'], 'kernel_release': release,
        'compiled': True, 'android_config_prerequisites_verified': required,
        'dtb_compatible': compatible, 'hardware_tested': False,
        'android_vendor_abi_verified': False, 'bootable_verified': False,
        'flashable_boot_created': False, 'partition_table_modified': False,
        'modules_built': False,
        'limitations': ['jasmine hardware inherited; board differences unverified',
                        'downstream KGSL/ION/camera/audio ABI compatibility unverified',
                        'early modules and firmware loading not integrated',
                        'Android boot packaging and VINTF kernel compatibility unverified'],
        'outputs': [{'path': str(p.relative_to(SOURCE)), 'sha256': digest(p),
                     'size': p.stat().st_size} for p in files],
    }
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


def main():
    os.chdir(ROOT)
    from ci_build_candidate import sync_progress
    steps = [('prepare', ['sudo', 'apt-get', 'update'], '更新临时云端编译环境。'),
             ('dependencies', ['sudo', 'apt-get', 'install', '-y', 'gcc-aarch64-linux-gnu',
                               'make', 'flex', 'bison', 'libssl-dev', 'libelf-dev', 'bc',
                               'device-tree-compiler'], '准备交叉编译器和设备树工具。'),
             ('compile', [sys.executable, __file__, '--build'],
              '编译固定 SDM660 6.6.9 源码与实验 wayne DTB，核对 Android 配置。')]
    for name, command, action in steps:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        path = ROOT / os.environ['WAYNE_PROGRESS_FILE']
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as stream:
            stream.write(f'## {now} — kernel-6.6-{name}\n\n做了什么：开始{action}\n\n'
                         '发生了什么：进入独立编译实验，未生成可刷 boot。\n\n'
                         '下一步：记录本阶段结果，再检查后续驱动和启动接口。\n\n')
        sync_progress()
        result = subprocess.run([sys.executable, 'tools/record_step.py', '--action', action,
                                 '--outcome', '本阶段命令完成；编译结果不代表整机启动通过。',
                                 '--failure-note', '本阶段失败，已保存日志，停止后续构建。',
                                 '--next', '根据日志检查结果和未验证的厂商驱动接口。',
                                 'kernel-6.6-' + name, '--', *command])
        if REPORT.exists():
            run('git', 'add', REPORT)
        sync_progress()
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == '__main__':
    if sys.argv[1:] == ['--build']:
        build()
    elif sys.argv[1:]:
        raise SystemExit('Only --build is supported')
    else:
        main()
