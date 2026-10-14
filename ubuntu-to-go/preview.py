#!/usr/bin/env python3
"""Capture real VM screenshots using disposable overlays, never the published disk."""
import json, os, pathlib, shutil, socket, subprocess, time
from PIL import Image
HERE=pathlib.Path.cwd(); base=HERE/'Ubuntu-24.04-zh-CN-E14-20GiB.vhd.vtoy'
OUT=HERE/'previews';OUT.mkdir(exist_ok=True)
accel='kvm' if os.access('/dev/kvm',os.R_OK|os.W_OK) else 'tcg,thread=multi'
def run(*a,**kw):return subprocess.run(list(map(str,a)),check=True,**kw)
def overlay(name):
 p=HERE/name
 run('qemu-img','create','-f','qcow2','-F','vpc','-b',base,p)
 return p
def start(disk,name):
 var=HERE/(name+'-vars.fd');shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd',var)
 sock=HERE/(name+'.qmp')
 if sock.exists():sock.unlink()
 cmd=['qemu-system-x86_64','-machine','q35','-accel',accel,'-cpu','host' if accel=='kvm' else 'max','-smp','2','-m','4096','-drive','if=pflash,unit=0,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd','-drive',f'if=pflash,unit=1,format=raw,file={var}','-drive',f'file={disk},if=virtio,format=qcow2','-device','virtio-vga','-nic','none','-display','none','-serial',f'file:{HERE}/{name}-console.log','-qmp',f'unix:{sock},server=on,wait=off','-monitor','none','-no-reboot']
 if name=='desktop-preview':cmd += ['-drive',f'file={HERE}/ntfs-test.img,if=virtio,format=raw']
 p=subprocess.Popen(cmd)
 for _ in range(100):
  if sock.exists():break
  if p.poll() is not None:raise RuntimeError('Preview VM exited')
  time.sleep(.1)
 s=socket.socket(socket.AF_UNIX);s.connect(str(sock));f=s.makefile('rwb',buffering=0)
 json.loads(f.readline());qmp(f,'qmp_capabilities')
 return p,s,f
def qmp(f,command,arguments=None):
 d={'execute':command}
 if arguments:d['arguments']=arguments
 f.write(json.dumps(d).encode()+b'\n')
 while True:
  r=json.loads(f.readline())
  if 'error' in r:raise RuntimeError(r)
  if 'return' in r:return r['return']
def capture(f,name):
 ppm=OUT/(name+'.ppm');png=OUT/(name+'.png')
 qmp(f,'screendump',{'filename':str(ppm)})
 Image.open(ppm).save(png);ppm.unlink()
 print('Captured',png,flush=True)
def stop(p,s,f):
 try:qmp(f,'quit')
 finally:s.close();p.wait(timeout=30)
initial=overlay('initial-preview.qcow2');p,s,f=start(initial,'initial-preview')
time.sleep(120 if accel=='kvm' else 360)
capture(f,'01-first-boot');stop(p,s,f)
# All following account/configuration changes are confined to this overlay.
desktop=overlay('desktop-preview.qcow2')
run('truncate','-s','128M','ntfs-test.img')
run('mkfs.ntfs','-F','-Q','ntfs-test.img')
custom=r'''set -eu
useradd -m -s /bin/bash -c '预览用户' preview
echo 'preview:preview-only-local' | chpasswd
mkdir -p /home/preview/.config/autostart
printf 'yes\n' >/home/preview/.config/gnome-initial-setup-done
sed -i '/^AutomaticLoginEnable=/d; /^AutomaticLogin=/d; /^InitialSetupEnable=/d' /etc/gdm3/custom.conf
sed -i '/^\[daemon\]/a AutomaticLoginEnable=true\nAutomaticLogin=preview\nInitialSetupEnable=false' /etc/gdm3/custom.conf
cat >/home/preview/.config/autostart/preview-apps.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Preview apps
Exec=/bin/bash -c "sleep 55; nautilus --new-window /home/preview & sleep 45; /opt/QQ/qq"
X-GNOME-Autostart-enabled=true
EOF
cat >/home/preview/.config/autostart/software-smoke.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Software tests
Exec=/bin/bash -c "sleep 180; /usr/bin/python3 /home/preview/app-smoke.py"
X-GNOME-Autostart-enabled=true
EOF
cat >/etc/systemd/system/togo-ntfs-test.service <<'EOF'
[Unit]
Description=Disposable NTFS read/write test
After=local-fs.target
Before=display-manager.service
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'set -e; mkdir -p /mnt/ntfs-test; mount -t ntfs3 /dev/vdb /mnt/ntfs-test; echo test-data > /mnt/ntfs-test/probe.txt; grep -qx test-data /mnt/ntfs-test/probe.txt; umount /mnt/ntfs-test; echo TOGO_NTFS_RW_PASS > /dev/ttyS0'
[Install]
WantedBy=graphical.target
EOF
systemctl enable togo-ntfs-test.service
chown -R preview:preview /home/preview
'''
env=os.environ.copy();env['LIBGUESTFS_BACKEND']='direct'
run('sudo','env','LIBGUESTFS_BACKEND=direct','virt-customize','-a',desktop,'--no-network','--run-command',custom,'--upload',str(pathlib.Path(__file__).resolve().parent/'app-smoke.py')+':/home/preview/app-smoke.py','--run-command','chown preview:preview /home/preview/app-smoke.py',env=env)
p,s,f=start(desktop,'desktop-preview')
start_at=time.monotonic()
for seconds,name in [(55,'02-desktop'),(105,'03-files'),(165,'04-qq')]:
 delay=seconds-(time.monotonic()-start_at)
 if delay>0:time.sleep(delay)
 capture(f,name)
time.sleep(max(0,350-(time.monotonic()-start_at)))
capture(f,'05-software-tests')
qmp(f,'system_powerdown')
try:p.wait(timeout=60)
except subprocess.TimeoutExpired:pass
if p.poll() is None:stop(p,s,f)
else:s.close()
assert 'TOGO_NTFS_RW_PASS' in pathlib.Path('desktop-preview-console.log').read_text(errors='replace'),'NTFS read/write test failed'
app_results=subprocess.check_output(['sudo','env','LIBGUESTFS_BACKEND=direct','virt-cat','-a',str(desktop),'/home/preview/app-test-results/results.json'],text=True)
(OUT/'software-tests.json').write_text(app_results)
report=json.loads(app_results)
assert all(x.get('returncode')==0 for x in report['cli'].values()),'CLI smoke test failed'
assert all(x.get('startup_returncode') in (None,0) and 'error' not in x for x in report['gui'].values()),'GUI smoke test failed'
# The pristine fixed VHD was opened only as a read-only backing image.
