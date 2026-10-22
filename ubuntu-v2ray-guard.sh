#!/usr/bin/env bash

# V2RAY-GUARD-PROJECT (v2)
V2_GUARD_LEGACY=${V2_GUARD_LEGACY:-0}
V2_BIN=/usr/local/sbin/v2ray-guard
V2_DIR=/etc/v2ray-guard
V2_RUN=/run/v2ray-guard
V2_CFG=/etc/v2ray-guard/probe.conf
V2_RAW=https://raw.githubusercontent.com/gaozhenyang56-blip/wayne-hyperos4/ubuntu-v2ray-guard/ubuntu-v2ray-guard.sh
v2_msg(){ printf '[V2Ray 守护] %s\n' "$*"; logger -t v2ray-guard -- "$*" 2>/dev/null || :; }
v2_bad(){ printf '错误：%s\n' "$*" >&2; exit 1; }
v2_root(){ ((EUID==0)) || v2_bad '请使用 sudo 执行'; [[ -d /run/systemd/system ]] || v2_bad '当前环境没有运行 systemd'; }
v2_valid_unit(){ [[ "$1" =~ ^[a-zA-Z0-9_.@-]+\.service$ ]]; }
v2_read(){
 V2_PORT=0 V2_MODE=tcp V2_BG='' V2_TARGET='' V3_AUTO=1
 if [[ -r "$V2_DIR/service" ]]; then V2_TARGET="$(head -n1 "$V2_DIR/service")"; fi
 if ! v2_valid_unit "$V2_TARGET"; then
   local u
   for u in v2ray.service xray.service x-ui.service 3x-ui.service; do
     if [[ "$(systemctl show "$u" -p LoadState --value 2>/dev/null || :)" == loaded ]]; then V2_TARGET="$u"; break; fi
   done
 fi
 if [[ -r "$V2_CFG" ]]; then
  local k v
  while IFS='=' read -r k v; do
   case "$k" in
    PORT) [[ "$v" =~ ^[0-9]+$ ]] && V2_PORT="$v" || :;;
    MODE) [[ "$v" =~ ^(tcp|http|socks5)$ ]] && V2_MODE="$v" || :;;
    BG) [[ -z "$v" ]] || { v2_valid_unit "$v" && V2_BG="$v" || :; };;
    AUTO) [[ "$v" == 0 || "$v" == 1 ]] && V3_AUTO="$v" || :;;
   esac
  done < "$V2_CFG"
 fi
}
v2_configure(){
 v2_root; v2_read; local chosen
 while (($#)); do
  (($#>=2)) || v2_bad "参数 $1 缺少内容"
  case "$1" in
   --port) V2_PORT="$2";;
   --mode) V2_MODE="$2";;
   --background-unit) V2_BG="$2";;
   --disable-background) V2_BG=''; V3_AUTO=0;;
   --auto-on) V3_AUTO=1;;
   --auto-off) V3_AUTO=0;;
   *) v2_bad "无效选项：$1";;
  esac
  shift 2
 done
 [[ "$V2_PORT" =~ ^[0-9]+$ ]] && ((10#$V2_PORT <= 65535)) || v2_bad '端口无效，请输入 0～65535'
 [[ "$V2_MODE" =~ ^(tcp|http|socks5)$ ]] || v2_bad '检测模式无效，请使用 tcp、socks5 或 http'
 [[ "$V2_MODE" == tcp || "$V2_PORT" != 0 ]] || v2_bad '启用代理检测必须指定非零端口'
 if [[ -n "$V2_BG" ]]; then
   v2_valid_unit "$V2_BG" && [[ "$V2_BG" != "$V2_TARGET" ]] || v2_bad '后台服务名称无效，或选择了正在保护的代理'
   [[ "$(systemctl show "$V2_BG" -p LoadState --value 2>/dev/null || :)" == loaded ]] || v2_bad '找不到指定的后台服务'
   case "$V2_BG" in
    astrbot*.service|AstrBot*.service|ssh.service|sshd.service|systemd-*.service|network*.service|NetworkManager.service|dbus.service|cron.service|docker.service|containerd.service|nginx.service|apache2.service|ufw.service|firewalld.service|v2ray*.service|xray*.service|x-ui.service|3x-ui.service)
       v2_bad '禁止对 SSH、网络、代理等关键服务限速';;
   esac
 fi
 install -d -m 0700 "$V2_DIR"
 (umask 077; printf 'PORT=%s\nMODE=%s\nBG=%s\nAUTO=%s\n' "$V2_PORT" "$V2_MODE" "$V2_BG" "$V3_AUTO" > "$V2_CFG")
 v2_msg "配置已保存：检测端口 $V2_PORT，检测协议 $V2_MODE，后台服务 $V2_BG，自动优化 $V3_AUTO"
}
v2_tcp(){
 ((V2_PORT>0)) || return 0
 timeout 3 bash -c 'exec 3<>/dev/tcp/127.0.0.1/$1' _ "$V2_PORT" 2>/dev/null
}
v2_proxy(){
 [[ "$V2_MODE" == tcp ]] && return 0
 command -v curl >/dev/null || return 1
 local p=http
 [[ "$V2_MODE" == socks5 ]] && p=socks5h
 curl -q -fsS --noproxy '' --proxy "$p://127.0.0.1:$V2_PORT" \
  --connect-timeout 3 --max-time 8 -o /dev/null https://cp.cloudflare.com/generate_204 2>/dev/null
}
v2_cool(){
 local file="$V2_RUN/$1.stamp" now old=0
 now="$(date +%s)"
 [[ -r "$file" ]] && read -r old < "$file" || :
 [[ "$old" =~ ^[0-9]+$ ]] || old=0
 ((now-old>=900)) || return 1
 printf '%s\n' "$now" > "$file"
}
v2_fail_count(){
 local file="$V2_RUN/$1.fail" n=0
 [[ -r "$file" ]] && read -r n < "$file" || :
 [[ "$n" =~ ^[0-9]+$ ]] || n=0
 V2_FAIL=$((n+1)); printf '%s\n' "$V2_FAIL" > "$file"
}
v2_metrics(){
 local t a x y z q d i
 read -r t a < <(awk '/^MemTotal:/ {t=$2} /^MemAvailable:/ {a=$2} END {print t+0,a+0}' /proc/meminfo)
 V2_MEM=$((t>0 ? 100*a/t : 100))
 read -r x y < <(awk '/^cpu / {t=0;for(i=2;i<=NF;i++)t+=$i;print t,$5+$6;exit}' /proc/stat)
 sleep 1
 read -r z q < <(awk '/^cpu / {t=0;for(i=2;i<=NF;i++)t+=$i;print t,$5+$6;exit}' /proc/stat)
 d=$((z-x)); i=$((q-y)); V2_CPU=$((d>0 ? 100*(d-i)/d : 0))
}
v2_restore(){
 local u='' w=''
 [[ -r "$V2_RUN/cpu.original" ]] || return 0
 read -r u w < "$V2_RUN/cpu.original" || :
 if v2_valid_unit "$u" && [[ "$w" =~ ^[0-9]+$ ]] && ((w>=1&&w<=10000)); then
   systemctl set-property --runtime "$u" "CPUWeight=$w" CPUQuota=infinity >/dev/null 2>&1 || return 1
 fi
 rm -f "$V2_RUN/cpu.original"
 v2_msg "已恢复后台服务 $u 的 CPU 设置"
}
# 自动选择低优先级的维护及索引服务，不干预未知服务。
v3_safe_unit(){
 case "$1" in
  apt-daily.service|apt-daily-upgrade.service|unattended-upgrades.service|packagekit.service|fwupd.service|man-db.service|plocate-updatedb.service|mlocate.service|tracker-miner-fs-3.service) return 0;;
  *) return 1;;
 esac
}
v3_auto_candidate(){
 [[ "$V3_AUTO" == 1 && -z "$V2_BG" ]] || return 0
 [[ -f /sys/fs/cgroup/cgroup.controllers ]] || return 0
 local u mem best=0 winner='' old='' weight=''
 if [[ -r "$V2_RUN/cpu.original" ]]; then
   read -r old weight < "$V2_RUN/cpu.original" || :
   if v3_safe_unit "$old" && systemctl is-active --quiet "$old"; then
     V2_BG="$old"; return 0
   fi
 fi
 for u in apt-daily.service apt-daily-upgrade.service unattended-upgrades.service packagekit.service fwupd.service man-db.service plocate-updatedb.service mlocate.service tracker-miner-fs-3.service; do
   systemctl is-active --quiet "$u" || continue
   [[ "$u" != "$V2_TARGET" ]] || continue
   mem="$(systemctl show "$u" -p MemoryCurrent --value 2>/dev/null || :)"
   [[ "$mem" =~ ^[0-9]+$ ]] || continue
   ((mem>33554432)) || continue
   if ((mem>best)); then winner="$u"; best="$mem"; fi
 done
 [[ -n "$winner" ]] && V2_BG="$winner"
 return 0
}
v2_resource(){
 local former oldw w quota group path mem
 if [[ -r "$V2_RUN/cpu.original" ]]; then
  read -r former oldw < "$V2_RUN/cpu.original" || :
  [[ "$former" == "$V2_BG" ]] || v2_restore || :
 fi
 if [[ -r /etc/v2ray-guard/astrbot-target ]]; then
    local astrbot_protected
    astrbot_protected="$(head -n 1 /etc/v2ray-guard/astrbot-target)"
    [[ "$astrbot_protected" == "systemd:$V2_BG" ]] && return 0
 fi
 case "$V2_BG" in astrbot*.service|AstrBot*.service) return 0;; esac
 [[ -n "$V2_BG" && "$V2_BG" != "$V2_TARGET" ]] || return 0
 [[ "$(systemctl show "$V2_BG" -p LoadState --value 2>/dev/null || :)" == loaded ]] || return 0
 if ((V2_CPU>=85)); then
  v2_fail_count cpu
  if ((V2_FAIL>=2)) && [[ ! -f "$V2_RUN/cpu.original" && -f /sys/fs/cgroup/cgroup.controllers ]] && v2_cool cpu; then
    quota="$(systemctl show "$V2_BG" -p CPUQuotaPerSecUSec --value 2>/dev/null || :)"
    w="$(systemctl show "$V2_BG" -p CPUWeight --value 2>/dev/null || :)"
    if [[ "$quota" == infinity || "$quota" == '[not set]' ]] && [[ "$w" =~ ^[0-9]+$ ]] && ((w>=1&&w<=10000)); then
     if systemctl set-property --runtime "$V2_BG" CPUWeight=20 CPUQuota=75% >/dev/null 2>&1; then
       printf '%s %s\n' "$V2_BG" "$w" > "$V2_RUN/cpu.original"
       v2_msg "CPU 占用 $V2_CPU%：已对低优先级后台服务 $V2_BG 临时设置单核心 75% 限制"
     fi
    fi
  fi
 elif ((V2_CPU<=65)); then
  rm -f "$V2_RUN/cpu.fail"; v2_restore || :
 fi
 ((V2_MEM<12)) || return 0
 [[ -f /sys/fs/cgroup/cgroup.controllers ]] && v2_cool memory || return 0
 group="$(systemctl show "$V2_BG" -p ControlGroup --value 2>/dev/null || :)"
 [[ "$group" == /* && "$group" != / && "$group" != *..* ]] || return 0
 path="/sys/fs/cgroup$group"
 [[ -w "$path/memory.reclaim" && -r "$path/memory.current" ]] || return 0
 read -r mem < "$path/memory.current" || return 0
 [[ "$mem" =~ ^[0-9]+$ ]] && ((mem>33554432)) || return 0
 if (printf '%s\n' 16777216 > "$path/memory.reclaim") 2>/dev/null; then
   v2_msg "可用内存 $V2_MEM%：已请求从后台服务 $V2_BG 回收 16MiB 缓存"
 fi
}
v2_check(){
 v2_root; v2_read; v2_valid_unit "$V2_TARGET" || v2_bad '未找到 V2Ray/Xray systemd 服务'
 install -d -m 0700 "$V2_RUN"
 command -v flock >/dev/null || v2_bad '缺少 flock 命令'
 exec 9>"$V2_RUN/check.lock"; flock -n 9 || return 0
 if ! systemctl is-active --quiet "$V2_TARGET"; then
   v2_msg "检测到 $V2_TARGET 未运行，正在尝试恢复"
   systemctl reset-failed "$V2_TARGET" || :
   systemctl start "$V2_TARGET" || v2_msg "启动 $V2_TARGET 失败"
   rm -f "$V2_RUN/port.fail"
 elif ((V2_PORT>0)); then
   if v2_tcp; then
    rm -f "$V2_RUN/port.fail"
    if [[ "$V2_MODE" != tcp ]] && ! v2_proxy && v2_cool proxy; then
      v2_msg '代理转发测试失败，但本地监听正常；请检查网络、DNS 或上游，不盲目重启'
    fi
   else
    v2_fail_count port
    if ((V2_FAIL>=3)) && v2_cool restart; then
       v2_msg "本地端口 $V2_PORT 连续三次检测失败，尝试恢复 $V2_TARGET"
       systemctl try-restart "$V2_TARGET" || v2_msg '重启尝试失败，请检查服务日志'
       rm -f "$V2_RUN/port.fail"
    fi
   fi
 fi
 v2_metrics
 if ((V2_MEM<12 || V2_CPU>=85)) && v2_cool pressure; then
   v2_msg "资源压力：可用内存 $V2_MEM%，CPU 占用 $V2_CPU%；不会限制 V2Ray"
 fi
 if ((V2_MEM<12 || V2_CPU>=85)); then v3_auto_candidate; fi
 v2_resource
 if [[ -x /usr/local/sbin/v2ray-guard-astrbot ]]; then
   timeout 20 /usr/local/sbin/v2ray-guard-astrbot check || v2_msg 'AstrBot 守护检测异常，请查看日志'
 fi
}
# 统一把 systemd 状态转换成简洁的中文。
v3_state(){
 case "$1" in
 active) printf '运行中';;
 inactive) printf '未运行';;
 failed) printf '异常';;
 activating) printf '启动中';;
 enabled) printf '已启用';;
 disabled) printf '未启用';;
 static) printf '静态服务';;
 masked) printf '已屏蔽';;
 *) printf '%s' "$1";;
 esac
}
v2_status(){
 v2_root; v2_read
 printf 'V2Ray 守护 v2.3.0｜保护服务：%s｜运行状态：%s｜开机启动：%s\n' "$V2_TARGET" \
  "$(v3_state "$(systemctl is-active "$V2_TARGET" 2>/dev/null || :)")" "$(v3_state "$(systemctl is-enabled "$V2_TARGET" 2>/dev/null || :)")"
 printf '定时检测：%s｜端口：%s｜模式：%s｜后台服务：%s\n' \
  "$(systemctl is-active v2ray-guard-check.timer 2>/dev/null || :)" "$V2_PORT" "$V2_MODE" "$V2_BG"
 printf '自动资源优化：%s（仅限安全白名单）｜手动指定服务：%s\n' "$V3_AUTO" "${V2_BG:-none}"
 systemctl show "$V2_TARGET" -p MainPID -p MemoryCurrent -p NRestarts || :
 awk '/^(MemTotal|MemAvailable|SwapTotal|SwapFree):/ {print}' /proc/meminfo
 if [[ -x /usr/local/sbin/v2ray-guard-astrbot ]]; then /usr/local/sbin/v2ray-guard-astrbot status || :; fi
}
v2_diagnose(){
 v2_status; v2_read
 if [[ -x /usr/local/sbin/v2ray-guard-astrbot ]]; then
   printf '\n===== AstrBot 最近日志 =====\n'
   /usr/local/sbin/v2ray-guard-astrbot logs || :
 fi
 journalctl -u "$V2_TARGET" -n 20 --no-pager || :
 journalctl -t v2ray-guard -n 15 --no-pager || :
 if ((V2_PORT>0)); then
  v2_tcp && v2_msg '本地 TCP 端口：正常' || v2_msg '本地 TCP 端口：异常'
  if [[ "$V2_MODE" != tcp ]]; then v2_proxy && v2_msg '代理 HTTPS 测试：成功' || v2_msg '代理 HTTPS 测试：失败'; fi
 else v2_msg '尚未设置检测端口，可在菜单中配置'; fi
 ip route get 1.1.1.1 2>&1 | head -n 2 || :
 timeout 5 getent ahostsv4 cp.cloudflare.com 2>/dev/null | head -n 2 || :
 ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 10 || :
}
v2_upgrade(){
 v2_root; command -v curl >/dev/null || v2_bad '请安装 curl：sudo apt install curl'
 local d expect actual
 d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT
 curl -q -fsSL --retry 2 --connect-timeout 8 --max-time 30 "$V2_RAW" -o "$d/latest.sh" || v2_bad '下载失败，已保留旧版本'
 curl -q -fsSL --retry 2 --connect-timeout 8 --max-time 20 "$V2_RAW.sha256" -o "$d/checksum" || v2_bad '无法获取校验文件，已保留旧版本'
 read -r expect _ < "$d/checksum"
 [[ "$expect" =~ ^[a-fA-F0-9]{64}$ ]] || v2_bad 'SHA-256 校验文件格式错误'
 actual="$(sha256sum "$d/latest.sh" | awk '{print $1}')"
 [[ "$actual" == "$expect" ]] || v2_bad 'SHA-256 校验不一致，已取消升级'
 bash -n "$d/latest.sh" && grep -Fq V2RAY-GUARD-PROJECT "$d/latest.sh" || v2_bad '新版脚本语法或文件标识校验失败'
 if [[ -f "$V2_BIN" ]] && cmp -s "$V2_BIN" "$d/latest.sh"; then v2_msg '当前已经是最新版本'; return; fi
 bash "$d/latest.sh"
}
# 中文菜单：命令「vg」可直接打开，所有敏感操作均通过 sudo 执行。
v3_menu(){
 v2_root
 [[ -t 0 ]] || v2_bad '中文菜单需要在终端中打开'
 local choose port mode yn
 while :; do
  v2_read
  printf '\n=======================================\n'
  printf '       V2Ray + AstrBot 双服务守护 v2.3.0\n'
  printf '=======================================\n'
  printf ' 当前服务：%s\n' "$V2_TARGET"
  printf ' 检测端口：%s     自动优化：%s\n' "$V2_PORT" "$V3_AUTO"
  printf '%s\n' '---------------------------------------'
  printf '  1. 查看运行状态\n'
  printf '  2. 立即执行健康检查\n'
  printf '  3. 故障诊断\n'
  printf '  4. 设置代理检测端口\n'
  printf '  5. 开启或关闭自动资源优化\n'
  printf '  6. 查看守护日志\n'
  printf '  7. 在线升级\n'
  printf '  8. 显示帮助\n'
  printf '  9. 查看 AstrBot 状态和日志\n'
  printf ' 10. 指定 AstrBot 服务或容器\n'
  printf ' 11. 手动启动 AstrBot\n'
  printf '  0. 退出菜单\n'
  printf '=======================================\n'
  read -r -p '请输入选项数字：' choose || return 0
  case "$choose" in
   1) v2_status || : ;;
   2) v2_check || :; printf '本次检测已结束\n' ;;
   3) v2_diagnose || : ;;
   4)
     read -r -p '请输入实际监听端口（例如 1080）：' port || return 0
     printf '检测模式：1=只检查 TCP 端口，2=SOCKS5 代理，3=HTTP 代理\n'
     read -r -p '请选择模式（默认 1）：' mode || return 0
     case "$mode" in 2) mode=socks5;; 3) mode=http;; 1|'') mode=tcp;; *) printf '无效模式，已取消设置\n'; continue;; esac
     v2_configure --port "$port" --mode "$mode" || : ;;
   5)
     if [[ "$V3_AUTO" == 1 ]]; then
       read -r -p '自动优化目前已开启，是否关闭？输入 y 确认：' yn || return 0
       [[ "$yn" == y || "$yn" == Y ]] && v2_configure --auto-off yes || printf '保持开启\n'
     else
       read -r -p '自动优化目前已关闭，是否开启？输入 y 确认：' yn || return 0
       [[ "$yn" == y || "$yn" == Y ]] && v2_configure --auto-on yes || printf '保持关闭\n'
     fi ;;
   6) journalctl -t v2ray-guard -n 60 --no-pager || : ;;
   7) v2_upgrade || :; printf '升级操作已结束，请退出后重新输入 vg 使用新版本菜单\n'; return 0 ;;
   8) v2_help ;;
   9) if [[ -x /usr/local/sbin/v2ray-guard-astrbot ]]; then
       /usr/local/sbin/v2ray-guard-astrbot status || :
       /usr/local/sbin/v2ray-guard-astrbot logs || :
      else printf 'AstrBot 守护模块未安装，请重新运行升级\n'; fi ;;
   10)
     printf '1 = systemd 服务，2 = Docker 容器\n'
     read -r -p '选择部署方式：' mode || return 0
     case "$mode" in 1) mode=systemd;; 2) mode=docker;; *) printf '无效选择\n'; continue;; esac
     read -r -p '输入服务或容器名称：' yn || return 0
     if [[ -x /usr/local/sbin/v2ray-guard-astrbot ]]; then
       /usr/local/sbin/v2ray-guard-astrbot set "$mode" "$yn" || :
     fi ;;
   11) if [[ -x /usr/local/sbin/v2ray-guard-astrbot ]]; then
          /usr/local/sbin/v2ray-guard-astrbot recover || :
       fi ;;
   0) printf '已退出菜单，守护服务仍在后台运行\n'; return 0 ;;
   *) printf '选项无效，请输入 0 到 11\n'; continue ;;
  esac
  read -r -p '按回车键返回菜单……' yn || return 0
 done
}
v2_help(){
 cat <<'HELP'
V2Ray + AstrBot 双服务守护 v2.3.0（中文版）

输入 vg 打开中文交互式菜单，无需记忆复杂命令。
自动保护 V2Ray 及 AstrBot（Docker、Compose、systemd）。
如未识别 AstrBot，请在菜单第 10 项指定名称。
自动安全资源管理默认开启，仅针对允许优化的后台维护服务。
关闭自动优化：sudo v2ray-guard --configure --auto-off yes
开启自动优化：sudo v2ray-guard --configure --auto-on yes
直接升级：sudo v2ray-guard --upgrade
手动检测：sudo v2ray-guard --check
查看状态：sudo v2ray-guard --status
故障诊断：sudo v2ray-guard --diagnose
配置端口：sudo v2ray-guard --configure --port 1080 --mode socks5
卸载守护组件（保留代理）：sudo v2ray-guard --remove
不会随意结束进程、清空全部缓存或限制代理服务自身。
HELP
}
if [[ "$V2_GUARD_LEGACY" != 1 ]]; then
 case "$1" in
  --menu|menu) v3_menu; exit $?;;
  '') if [[ "${0##*/}" == v2ray-guard ]]; then v3_menu; exit $?; fi;;
  --upgrade|upgrade) v2_upgrade; exit $?;;
  --configure|configure) shift; v2_configure "$@"; exit $?;;
  --status|status) v2_status; exit $?;;
  --diagnose|diagnose) v2_diagnose; exit $?;;
  --check|check) v2_check; exit $?;;
  --version|-V) echo 2.3.0; exit 0;;
  --help|-h|help) v2_help; exit 0;;
  --remove|remove)
   v2_root; install -d -m 0700 "$V2_RUN"; v2_restore || :
   if [[ -x /usr/local/sbin/v2ray-guard-astrbot ]]; then
     /usr/local/sbin/v2ray-guard-astrbot remove || :
     rm -f /usr/local/sbin/v2ray-guard-astrbot
   fi
   V2_GUARD_LEGACY=1 bash "$0" --remove
   rm -f "$V2_CFG"
   if [[ -f /usr/local/bin/vg ]] && grep -Fq "# Managed by ubuntu-v2ray-guard.sh" /usr/local/bin/vg; then rm -f /usr/local/bin/vg; fi
   if [[ -f "$V2_BIN" ]] && grep -Fq V2RAY-GUARD-PROJECT "$V2_BIN"; then rm -f "$V2_BIN"; fi
   exit 0 ;;
 esac
fi
# Ubuntu 低占用 V2Ray/Xray 守护脚本
# 仅管理现有 systemd 服务，不修改节点配置和端口。
set -Eeuo pipefail

readonly VERSION='2.3.0'
readonly STATE_DIR='/etc/v2ray-guard'
readonly STATE_FILE="$STATE_DIR/service"
readonly CHECKER='/usr/local/sbin/v2ray-guard-check'
readonly TIMER_UNIT='/etc/systemd/system/v2ray-guard-check.timer'
readonly CHECK_UNIT='/etc/systemd/system/v2ray-guard-check.service'
readonly ROTATE_FILE='/etc/logrotate.d/v2ray-guard'
readonly DROPIN_NAME='90-v2ray-guard.conf'
readonly SIGNATURE='# Managed by ubuntu-v2ray-guard.sh'

SERVICE=''
ACTION='install'

say()  { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'HELP'
使用方法：sudo bash ubuntu-v2ray-guard.sh [--service 服务名称] [--status|--remove|--help]

不指定服务时，自动寻找 V2Ray、Xray、x-ui 或 3x-ui 的 systemd 服务。
--service 服务名称  指定需要保护的服务，例如 v2ray.service
--status          查看服务及守护状态
--remove          卸载守护功能，不会停止或卸载代理
--help            显示帮助

安装后直接输入 vg 打开中文菜单。
本脚本配置开机启动、异常重启、每两分钟检测一次服务，并管理代理日志。
不会直接限制 V2Ray 的 CPU 和内存，也不会修改网络配置或节点信息。
HELP
}

while (($#)); do
  case "$1" in
    --service) (($# >= 2)) || fail '--service 后面缺少服务名称'; SERVICE="$2"; shift 2 ;;
    --service=*) SERVICE="${1#--service=}"; shift ;;
    --status) ACTION='status'; shift ;;
    --remove) ACTION='remove'; shift ;;
    --help|-h) usage; exit 0 ;;
    *) fail "未知选项： $1 (try --help)" ;;
  esac
done

[[ "$(id -u)" -eq 0 ]] || fail '请使用 sudo 执行此脚本'
[[ -d /run/systemd/system ]] || fail '当前未运行 systemd（不支持 Docker 内部及非 systemd 系统）'
command -v systemctl >/dev/null || fail '缺少 systemctl 命令'

validate_unit() {
  [[ "$1" =~ ^[a-zA-Z0-9_.@-]+\.service$ ]] || fail "服务名称无效：$1"
}

is_loaded() {
  local state
  state="$(systemctl show "$1" -p LoadState --value 2>/dev/null || true)"
  [[ "$state" == loaded ]]
}

select_service() {
  local candidate
  if [[ -n "$SERVICE" ]]; then
    validate_unit "$SERVICE"
    is_loaded "$SERVICE" || fail "$SERVICE 未找到；请通过 systemctl list-unit-files 查看服务名称"
    return
  fi
  if [[ -r "$STATE_FILE" ]]; then
    candidate="$(head -n 1 "$STATE_FILE")"
    if [[ "$candidate" =~ ^[a-zA-Z0-9_.@-]+\.service$ ]] && is_loaded "$candidate"; then
      SERVICE="$candidate"; return
    fi
  fi
  for candidate in v2ray.service 'v2ray@config.service' xray.service 'xray@config.service' 3x-ui.service x-ui.service; do
    if is_loaded "$candidate"; then SERVICE="$candidate"; return; fi
  done
  fail "未找到 V2Ray/Xray 的 systemd 服务，请通过 --service NAME.service 指定；不会更改 Docker 部署"
}

show_status() {
  select_service
  say "目标服务： $SERVICE"
  printf '  开机启动： %s\n' "$(systemctl is-enabled "$SERVICE" 2>/dev/null || true)"
  printf '  运行状态：      %s\n' "$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
  printf '  守护定时器：  %s\n' "$(systemctl is-active v2ray-guard-check.timer 2>/dev/null || true)"
  systemctl show "$SERVICE" -p MainPID -p NRestarts -p ActiveState -p SubState -p MemoryCurrent --no-pager 2>/dev/null || true
  printf '\n最近的服务日志：\n'
  journalctl -u "$SERVICE" --since '15 minutes ago' -n 8 --no-pager 2>/dev/null || true
}

remove_guard() {
  # 卸载时只删除脚本自身创建并标记的文件。
  if [[ -r "$STATE_FILE" ]] && [[ -z "$SERVICE" ]]; then SERVICE="$(head -n 1 "$STATE_FILE")"; fi
  [[ -z "$SERVICE" ]] || validate_unit "$SERVICE"
  systemctl disable --now v2ray-guard-check.timer >/dev/null 2>&1 || true
  for f in "$TIMER_UNIT" "$CHECK_UNIT" "$CHECKER" "$ROTATE_FILE"; do
    if [[ -f "$f" ]] && grep -Fq "$SIGNATURE" "$f"; then rm -f -- "$f"; fi
  done
  if [[ -n "$SERVICE" ]]; then
    local dropin="/etc/systemd/system/$SERVICE.d/$DROPIN_NAME"
    if [[ -f "$dropin" ]] && grep -Fq "$SIGNATURE" "$dropin"; then rm -f -- "$dropin"; fi
  fi
  [[ -f "$STATE_FILE" ]] && rm -f -- "$STATE_FILE"
  systemctl daemon-reload
  say '守护组件已经卸载，未停止或卸载代理本体'
  warn '服务重启策略的变更会在下次启动服务时完全生效'
}

if [[ "$ACTION" == remove ]]; then remove_guard; exit 0; fi
if [[ "$ACTION" == status ]]; then show_status; exit 0; fi

select_service
say "已识别服务： $SERVICE"

# 安装时不重启正在运行的代理，尽量维持已有连接。
install -d -m 0755 "$STATE_DIR" "/etc/systemd/system/$SERVICE.d"
printf '%s\n' "$SERVICE" > "$STATE_FILE"
chmod 0644 "$STATE_FILE"

cat > "/etc/systemd/system/$SERVICE.d/$DROPIN_NAME" <<'DROPIN'
# Managed by ubuntu-v2ray-guard.sh
[Unit]
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=6

[Service]
Restart=always
RestartSec=10s
# 内存不足时优先保障代理服务。
# 不预留固定内存，也不设置不合理的内存硬性上限。
OOMScoreAdjust=-300
CPUWeight=250
# 限制日志洪水，同时保留正常的故障排查日志。
LogRateLimitIntervalSec=30s
LogRateLimitBurst=120
DROPIN

cat > "$CHECKER" <<'CHECKER'
#!/usr/bin/env bash
# Managed by ubuntu-v2ray-guard.sh
set -Eeuo pipefail
STATE='/etc/v2ray-guard/service'
[[ -r "$STATE" ]] || exit 0
unit="$(head -n 1 "$STATE")"
[[ "$unit" =~ ^[a-zA-Z0-9_.@-]+\.service$ ]] || exit 1
if ! systemctl is-active --quiet "$unit"; then
  logger -t v2ray-guard -- "$unit is inactive; attempting recovery"
  systemctl reset-failed "$unit" || true
  if ! systemctl start "$unit"; then
    logger -t v2ray-guard -- "无法启动 $unit; check journalctl -u $unit"
    exit 1
  fi
fi
CHECKER
chmod 0755 "$CHECKER"

cat > "$CHECK_UNIT" <<'UNIT'
# Managed by ubuntu-v2ray-guard.sh
[Unit]
Description=V2Ray/Xray 轻量化运行检测
After=network.target
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/v2ray-guard-check
TimeoutStartSec=30s
UNIT

cat > "$TIMER_UNIT" <<'TIMER'
# Managed by ubuntu-v2ray-guard.sh
[Unit]
Description=V2Ray/Xray 定时运行检测（低资源开销）
[Timer]
OnBootSec=90s
OnUnitActiveSec=2min
AccuracySec=30s
Unit=v2ray-guard-check.service
[Install]
WantedBy=timers.target
TIMER

if command -v logrotate >/dev/null 2>&1; then
  # 如系统已有代理日志轮转规则，则不额外创建重复规则。
  logrotate_already_managed=0
  while IFS= read -r -d '' file; do
    [[ "$file" == "$ROTATE_FILE" ]] && continue
    if grep -Eq '/var/log/(v2ray|xray)/' "$file" 2>/dev/null; then
      logrotate_already_managed=1
      break
    fi
  done < <(find /etc/logrotate.d -maxdepth 1 -type f -print0 2>/dev/null)
  if [[ "$logrotate_already_managed" -eq 1 ]]; then
    if [[ -f "$ROTATE_FILE" ]] && grep -Fq "$SIGNATURE" "$ROTATE_FILE"; then
      rm -f -- "$ROTATE_FILE"
    fi
    say '已有 V2Ray/Xray 日志轮转配置，保持原设置'
  else
  cat > "$ROTATE_FILE" <<'ROTATE'
# Managed by ubuntu-v2ray-guard.sh
/var/log/v2ray/*.log /var/log/xray/*.log {
    daily
    maxsize 5M
    rotate 4
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}
ROTATE
  say '日志轮转已配置（每个文件最多保留四份轮转记录）'
  fi
else
  warn '未安装 logrotate，跳过日志轮转；如需启用请执行 sudo apt install logrotate'
fi

systemctl daemon-reload
if ! systemctl enable "$SERVICE"; then
  warn "$SERVICE 无法直接设置开机启动（可能是静态服务），定时守护仍会启用"
fi
systemctl enable --now v2ray-guard-check.timer

if systemctl is-active --quiet "$SERVICE"; then
  say 'V2Ray 服务运行正常，无须重启，保持现有连接'
else
  say '服务尚未运行，正在尝试启动'
  if ! systemctl start "$SERVICE"; then
    warn "服务 $SERVICE 启动失败，请查看 sudo journalctl -u $SERVICE -n 80 --no-pager"
    exit 1
  fi
fi

say "V2Ray 守护 v$VERSION 安装成功，已配置开机启动、异常恢复和定时检查"
show_status

# 旧版安装完成后，自动迁移为中文菜单及快捷命令。
if [[ "$V2_GUARD_LEGACY" != 1 ]]; then
 V2_SOURCE="$0"
 V2_STAGED="$V2_BIN.new.$$"
 install -m 0755 "$V2_SOURCE" "$V2_STAGED"
 mv -f "$V2_STAGED" "$V2_BIN"
 cat > /usr/local/sbin/v2ray-guard-check <<'CHECK'
#!/usr/bin/env bash
# Managed by ubuntu-v2ray-guard.sh
exec /usr/local/sbin/v2ray-guard --check
CHECK
 chmod 0755 /usr/local/sbin/v2ray-guard-check
 # 创建短命令「vg」，无需手动输入 sudo。
 if [[ ! -e /usr/local/bin/vg ]] || grep -Fq '# Managed by ubuntu-v2ray-guard.sh' /usr/local/bin/vg 2>/dev/null; then
  cat > /usr/local/bin/vg <<'VGCMD'
#!/usr/bin/env bash
# Managed by ubuntu-v2ray-guard.sh
if ((EUID==0)); then exec /usr/local/sbin/v2ray-guard "$@"; fi
exec sudo /usr/local/sbin/v2ray-guard "$@"
VGCMD
  chmod 0755 /usr/local/bin/vg
 else
  v2_msg '系统已存在 vg 命令，未覆盖；请使用 sudo v2ray-guard --menu 打开菜单'
 fi
 v2_msg 'v2.2 中文版安装完成：输入 vg 打开菜单；自动安全资源优化已开启，可使用 sudo v2ray-guard --upgrade 更新'
fi
