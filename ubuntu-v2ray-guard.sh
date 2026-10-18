#!/usr/bin/env bash
# Ubuntu V2Ray/Xray low-overhead reliability guard
# Manages only an existing systemd service; never changes proxy configs/ports.
set -Eeuo pipefail

readonly VERSION='1.0.0'
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
