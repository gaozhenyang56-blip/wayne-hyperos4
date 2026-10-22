#!/usr/bin/env bash
# AstrBot 守护模块（供 V2Ray Guard 使用）
# Managed by ubuntu-v2ray-guard.sh
set -Eeuo pipefail
STATE=/etc/v2ray-guard/astrbot-target
POLICY=/etc/v2ray-guard/astrbot-policy-backup
RUNDIR=/run/v2ray-guard
AB_TYPE='' AB_NAME=''
msg(){ printf '[AstrBot 守护] %s\n' "$*"; logger -t v2ray-guard -- "AstrBot: $*" 2>/dev/null || :; }
die(){ msg "错误：$*" >&2; exit 1; }
valid(){ [[ "$1" =~ ^[a-zA-Z0-9_.@-]+\.service$ ]]; }
loaded(){ [[ "$(systemctl show "$1" -p LoadState --value 2>/dev/null || :)" == loaded ]]; }
exists(){ command -v docker >/dev/null 2>&1 && docker inspect --type container "$1" >/dev/null 2>&1; }
detect(){
 AB_TYPE='' AB_NAME=''
 local type='' name='' u found
 if [[ -r "$STATE" ]]; then
  IFS=: read -r type name < "$STATE" || :
  if [[ "$type" == systemd ]] && valid "$name" && loaded "$name"; then AB_TYPE=systemd; AB_NAME="$name"; return; fi
  if [[ "$type" == docker ]] && [[ "$name" =~ ^[a-zA-Z0-9_.-]+$ ]] && exists "$name"; then AB_TYPE=docker; AB_NAME="$name"; return; fi
 fi
 for u in astrbot.service AstrBot.service astrbot-bot.service; do
   if loaded "$u"; then AB_TYPE=systemd; AB_NAME="$u"; return; fi
 done
 command -v docker >/dev/null 2>&1 || return 0
 if exists astrbot; then AB_TYPE=docker; AB_NAME=astrbot; return; fi
 found="$(docker ps -a --filter label=com.docker.compose.service=astrbot --format '{{.Names}}' 2>/dev/null || :)"
 if [[ -n "$found" && "$found" != *$'\n'* && "$found" =~ ^[a-zA-Z0-9_.-]+$ ]]; then AB_TYPE=docker; AB_NAME="$found"; fi
}
cool(){
 local f="$RUNDIR/astrbot-$1.stamp" n o=0
 install -d -m 0700 "$RUNDIR"
 n="$(date +%s)"
 [[ -r "$f" ]] && read -r o < "$f" || :
 [[ "$o" =~ ^[0-9]+$ ]] || o=0
 ((n-o>=900)) || return 1
 printf '%s\n' "$n" > "$f"
}
setup(){
 detect
 [[ -n "$AB_TYPE" ]] || { msg '未识别到 AstrBot，请在 vg 菜单指定服务或容器'; return 0; }
 if [[ "$AB_TYPE" == systemd ]]; then
   local t f
   t="$(systemctl show "$AB_NAME" -p Type --value 2>/dev/null || :)"
   if [[ "$t" == oneshot ]]; then msg "AstrBot $AB_NAME 是一次性服务，跳过自动重启配置"; return 0; fi
   f="/etc/systemd/system/$AB_NAME.d/90-v2ray-guard.conf"
   install -d -m 0755 "/etc/systemd/system/$AB_NAME.d"
   if [[ -f "$f" ]] && ! grep -Fq '# Managed by ubuntu-v2ray-guard.sh' "$f"; then
     msg "已有用户配置 $f，未覆盖"; return 0
   fi
   cat > "$f" <<'UNIT'
# Managed by ubuntu-v2ray-guard.sh
[Unit]
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=6
[Service]
Restart=always
RestartSec=12s
OOMScoreAdjust=-250
CPUWeight=250
UNIT
   systemctl daemon-reload
   systemctl enable "$AB_NAME" >/dev/null 2>&1 || msg "服务 $AB_NAME 无法直接设置开机启动，定时守护仍会检查"
   if ! systemctl is-active --quiet "$AB_NAME"; then
     systemctl start "$AB_NAME" || msg "启动 $AB_NAME 失败，请查看日志"
   fi
   msg "已保护 AstrBot systemd 服务：$AB_NAME；未重启正在运行的机器人"
 else
   local p
   p="$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$AB_NAME" 2>/dev/null || :)"
   case "$p" in
    always|unless-stopped) msg "保留 Docker 自动重启策略：$p";;
    no|on-failure|'')
      if [[ ! -f "$POLICY" ]]; then
        (umask 077; printf '%s:%s\n' "$AB_NAME" "${p:-no}" > "$POLICY")
      fi
      if docker update --restart unless-stopped "$AB_NAME" >/dev/null 2>&1; then
        msg "容器 $AB_NAME 已设置异常恢复和开机自启"
      else msg "Docker 重启策略设置失败：$AB_NAME"; fi;;
    *) msg "保留容器原有重启策略：$p";;
   esac
   msg "已识别 AstrBot 容器 $AB_NAME；不会重建容器或修改配置"
 fi
}
check(){
 detect
 [[ -n "$AB_TYPE" ]] || { cool notfound && msg '未发现 AstrBot，无法执行保活' || :; return 0; }
 if [[ "$AB_TYPE" == systemd ]]; then
   if ! systemctl is-active --quiet "$AB_NAME" && cool svc; then
     msg "AstrBot $AB_NAME 未运行，正在尝试恢复"
     systemctl reset-failed "$AB_NAME" || :
     systemctl start "$AB_NAME" || msg "AstrBot $AB_NAME 恢复失败"
   fi
 else
   local running code health
   running="$(docker inspect -f '{{.State.Running}}' "$AB_NAME" 2>/dev/null || :)"
   if [[ "$running" == true ]]; then
     health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$AB_NAME" 2>/dev/null || :)"
     if [[ "$health" == unhealthy ]] && cool unhealthy; then
       msg "AstrBot $AB_NAME 容器健康异常；为防止影响会话，未盲目重启"
     fi
   else
     code="$(docker inspect -f '{{.State.ExitCode}}' "$AB_NAME" 2>/dev/null || :)"
     if [[ "$code" =~ ^[0-9]+$ ]] && ((code>0)) && cool crashed; then
       msg "AstrBot $AB_NAME 异常退出（代码 $code），尝试启动"
       docker start "$AB_NAME" >/dev/null 2>&1 || msg "AstrBot $AB_NAME 恢复失败"
     elif cool stopped; then msg "AstrBot $AB_NAME 已停止，可能是人为关闭，不强制启动"; fi
   fi
 fi
}
status(){
 detect
 if [[ -z "$AB_TYPE" ]]; then printf 'AstrBot：尚未识别，请在菜单指定\n'; return 0; fi
 if [[ "$AB_TYPE" == systemd ]]; then
   printf 'AstrBot：systemd 服务 %s｜运行：%s｜开机：%s\n' "$AB_NAME" \
     "$(systemctl is-active "$AB_NAME" 2>/dev/null || :)" "$(systemctl is-enabled "$AB_NAME" 2>/dev/null || :)"
 else
   printf 'AstrBot：Docker 容器 %s｜运行：%s｜重启策略：%s\n' "$AB_NAME" \
     "$(docker inspect -f '{{.State.Status}}' "$AB_NAME" 2>/dev/null || :)" \
     "$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$AB_NAME" 2>/dev/null || :)"
 fi
}
logs(){
 detect
 if [[ "$AB_TYPE" == systemd ]]; then journalctl -u "$AB_NAME" -n 25 --no-pager || :
 elif [[ "$AB_TYPE" == docker ]]; then docker logs --tail 25 "$AB_NAME" 2>&1 || :
 else msg '未识别 AstrBot，无法查询日志'; fi
}
recover(){
 detect
 if [[ "$AB_TYPE" == systemd ]]; then systemctl start "$AB_NAME"
 elif [[ "$AB_TYPE" == docker ]]; then docker start "$AB_NAME"
 else msg '未识别 AstrBot，请先指定服务或容器'; fi
}
pin(){
 local type="$1" name="$2"
 case "$type" in
  systemd) valid "$name" && loaded "$name" || die "服务不存在：$name";;
  docker) [[ "$name" =~ ^[a-zA-Z0-9_.-]+$ ]] && exists "$name" || die "容器不存在：$name";;
  *) die '部署类型只能是 systemd 或 docker';;
 esac
 install -d -m 0700 /etc/v2ray-guard
 (umask 077; printf '%s:%s\n' "$type" "$name" > "$STATE")
 setup
}
uninstall(){
 detect
 local f name policy
 if [[ "$AB_TYPE" == systemd ]]; then
   f="/etc/systemd/system/$AB_NAME.d/90-v2ray-guard.conf"
   if [[ -f "$f" ]] && grep -Fq '# Managed by ubuntu-v2ray-guard.sh' "$f"; then
     rm -f "$f"; systemctl daemon-reload
   fi
 fi
 if [[ -r "$POLICY" ]]; then
   IFS=: read -r name policy < "$POLICY" || :
   if [[ "$name" =~ ^[a-zA-Z0-9_.-]+$ ]] && [[ "$policy" =~ ^(no|on-failure)$ ]] && exists "$name"; then
     docker update --restart "$policy" "$name" >/dev/null 2>&1 || msg 'Docker 原有策略恢复失败，请手动检查'
   fi
 fi
 rm -f "$POLICY" "$STATE"
 msg 'AstrBot 守护已移除，机器人和数据未删除'
}
((EUID==0)) || die '请用 sudo 运行'
[[ -d /run/systemd/system ]] || die '仅支持 systemd 主机'
case "${1:-}" in
 install) setup;; check) check;; status) status;; logs) logs;; recover) recover;;
 set) (($#>=3)) || die '参数不足'; pin "$2" "$3";;
 remove) uninstall;;
 *) die '用法：astrbot-guard {install|check|status|logs|recover|set systemd|docker 名称|remove}';;
esac
