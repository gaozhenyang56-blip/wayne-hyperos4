#!/usr/bin/env python3
"""Build a Chinese Ubuntu desktop VHD on an Ubuntu GitHub Actions runner."""
import hashlib, json, os, pathlib, shutil, socket, struct, subprocess, sys, time
import yaml
ROOT = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('ubuntu-build').resolve(); WORK.mkdir(exist_ok=True)
os.chdir(WORK)
NAME='Ubuntu-24.04-zh-CN-E14-20GiB.vhd.vtoy'
def run(*args):
    print('+', ' '.join(map(str,args)),flush=True)
    return subprocess.run(list(map(str,args)),check=True)
def download(url,path):
    run('curl','--fail','--location','--retry','3','--connect-timeout','30','--max-time','900',url,'-o',path)
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()
base='https://cloud-images.ubuntu.com/noble/current/'
download(base+'SHA256SUMS','base-SHA256SUMS')
download(base+'noble-server-cloudimg-amd64.img','ubuntu.qcow2')
expected=next(x.split()[0] for x in pathlib.Path('base-SHA256SUMS').read_text().splitlines() if x.endswith(' *noble-server-cloudimg-amd64.img'))
assert sha('ubuntu.qcow2')==expected,'Ubuntu checksum mismatch'
download('https://github.com/ventoy/vtoyboot/releases/download/v1.0.36/vtoyboot-1.0.36.iso','vtoyboot.iso')
assert sha('vtoyboot.iso')=='e0fd493014b57f2c72c7b1b45c53b3e7cd3b746fedee5a9f20b057811168267e'
download('https://qqdl.gtimg.cn/qqfile/QQNT/9.9.36/beta/9ee04bef/linuxqq_3.2.34-53644_amd64.deb','qq.deb')
assert sha('qq.deb')=='436c65e1dd28422e128a21cbddb5fe4e2e6c079d7f27fec2541e014d38cc336e','QQ checksum mismatch'
run('qemu-img','resize','ubuntu.qcow2','20G')
seed={'users':[],'disable_root':True,'locale':'zh_CN.UTF-8','timezone':'Asia/Shanghai','write_files':[{'path':'/root/guest-build.sh','permissions':'0700','content':(ROOT/'guest-build.sh').read_text()}],'runcmd':[['bash','/root/guest-build.sh']]}
pathlib.Path('user-data').write_text('#cloud-config\n'+yaml.safe_dump(seed,allow_unicode=True))
pathlib.Path('meta-data').write_text('instance-id: ubuntu-to-go-20g-01\nlocal-hostname: ubuntu-to-go\n')
run('genisoimage','-output','seed.iso','-volid','cidata','-joliet','-rock','user-data','meta-data','qq.deb')
accel='kvm' if os.access('/dev/kvm',os.R_OK|os.W_OK) else 'tcg,thread=multi'
print('Acceleration:',accel,flush=True)
code=pathlib.Path('/usr/share/OVMF/OVMF_CODE_4M.fd');var=pathlib.Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
shutil.copyfile(var,'build-vars.fd')
def vm_args(log,varsfile,drive):
    return ['qemu-system-x86_64','-machine','q35','-accel',accel,'-cpu','host' if accel=='kvm' else 'max','-smp','2','-m','4096','-drive',f'if=pflash,unit=0,format=raw,readonly=on,file={code}','-drive',f'if=pflash,unit=1,format=raw,file={varsfile}','-drive',drive,'-device','virtio-vga','-netdev','user,id=n0','-device','virtio-net-pci,netdev=n0','-display','none','-serial',f'file:{log}','-monitor','none','-no-reboot']
cmd=vm_args('build-console.log','build-vars.fd','file=ubuntu.qcow2,if=virtio,format=qcow2')+['-drive','file=seed.iso,media=cdrom,readonly=on','-drive','file=vtoyboot.iso,media=cdrom,readonly=on']
p=subprocess.Popen(cmd)
start=time.monotonic();pos=0
try:
    while p.poll() is None:
        if time.monotonic()-start>5400: raise TimeoutError('Build VM exceeded 90 minutes')
        time.sleep(10)
        if pathlib.Path('build-console.log').exists():
            with open('build-console.log','r',errors='replace') as f:
                f.seek(pos);data=f.read();pos=f.tell()
            print(data,flush=True)
    log=pathlib.Path('build-console.log').read_text(errors='replace')
    assert p.returncode==0 and 'BUILD_COMPLETED' in log and 'BUILD_FAILED:' not in log,'Guest build failed'
finally:
    if p.poll() is None: p.terminate();p.wait(timeout=30)
run('qemu-img','check','-f','qcow2','ubuntu.qcow2')
run('qemu-img','convert','-p','-f','qcow2','-O','vpc','-o','subformat=fixed,force_size=on','ubuntu.qcow2',NAME)
with open(NAME,'rb') as f:
    f.seek(-512,2);footer=f.read(512)
assert footer[:8]==b'conectix' and struct.unpack('>I',footer[60:64])[0]==2
assert struct.unpack('>Q',footer[48:56])[0]==20*1024**3
env=os.environ.copy();env['LIBGUESTFS_BACKEND']='direct'
space=subprocess.check_output(['virt-cat','-a',NAME,'/var/log/ubuntu-to-go-free-space.txt'],env=env,text=True)
pathlib.Path('磁盘空间.txt').write_text(space)
report={'base_sha256':expected,'qq_version':'3.2.34-53644','qq_sha256':'436c65e1dd28422e128a21cbddb5fe4e2e6c079d7f27fec2541e014d38cc336e','root_space_df':space,'vtoyboot':'1.0.36','vhd_size_bytes':os.path.getsize(NAME),'vhd_sha256':sha(NAME),'format':'fixed VHD','virtual_capacity_GiB':20,'language':'zh_CN.UTF-8','first_boot':'GNOME local user/password setup','validation':'guest package and kernel-module presence; fixed VHD footer; QEMU image check. Hardware and Ventoy boot require verification.'}
pathlib.Path('manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
run('python3',ROOT/'preview.py')
# Archive zeros efficiently, split below GitHub's per-asset limit.
run('tar','-I','zstd -T2 -8','-cf',NAME+'.tar.zst',NAME)
run('split','-b','1900000000','-d','-a','3',NAME+'.tar.zst',NAME+'.tar.zst.')
assets=sorted(pathlib.Path('.').glob(NAME+'.tar.zst.[0-9][0-9][0-9]'))
pathlib.Path('SHA256SUMS').write_text(''.join(f'{sha(x)}  {x.name}\n' for x in assets))
shutil.copyfile(ROOT/'使用说明.txt','使用说明.txt')
print('IMAGE_READY',flush=True)
