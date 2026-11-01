#!/bin/zsh
set -e
cd "$(dirname "$0")"
PORT="${FLUENT_LAB_PORT:-8765}"
if ! command -v python3 >/dev/null 2>&1; then
  echo "需要安装 Python 3 来运行本地网页服务。"
  read -r "?按 Enter 退出..."
  exit 1
fi
URL="http://127.0.0.1:${PORT}/"
echo "Fluent Lab running at: ${URL}"
echo "只在本机提供服务，关闭这个终端窗口即可停止。"
python3 -m http.server "${PORT}" --bind 127.0.0.1 &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT INT TERM
sleep 1
open "${URL}"
wait "${SERVER_PID}"
