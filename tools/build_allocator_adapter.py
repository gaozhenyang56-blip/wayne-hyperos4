#!/usr/bin/env python3
"""Host mock tests and GNU/Linux ARM cross-builds, never a vendor injection."""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess

ROOT=pathlib.Path(__file__).resolve().parent.parent
UAPI=ROOT/'research/gpu-allocator-stage/kernel-uapi'
CODE=ROOT/'compat/wayne_dma_heap'


def run(args):
    subprocess.run([str(x) for x in args],check=True)


def build(output,cross=False):
    output.mkdir(parents=True,exist_ok=True)
    flags=['-D_GNU_SOURCE','-std=c11','-Wall','-Wextra','-Werror','-fPIC','-O2','-I'+str(UAPI)]
    source=CODE/'adapter.c';test=CODE/'test_adapter.c'
    run(['cc',*flags,source,test,'-o',output/'test_adapter'])
    run([output/'test_adapter'])
    artifacts=[]
    if cross:
        for prefix,arch,bits,machine in [('aarch64-linux-gnu-','aarch64',64,'AArch64'),
                                        ('arm-linux-gnueabihf-','armv7',32,'ARM')]:
            dest=output/arch;dest.mkdir(exist_ok=True);obj=dest/'adapter.o';lib=dest/'libwayne_dma_heap.a'
            run([prefix+'gcc',*flags,'-c',source,'-o',obj]);run([prefix+'ar','rcs',lib,obj])
            header=subprocess.check_output(['readelf','-h',str(obj)],text=True)
            if 'ELF'+str(bits) not in header or 'Machine:' not in header or machine not in header:
                raise ValueError('Wrong object target: '+arch)
            (dest/'readelf.txt').write_text(header)
            for path in [obj,lib]:
                artifacts.append({'path':str(path.relative_to(ROOT)),
                    'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size,
                    'target':arch,'elf_bits':bits,'machine':machine})
    report={'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'host_test_exit_code':0,'host_backend':'mocked heap syscalls only',
        'cross_compiled':cross,'cross_environment':'GNU/Linux toolchains',
        'android_bionic_linked':False,'injected_into_vendor':False,'kgsl_implemented':False,
        'legacy_ion_ioctl_implemented':False,'hardware_tested':False,'bootable_verified':False,
        'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [source,CODE/'adapter.h',test,UAPI/'ion-lineage.h',UAPI/'dma-heap.h']},
        'outputs':artifacts}
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--cross',action='store_true')
    p.add_argument('--output',type=pathlib.Path,default=ROOT/'downloads/allocator-native')
    p.add_argument('--report',type=pathlib.Path,required=True);args=p.parse_args()
    report=build(args.output.resolve(),args.cross);args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
