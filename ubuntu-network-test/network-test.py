import json, os, pathlib, shutil, subprocess, time
ROOT=pathlib.Path(__import__('sys').argv[1]).resolve() if len(__import__('sys').argv)>1 else pathlib.Path('ubuntu-build').resolve()
work=ROOT/'network-test';work.mkdir(exist_ok=True)
base=ROOT/'ubuntu.qcow2';assert base.exists(),'No completed installation checkpoint available'
marker=json.loads((ROOT/'image-complete.json').read_text())
def run(*args):return subprocess.run(list(map(str,args)),check=True)
overlay=work/'network.qcow2';run('qemu-img','create','-f','qcow2','-F','qcow2','-b',base,overlay)
script=r'''#!/bin/bash
set -Eeuo pipefail
exec > >(tee -a /var/log/network-validation.log /dev/ttyS0) 2>&1
trap 'echo NETWORK_TEST_FAILED >/dev/ttyS0; sync; poweroff -f' ERR
nm-online -q -t 90
systemctl is-active NetworkManager
systemctl is-active systemd-resolved
test -L /etc/resolv.conf
test "$(readlink /etc/resolv.conf)" = /run/systemd/resolve/stub-resolv.conf
ip -4 address
ip -4 route
ip -4 route show default | grep -q '^default '
iface=$(ip -o -4 route show default | awk '{print $5;exit}')
uuid=$(nmcli -g GENERAL.CON-UUID device show "$iface")
nmcli -g ipv4.method connection show "$uuid" | grep -qx auto
nmcli -t -f DEVICE,TYPE,STATE device
resolvectl status
getent ahostsv4 archive.ubuntu.com
curl -4 --fail --head --retry 2 --connect-timeout 15 --max-time 45 https://archive.ubuntu.com/ubuntu/dists/noble/Release
printf '{"network_manager":true,"systemd_resolved":true,"normal_resolver_symlink":true,"dhcp_route":true,"dns":true,"https":true,"environment":"QEMU user-mode Ethernet; physical Wi-Fi untested"}\n' >/var/log/network-validation.json
sync
echo NETWORK_TEST_PASSED >/dev/ttyS0
poweroff
'''
(work/'network-test.sh').write_text(script)
unit='''[Unit]
Description=Validate Ubuntu To Go final network configuration
Wants=network-online.target
After=network-online.target NetworkManager.service systemd-resolved.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/network-test.sh
[Install]
WantedBy=graphical.target
'''
(work/'network-validation.service').write_text(unit)
run('sudo','env','LIBGUESTFS_BACKEND=direct','virt-customize','-a',overlay,'--no-network','--upload',str(work/'network-test.sh')+':/usr/local/sbin/network-test.sh','--upload',str(work/'network-validation.service')+':/etc/systemd/system/network-validation.service','--run-command','chmod 755 /usr/local/sbin/network-test.sh; systemctl enable network-validation.service')
shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd',work/'vars.fd')
accel='kvm' if os.access('/dev/kvm',os.R_OK|os.W_OK) else 'tcg,thread=multi'
cmd=['qemu-system-x86_64','-machine','q35','-accel',accel,'-cpu','host' if accel=='kvm' else 'max','-smp','2','-m','4096','-drive','if=pflash,unit=0,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd','-drive',f'if=pflash,unit=1,format=raw,file={work}/vars.fd','-drive',f'file={overlay},if=virtio,format=qcow2','-netdev','user,id=n0','-device','virtio-net-pci,netdev=n0','-display','none','-serial',f'file:{work}/console.log','-monitor','none','-no-reboot']
p=subprocess.Popen(cmd)
try:p.wait(timeout=360)
except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=30)
log=(work/'console.log').read_text(errors='replace');print(log[-15000:])
assert p.returncode==0 and 'NETWORK_TEST_PASSED' in log and 'NETWORK_TEST_FAILED' not in log,'Network validation failed'
r=subprocess.check_output(['sudo','env','LIBGUESTFS_BACKEND=direct','virt-cat','-a',str(overlay),'/var/log/network-validation.json'],text=True)
report=json.loads(r);report['guest_script_sha256']=marker['guest_script_sha256'];report['base_sha256']=marker['base_sha256']
(work/'NETWORK_TEST.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
