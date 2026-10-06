#!/usr/bin/env python3
"""Build a focused compatibility checker from pinned AOSP sources."""
import concurrent.futures
import pathlib
import subprocess


def main():
    root=pathlib.Path(__file__).resolve().parent.parent
    output=root/'tools/local/vintf-build';output.mkdir(parents=True,exist_ok=True)
    vintf=['parse_string','parse_xml','CompatibilityMatrix','FQName','FqInstance','HalManifest',
           'HalInterface','KernelConfigTypedValue','KernelInfo','ManifestHal','ManifestInstance',
           'MatrixHal','MatrixInstance','MatrixKernel','Regex','SystemSdk','TransportArch','XmlFile','utils',
           'KernelConfigParser','KernelConfigs']
    base=['strings','stringprintf','logging','threads','file','errors_unix','posix_strerror_r','result']
    log=['log_event_list','log_event_write','logger_name','logger_read','logger_write','properties']
    sources=[root/'sources/libvintf'/(x+'.cpp') for x in vintf]
    sources += [root/'sources/libbase'/(x+'.cpp') for x in base]
    sources += [root/'sources/logging/liblog'/(x+'.cpp') for x in log]
    sources += [root/'sources/tinyxml2/tinyxml2.cpp',root/'tools/vintf_pair_check.cpp']
    includes=['sources/libvintf/include','sources/libvintf/include/vintf','sources/libvintf',
              'sources/libbase/include','sources/logging/liblog/include','sources/logging/liblog',
              'sources/system-core/libutils/binder/include','sources/system-core/libcutils/include',
              'sources/system-core/libutils/include','sources/hidl-tools/metadata/include',
              'sources/tinyxml2','sources/fmt/include']
    # Availability gates concern Android's log API; all compiled host log functions exist.
    flags=['-std=gnu++23','-O1','-ffunction-sections','-fdata-sections','-DFMT_HEADER_ONLY',
           '-D_GNU_SOURCE','-D__builtin_available(...)=true']
    flags += ['-I'+str(root/p) for p in includes]
    def compile_one(pair):
        index,source=pair;obj=output/(str(index)+'.o')
        extra=['-D_POSIX_C_SOURCE=200809L'] if source.name=='posix_strerror_r.cpp' else ['-include','algorithm']
        result=subprocess.run(['g++',*flags,*extra,'-c',str(source),'-o',str(obj)],capture_output=True,text=True)
        (output/(str(index)+'.log')).write_text(result.stdout+result.stderr)
        if result.returncode: print(str(source)+'\n'+result.stderr[-5000:],flush=True)
        return result.returncode,obj
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(compile_one,enumerate(sources)))
    if any(code for code,_ in results):raise SystemExit(1)
    command=['g++','-Wl,--gc-sections',*[str(obj) for _,obj in results],'-pthread','-lz',
             '-o',str(root/'tools/local/vintf_pair_check')]
    subprocess.run(command,check=True)
    print('Built tools/local/vintf_pair_check')


if __name__=='__main__':main()
