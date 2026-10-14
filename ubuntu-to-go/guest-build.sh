#!/bin/bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
exec > >(tee -a /var/log/ubuntu-to-go-build.log /dev/ttyS0) 2>&1
trap 'echo BUILD_FAILED:$LINENO >/dev/ttyS0; sync; poweroff -f' ERR
cat >/etc/apt/sources.list.d/ubuntu.sources <<'EOF'
Types: deb
URIs: https://archive.ubuntu.com/ubuntu
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: https://security.ubuntu.com/ubuntu
Suites: noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
printf 'Acquire::Retries "3";\nAcquire::Languages "zh_CN;zh;en";\n' >/etc/apt/apt.conf.d/80-to-go
apt-get update
apt-get install -y --no-install-recommends curl ca-certificates gnupg
install -d -m 0755 /etc/apt/keyrings
curl --fail --location --retry 3 https://packages.mozilla.org/apt/repo-signing-key.gpg -o /etc/apt/keyrings/packages.mozilla.org.asc
fingerprint=$(gpg --show-keys --with-colons /etc/apt/keyrings/packages.mozilla.org.asc | awk -F: '$1=="fpr" {print $10;exit}')
[[ "$fingerprint" == 35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3 ]]
printf 'deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.asc] https://packages.mozilla.org/apt mozilla main\n' >/etc/apt/sources.list.d/mozilla.list
printf 'Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n' >/etc/apt/preferences.d/mozilla
apt-get update
apt-get install -y --no-install-recommends ubuntu-desktop-minimal gnome-terminal gnome-initial-setup network-manager network-manager-gnome linux-generic linux-firmware firmware-sof-signed intel-microcode ntfs-3g exfatprogs cryptsetup gvfs-backends gvfs-fuse udisks2 gnome-disk-utility language-pack-zh-hans language-pack-gnome-zh-hans fonts-noto-cjk fonts-noto-color-emoji ibus-libpinyin software-properties-gtk ubuntu-drivers-common nvidia-prime mesa-utils firefox firefox-l10n-zh-cn libreoffice-writer libreoffice-calc libreoffice-impress libreoffice-gtk3 libreoffice-l10n-zh-cn libreoffice-help-zh-cn vlc file-roller p7zip-full unzip gnome-system-monitor gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly libfuse2t64 libnss3 libxss1 libasound2t64
apt-get install -y --no-install-recommends linux-modules-nvidia-580-generic nvidia-driver-580
prime-select on-demand
curl --fail --location --retry 3 'https://qqdl.gtimg.cn/qqfile/QQNTV2/9.9.35/release/1763096b/QQ_3.2.33_260902_amd64_01.deb' -o /tmp/qq.deb
sha256sum /tmp/qq.deb >/var/log/qq-package.sha256
apt-get install -y /tmp/qq.deb
# Allow Electron's sandbox on Ubuntu 24.04 without disabling user-namespace protection globally.
cat >/etc/apparmor.d/qq-to-go <<'EOF'
abi <abi/4.0>,
include <tunables/global>
profile qq-to-go /opt/QQ/qq flags=(unconfined) {
  userns,
}
EOF
apparmor_parser -r /etc/apparmor.d/qq-to-go

locale-gen zh_CN.UTF-8
update-locale LANG=zh_CN.UTF-8 LANGUAGE=zh_CN:zh
ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
printf 'Asia/Shanghai\n' >/etc/timezone
mkdir -p /etc/dconf/db/local.d /etc/skel/.config
cat >/etc/dconf/profile/user <<'EOF'
user-db:user
system-db:local
EOF
cat >/etc/dconf/db/local.d/00-to-go <<'EOF'
[org/gnome/desktop/input-sources]
sources=[('xkb', 'us'), ('ibus', 'libpinyin')]
[org/gnome/desktop/interface]
clock-format='24h'
[org/gnome/shell]
favorite-apps=['firefox.desktop', 'org.gnome.Nautilus.desktop', 'qq.desktop', 'libreoffice-writer.desktop', 'org.gnome.Terminal.desktop']
EOF
dconf update
cat >/etc/skel/.config/user-dirs.locale <<'EOF'
zh_CN
EOF
# Physical network interfaces are managed automatically on first boot.
rm -f /etc/netplan/50-cloud-init.yaml
printf 'network:\n  version: 2\n  renderer: NetworkManager\n' >/etc/netplan/01-network-manager-all.yaml
chmod 600 /etc/netplan/01-network-manager-all.yaml
mkdir -p /etc/NetworkManager/conf.d
printf '[keyfile]\nunmanaged-devices=none\n' >/etc/NetworkManager/conf.d/10-globally-managed-devices.conf
systemctl enable NetworkManager
systemctl disable systemd-networkd-wait-online.service ssh.service ssh.socket || true
systemctl set-default graphical.target
# GNOME creates the real user locally, with password confirmation, on first boot.
sed -i '/^InitialSetupEnable=/d' /etc/gdm3/custom.conf
sed -i '/^\[daemon\]/a InitialSetupEnable=true' /etc/gdm3/custom.conf
mkdir -p /etc/gnome-initial-setup
printf '[pages]\nskip=goa,privacy,software,ubuntu-report,livepatch\n' >/etc/gnome-initial-setup/vendor.conf
# Install the official vtoyboot payload supplied on the read-only build CD.
mkdir -p /mnt/vtoyboot /opt/vtoyboot
mount -o ro -L Vtoyboot /mnt/vtoyboot
tar xzf /mnt/vtoyboot/vtoyboot-1.0.36.tar.gz -C /opt/vtoyboot --strip-components=1
cd /opt/vtoyboot
bash vtoyboot.sh
update-initramfs -u -k all
# Validate package and driver presence. Hardware execution requires the ThinkPad.
kernel=$(ls /lib/modules | sort -V | tail -1)
for mod in nvidia i915 iwlwifi rtw89_8852be snd_sof_pci_intel_tgl thinkpad_acpi ntfs3; do
  modinfo -k "$kernel" "$mod" >/dev/null
done
for pkg in gnome-shell gdm3 gnome-initial-setup firefox libreoffice-writer vlc linuxqq; do
  dpkg-query -W -f='${Status}\n' "$pkg" | grep -q 'install ok installed'
done
df -B1 / >/var/log/ubuntu-to-go-free-space.txt
dpkg-query -W -f='${Package}\t${Version}\n' >/var/log/ubuntu-to-go-packages.tsv
printf 'LANG=zh_CN.UTF-8\nLANGUAGE=zh_CN:zh\n' >/etc/default/locale
# No published account, SSH key, proxy certificate, or build-time password.
for user in $(awk -F: '$3>=1000 && $3<60000 {print $1}' /etc/passwd); do userdel -r "$user" || true; done
passwd -l root
rm -f /etc/sudoers.d/90-cloud-init-users /etc/ssh/ssh_host_* /etc/apt/apt.conf.d/99build-proxy
rm -rf /var/lib/AccountsService/users/* /var/lib/cloud/* /root/.ssh /root/.bash_history
rm -f /root/guest-build.sh /usr/local/share/ca-certificates/build-proxy.crt
update-ca-certificates
mkdir -p /etc/cloud
touch /etc/cloud/cloud-init.disabled
apt-get clean
rm -f /tmp/qq.deb
rm -rf /var/lib/apt/lists/*
rm -f /var/lib/systemd/random-seed
truncate -s0 /etc/machine-id
sync
printf 'BUILD_COMPLETED\n' >/dev/ttyS0
poweroff
