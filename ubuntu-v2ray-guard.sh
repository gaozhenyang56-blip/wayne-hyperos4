#!/usr/bin/env bash

# V2RAY-GUARD-PROJECT (v2)
V2_BIN=/usr/local/sbin/v2ray-guard
V2_DIR=/etc/v2ray-guard
V2_RUN=/run/v2ray-guard
V2_CFG=/etc/v2ray-guard/probe.conf
V2_RAW=https://raw.githubusercontent.com/gaozhenyang56-blip/wayne-hyperos4/ubuntu-v2ray-guard/ubuntu-v2ray-guard.sh
v2_msg(){ printf '[Guard v2] %s\n' "$*"; logger -t v2ray-guard -- "$*" 2>/dev/null || :; }
v2_bad(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
v2_root(){ ((EUID==0)) || v2_bad 'Run with sudo'; [[ -d /run/systemd/system ]] || v2_bad 'systemd required'; }
v2_valid_unit(){ [[ "$1" =~ ^[a-zA-Z0-9_.@-]+\.service$ ]]; }
v2_read(){
 V2_PORT=0 V2_MODE=tcp V2_BG='' V2_TARGET=''
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
   esac
  done < "$V2_CFG"
 fi
}
v2_configure(){
 v2_root; v2_read; local chosen
 while (($#)); do
  (($#>=2)) || v2_bad "Missing value for $1"
  case "$1" in
   --port) V2_PORT="$2";;
   --mode) V2_MODE="$2";;
   --background-unit) V2_BG="$2";;
   --disable-background) V2_BG='';;
   *) v2_bad "Invalid option $1";;
  esac
  shift 2
 done
 [[ "$V2_PORT" =~ ^[0-9]+$ ]] && ((10#$V2_PORT <= 65535)) || v2_bad 'Invalid port'
 [[ "$V2_MODE" =~ ^(tcp|http|socks5)$ ]] || v2_bad 'Invalid mode'
 [[ "$V2_MODE" == tcp || "$V2_PORT" != 0 ]] || v2_bad 'Proxy probe requires --port'
 if [[ -n "$V2_BG" ]]; then
   v2_valid_unit "$V2_BG" && [[ "$V2_BG" != "$V2_TARGET" ]] || v2_bad 'Unsafe background unit'
   [[ "$(systemctl show "$V2_BG" -p LoadState --value 2>/dev/null || :)" == loaded ]] || v2_bad 'Unknown background unit'
   case "$V2_BG" in
    ssh.service|sshd.service|systemd-*.service|network*.service|NetworkManager.service|dbus.service|cron.service|docker.service|containerd.service|nginx.service|apache2.service|ufw.service|firewalld.service|v2ray*.service|xray*.service|x-ui.service|3x-ui.service)
       v2_bad 'Cannot optimize critical/network/proxy services';;
   esac
 fi
 install -d -m 0700 "$V2_DIR"
 (umask 077; printf 'PORT=%s\nMODE=%s\nBG=%s\n' "$V2_PORT" "$V2_MODE" "$V2_BG" > "$V2_CFG")
 v2_msg "Configured port=$V2_PORT type=$V2_MODE background=$V2_BG"
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
 v2_msg "Restored background unit CPU settings $u"
}
v2_resource(){
 local former oldw w quota group path mem
 if [[ -r "$V2_RUN/cpu.original" ]]; then
  read -r former oldw < "$V2_RUN/cpu.original" || :
  [[ "$former" == "$V2_BG" ]] || v2_restore || :
 fi
 [[ -n "$V2_BG" && "$V2_BG" != "$V2_TARGET" ]] || return 0
 [[ "$(systemctl show "$V2_BG" -p LoadState --value 2>/dev/null || :)" == loaded ]] || return 0
 if ((V2_CPU>=85)); then
  v2_fail_count cpu
  if ((V2_FAIL>=2)) && [[ ! -f "$V2_RUN/cpu.original" && -f /sys/fs/cgroup/cgroup.controllers ]] && v2_cool cpu; then
    quota="$(systemctl show "$V2_BG" -p CPUQuotaPerSecUSec --value 2>/dev/null || :)"
    w="$(systemctl show "$V2_BG" -p CPUWeight --value 2>/dev/null || :)"
    if [[ "$quota" == infinity || "$quota" == '[not set]' ]] && [[ "$w" =~ ^[0-9]+$ ]] && ((w>=1&&w<=10000)); then
     if systemctl set-property --runtime "$V2_BG" CPUWeight=20 CPUQuota=50% >/dev/null 2>&1; then
       printf '%s %s\n' "$V2_BG" "$w" > "$V2_RUN/cpu.original"
       v2_msg "CPU pressure $V2_CPU%: throttled OPTIONAL $V2_BG to 50% of one CPU"
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
   v2_msg "Low MemAvailable $V2_MEM%: requested 16MiB reclaim from opted-in $V2_BG"
 fi
}
v2_check(){
 v2_root; v2_read; v2_valid_unit "$V2_TARGET" || v2_bad 'Missing V2Ray service'
 install -d -m 0700 "$V2_RUN"
 command -v flock >/dev/null || v2_bad 'flock required'
 exec 9>"$V2_RUN/check.lock"; flock -n 9 || return 0
 if ! systemctl is-active --quiet "$V2_TARGET"; then
   v2_msg "$V2_TARGET inactive; trying recovery"
   systemctl reset-failed "$V2_TARGET" || :
   systemctl start "$V2_TARGET" || v2_msg "Failed to start $V2_TARGET"
   rm -f "$V2_RUN/port.fail"
 elif ((V2_PORT>0)); then
   if v2_tcp; then
    rm -f "$V2_RUN/port.fail"
    if [[ "$V2_MODE" != tcp ]] && ! v2_proxy && v2_cool proxy; then
      v2_msg 'Proxy traffic probe failed; local listener OK. Diagnose upstream/network, no blind restart.'
    fi
   else
    v2_fail_count port
    if ((V2_FAIL>=3)) && v2_cool restart; then
       v2_msg "Local port $V2_PORT absent for 3 checks; controlled $V2_TARGET restart"
       systemctl try-restart "$V2_TARGET" || v2_msg 'Restart attempt failed'
       rm -f "$V2_RUN/port.fail"
    fi
   fi
 fi
 v2_metrics
 if ((V2_MEM<12 || V2_CPU>=85)) && v2_cool pressure; then
   v2_msg "Pressure: MemAvailable=$V2_MEM% CPU=$V2_CPU%; V2Ray never throttled"
 fi
 v2_resource
}
v2_status(){
 v2_root; v2_read
 printf 'V2Ray Guard 2.0.0 service=%s active=%s boot=%s\n' "$V2_TARGET" \
  "$(systemctl is-active "$V2_TARGET" 2>/dev/null || :)" "$(systemctl is-enabled "$V2_TARGET" 2>/dev/null || :)"
 printf 'timer=%s port=%s mode=%s background=%s\n' \
  "$(systemctl is-active v2ray-guard-check.timer 2>/dev/null || :)" "$V2_PORT" "$V2_MODE" "$V2_BG"
 systemctl show "$V2_TARGET" -p MainPID -p MemoryCurrent -p NRestarts || :
 awk '/^(MemTotal|MemAvailable|SwapTotal|SwapFree):/ {print}' /proc/meminfo
}
v2_diagnose(){
 v2_status; v2_read
 journalctl -u "$V2_TARGET" -n 20 --no-pager || :
 journalctl -t v2ray-guard -n 15 --no-pager || :
 if ((V2_PORT>0)); then
  v2_tcp && v2_msg 'TCP listener: OK' || v2_msg 'TCP listener: FAILED'
  if [[ "$V2_MODE" != tcp ]]; then v2_proxy && v2_msg 'Proxy HTTPS: OK' || v2_msg 'Proxy HTTPS: FAILED'; fi
 else v2_msg 'No port set. Use --configure --port N --mode tcp|socks5|http'; fi
 ip route get 1.1.1.1 2>&1 | head -n 2 || :
 timeout 5 getent ahostsv4 cp.cloudflare.com 2>/dev/null | head -n 2 || :
 ps -eo pid,comm,%cpu,%mem --sort=-%mem | head -n 10 || :
}
v2_upgrade(){
 v2_root; command -v curl >/dev/null || v2_bad 'apt install curl'
 local d expect actual
 d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT
 curl -q -fsSL --retry 2 --connect-timeout 8 --max-time 30 "$V2_RAW" -o "$d/latest.sh" || v2_bad 'Download failed; old script kept'
 curl -q -fsSL --retry 2 --connect-timeout 8 --max-time 20 "$V2_RAW.sha256" -o "$d/checksum" || v2_bad 'Checksum unavailable; old script kept'
 read -r expect _ < "$d/checksum"
 [[ "$expect" =~ ^[a-fA-F0-9]{64}$ ]] || v2_bad 'Malformed checksum'
 actual="$(sha256sum "$d/latest.sh" | awk '{print $1}')"
 [[ "$actual" == "$expect" ]] || v2_bad 'Checksum mismatch'
 bash -n "$d/latest.sh" && grep -Fq V2RAY-GUARD-PROJECT "$d/latest.sh" || v2_bad 'Syntax/identity check failed'
 if [[ -f "$V2_BIN" ]] && cmp -s "$V2_BIN" "$d/latest.sh"; then v2_msg 'Already latest'; return; fi
 bash "$d/latest.sh"
}
v2_help(){
 cat <<'HELP'
V2Ray Guard v2
Install/migrate: sudo bash ubuntu-v2ray-guard.sh
Direct upgrade: sudo v2ray-guard --upgrade
Probe: sudo v2ray-guard --configure --port 1080 --mode socks5
TCP: sudo v2ray-guard --configure --port 443 --mode tcp
Optional background memory/CPU relief:
  sudo v2ray-guard --configure --background-unit my-worker.service
Disable optional unit:
  sudo v2ray-guard --configure --disable-background yes
Status: sudo v2ray-guard --status
Diagnostics: sudo v2ray-guard --diagnose
Manual check: sudo v2ray-guard --check
Uninstall guard only: sudo v2ray-guard --remove
No indiscriminate process killing, global cache flushing or V2Ray hard caps.
HELP
}
if [[ "$V2_GUARD_LEGACY" != 1 ]]; then
 case "$1" in
  --upgrade|upgrade) v2_upgrade; exit $?;;
  --configure|configure) shift; v2_configure "$@"; exit $?;;
  --status|status) v2_status; exit $?;;
  --diagnose|diagnose) v2_diagnose; exit $?;;
  --check|check) v2_check; exit $?;;
  --version|-V) echo 2.0.0; exit 0;;
  --help|-h|help) v2_help; exit 0;;
  --remove|remove)
   v2_root; install -d -m 0700 "$V2_RUN"; v2_restore || :
   V2_GUARD_LEGACY=1 bash "$0" --remove
   rm -f "$V2_CFG"
   if [[ -f "$V2_BIN" ]] && grep -Fq V2RAY-GUARD-PROJECT "$V2_BIN"; then rm -f "$V2_BIN"; fi
   exit 0 ;;
 esac
fi
# Ubuntu V2Ray/Xray low-overhead reliability guard
# Manages only an existing systemd service; never changes proxy configs/ports.
set -Eeuo pipefail

readonly VERSION='2.0.0'
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
Usage: sudo bash ubuntu-v2ray-guard.sh [--service UNIT] [--status|--remove|--help]

Without --service, searches for V2Ray/Xray and common x-ui/3x-ui service names.
--service UNIT  Existing systemd service to protect (example: v2ray.service)
--status        Show service and guard state (no changes)
--remove        Remove guard configuration (does NOT uninstall/stop V2Ray)
--help          Show help

Behavior: enable at boot, retry on failure, health-check every 2 minutes,
log rotation for /var/log/v2ray/*.log and /var/log/xray/*.log when available.
Does not impose a CPU/RAM cap, modify networking, or edit your V2Ray config.
HELP
}

while (($#)); do
  case "$1" in
    --service) (($# >= 2)) || fail 'Missing value after --service'; SERVICE="$2"; shift 2 ;;
    --service=*) SERVICE="${1#--service=}"; shift ;;
    --status) ACTION='status'; shift ;;
    --remove) ACTION='remove'; shift ;;
    --help|-h) usage; exit 0 ;;
    *) fail "Unknown option: $1 (try --help)" ;;
  esac
done

[[ "$(id -u)" -eq 0 ]] || fail 'Root required: run with sudo bash ...'
[[ -d /run/systemd/system ]] || fail 'systemd is not running (Docker/non-systemd hosts are unsupported)'
command -v systemctl >/dev/null || fail 'systemctl is missing'

validate_unit() {
  [[ "$1" =~ ^[a-zA-Z0-9_.@-]+\.service$ ]] || fail "Invalid service unit name: $1"
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
    is_loaded "$SERVICE" || fail "$SERVICE not found. Use systemctl list-unit-files | grep -Ei 'v2ray|xray'"
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
  fail "Couldn't find a systemd V2Ray/Xray service. Supply --service NAME.service. Docker installations aren't modified."
}

show_status() {
  select_service
  say "Target service: $SERVICE"
  printf '  boot enabled: %s\n' "$(systemctl is-enabled "$SERVICE" 2>/dev/null || true)"
  printf '  running:      %s\n' "$(systemctl is-active "$SERVICE" 2>/dev/null || true)"
  printf '  guard timer:  %s\n' "$(systemctl is-active v2ray-guard-check.timer 2>/dev/null || true)"
  systemctl show "$SERVICE" -p MainPID -p NRestarts -p ActiveState -p SubState -p MemoryCurrent --no-pager 2>/dev/null || true
  printf '\nRecent service logs:\n'
  journalctl -u "$SERVICE" --since '15 minutes ago' -n 8 --no-pager 2>/dev/null || true
}

remove_guard() {
  # Cleanup is restricted to our marker-protected files.
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
  say 'Guard removed. The proxy service itself was NOT stopped or uninstalled.'
  warn 'If already running, service restart-policy changes fully take effect at the next service restart.'
}

if [[ "$ACTION" == remove ]]; then remove_guard; exit 0; fi
if [[ "$ACTION" == status ]]; then show_status; exit 0; fi

select_service
say "Detected service: $SERVICE"

# A successful install never restarts an already-running proxy, preserving sessions.
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
# Prefer retaining the proxy over nonessential processes when memory is scarce.
# This does not reserve memory or impose an arbitrary hard memory limit.
OOMScoreAdjust=-300
# Rate-limit log floods without suppressing ordinary diagnostic logs.
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
    logger -t v2ray-guard -- "Could not start $unit; check journalctl -u $unit"
    exit 1
  fi
fi
CHECKER
chmod 0755 "$CHECKER"

cat > "$CHECK_UNIT" <<'UNIT'
# Managed by ubuntu-v2ray-guard.sh
[Unit]
Description=V2Ray/Xray lightweight availability check
After=network.target
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/v2ray-guard-check
TimeoutStartSec=30s
UNIT

cat > "$TIMER_UNIT" <<'TIMER'
# Managed by ubuntu-v2ray-guard.sh
[Unit]
Description=Periodic V2Ray/Xray availability check (low overhead)
[Timer]
OnBootSec=90s
OnUnitActiveSec=2min
AccuracySec=30s
Unit=v2ray-guard-check.service
[Install]
WantedBy=timers.target
TIMER

if command -v logrotate >/dev/null 2>&1; then
  # Don't create a second rotation rule for already-managed V2Ray logs.
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
    say 'An existing V2Ray/Xray logrotate policy was found; leaving it unchanged.'
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
  say 'Log rotation configured (up to 4 rotations per log).'
  fi
else
  warn 'logrotate is not installed; skipped log rotation. To enable: sudo apt install logrotate'
fi

systemctl daemon-reload
if ! systemctl enable "$SERVICE"; then
  warn "$SERVICE cannot be enabled directly (possibly a static unit). Timer protection still enabled."
fi
systemctl enable --now v2ray-guard-check.timer

if systemctl is-active --quiet "$SERVICE"; then
  say 'V2Ray service already running. No restart performed, preserving live connections.'
else
  say 'Service not running; trying to start it.'
  if ! systemctl start "$SERVICE"; then
    warn "Couldn't start $SERVICE. View errors: sudo journalctl -u $SERVICE -n 80 --no-pager"
    exit 1
  fi
fi

say "Installed v$VERSION. Boot start, restart-on-failure, periodic guard are configured."
show_status

# v2 migration after successful v1-compatible install.
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
 v2_msg 'v2 installed. Future direct upgrades: sudo v2ray-guard --upgrade'
fi
