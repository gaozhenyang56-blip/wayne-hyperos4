#!/usr/bin/env bash
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo '请使用 root 执行。' >&2
  exit 1
fi
deploy_dir=/opt/astrbot
if [ -e "$deploy_dir" ]; then
  echo '/opt/astrbot 已存在，请先检查，脚本不会覆盖。' >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1; then
  command -v curl >/dev/null 2>&1 || { echo '请先安装 curl。' >&2; exit 1; }
  installer_path=$(mktemp)
  trap 'rm -f "$installer_path"' EXIT
  curl -fsSL https://get.docker.com -o "$installer_path"
  sh "$installer_path"
fi
docker compose version >/dev/null
systemctl enable --now docker
if ss -ltnH '( sport = :6185 )' | read -r _; then
  echo '6185 端口已占用，请检查现有服务。' >&2
  exit 1
fi
install -d -m 0700 "$deploy_dir"
cat > "$deploy_dir/compose.yaml" <<'YAML'
services:
  astrbot:
    image: soulter/astrbot:latest
    restart: always
    init: true
    security_opt:
      - no-new-privileges:true
    ports:
      - "127.0.0.1:6185:6185"
    environment:
      TZ: Asia/Shanghai
    volumes:
      - ./data:/AstrBot/data
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
YAML
cd "$deploy_dir"
docker compose config -q
docker compose pull
docker compose up -d
docker compose ps
app_ready=false
for attempt in $(seq 1 30); do
  if curl -fsS --max-time 3 -o /dev/null http://127.0.0.1:6185/; then
    app_ready=true
    break
  fi
  sleep 2
done
if [ "$app_ready" != true ]; then
  echo '管理面板尚未就绪，请在服务器本机检查容器日志；日志不会上传到 Actions。' >&2
  exit 1
fi
echo '管理面板 HTTP 检查成功。'
echo '容器已启动；请在本机查看 docker compose logs 获取启动状态和初始凭据。'
echo '电脑建立 SSH 隧道：ssh -N -L 6185:127.0.0.1:6185 root@107.150.7.124'
echo '浏览器访问 http://127.0.0.1:6185 ，登录后修改初始密码。'
echo '若容器刚启动，请等待初始化完成；启动命令成功不等于应用已就绪。'
