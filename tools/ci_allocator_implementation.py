#!/usr/bin/env python3
"""One bounded allocator build, keeping previous kernel reports immutable."""
import datetime
import os
import pathlib
import subprocess
import sys
import json
from ci_build_candidate import sync_progress,run

ROOT=pathlib.Path(__file__).resolve().parent.parent
KERNEL_REPORT=ROOT/'artifacts/kernel-6.6-allocator-probe.json'
REPORT=ROOT/'research/allocator-implementation/cross-build.json'


def main():
    os.chdir(ROOT)
    steps=[('prepare',['sudo','apt-get','update'],'更新独立 allocator 构建环境。'),
      ('dependencies',['sudo','apt-get','install','-y','gcc-aarch64-linux-gnu','gcc-arm-linux-gnueabihf',
                       'make','flex','bison','libssl-dev','libelf-dev','bc','device-tree-compiler'],
                       '准备 ARM32/ARM64 工具链与内核依赖。'),
      ('adapter',[sys.executable,'tools/build_allocator_adapter.py','--cross','--output',
                  'downloads/allocator-cross','--report',str(REPORT)],
                  '运行受限 source-client 适配器负例测试与 GNU/Linux ARM32/ARM64 交叉编译。'),
      ('kernel',[sys.executable,__file__,'--kernel'],
                  '验证完整 6.6 配置并编译 heap/sync 实验内核和 DTB，独立保存报告。')]
    before={p:p.read_bytes() for p in [ROOT/'artifacts/kernel-6.6-probe.json',ROOT/'artifacts/static-candidate-package.json']}
    for name,command,action in steps:
        now=datetime.datetime.now(datetime.timezone.utc).isoformat()
        path=ROOT/os.environ['WAYNE_PROGRESS_FILE'];path.parent.mkdir(exist_ok=True,parents=True)
        with path.open('a') as f:
            f.write(f'## {now}\n\n做了什么：开始{action}\n\n发生了什么：进入本阶段；不注入旧 vendor，不生成可刷 boot。\n\n下一步：保存阶段结果并核对剩余接口阻碍。\n\n')
        sync_progress()
        r=subprocess.run([sys.executable,'tools/record_step.py','--action',action,
            '--outcome','本阶段命令完成；构建通过不代表旧 vendor 兼容或整机启动。',
            '--failure-note','本阶段失败，已保存日志并停止，不伪造成功。',
            '--next','核对研究报告、配置生效及未解决的 KGSL/显示/安全堆接口。',
            'allocator-implementation-'+name,'--',*command])
        for p in [REPORT,KERNEL_REPORT]:
            if p.exists():run('git','add',p)
        sync_progress()
        if r.returncode:raise SystemExit(r.returncode)
    if any(p.read_bytes()!=data for p,data in before.items()):
        raise ValueError('Historical build report changed')


if __name__=='__main__':
    if sys.argv[1:]==['--kernel']:
        from ci_kernel_66_probe import build
        build(KERNEL_REPORT)
    elif not sys.argv[1:]:main()
    else:raise SystemExit('Unknown argument')
