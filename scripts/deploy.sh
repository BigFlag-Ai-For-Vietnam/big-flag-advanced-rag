#!/usr/bin/env bash
# Deploy trên VM: rebuild + restart CHỈ những service đã đổi (backend/frontend),
# giữ nguyên infra stack (qdrant/mlflow/rustfs/postgres/nginx).
#
# Được gọi bởi self-hosted GitHub Actions runner (.github/workflows/deploy.yml) SAU khi
# cây làm việc đã được fast-forward tới commit đích. Cũng chạy tay được trên VM:
#   ./scripts/deploy.sh                 # tự dò thay đổi (BEFORE/AFTER env) hoặc rebuild cả hai
#   ./scripts/deploy.sh backend         # ép rebuild backend (+ retrieval-mcp)
#   ./scripts/deploy.sh frontend        # ép rebuild frontend
#   ./scripts/deploy.sh backend frontend
#
# Env (do workflow set, tuỳ chọn khi chạy tay):
#   DEPLOY_BEFORE  commit trước push (github.event.before) — để tính diff
#   DEPLOY_AFTER   commit sau push   (github.sha)          — mặc định HEAD
set -euo pipefail

# Chạy từ gốc repo dù được gọi ở đâu.
cd "$(dirname "$0")/.."

COMPOSE="docker compose"
INFRA_COMPOSE="docker compose -f infra/docker-compose.yml"

rebuild_backend=false
rebuild_frontend=false
recreate_nginx=false   # infra/ (compose hoặc nginx conf) đổi → recreate nginx để nạp lại

if [[ $# -gt 0 ]]; then
  # Chế độ ép tay: dùng service truyền vào.
  for svc in "$@"; do
    case "$svc" in
      backend)  rebuild_backend=true ;;
      frontend) rebuild_frontend=true ;;
      nginx)    recreate_nginx=true ;;
      *) echo "!! service không hợp lệ: $svc (chỉ backend|frontend|nginx)"; exit 2 ;;
    esac
  done
else
  # Chế độ tự dò: so diff BEFORE..AFTER. Không có thông tin diff -> rebuild cả hai.
  before="${DEPLOY_BEFORE:-}"
  after="${DEPLOY_AFTER:-HEAD}"
  if [[ -z "$before" || "$before" =~ ^0+$ ]] || ! git cat-file -e "$before^{commit}" 2>/dev/null; then
    echo ">> Không có commit gốc để so sánh — rebuild cả backend lẫn frontend."
    rebuild_backend=true
    rebuild_frontend=true
    recreate_nginx=true
  else
    changed="$(git diff --name-only "$before" "$after" || true)"
    echo ">> Files đổi giữa ${before:0:7}..${after:0:7}:"
    echo "$changed" | sed 's/^/     /'
    grep -qE '^backend/'          <<<"$changed" && rebuild_backend=true  || true
    grep -qE '^frontend/'         <<<"$changed" && rebuild_frontend=true || true
    # Đổi compose app hoặc .env → rebuild cả hai cho chắc.
    grep -qE '^(docker-compose\.yml|\.env)' <<<"$changed" && { rebuild_backend=true; rebuild_frontend=true; } || true
    # Đổi infra/ (compose infra hoặc nginx conf) → recreate nginx để nạp cert/route mới.
    grep -qE '^infra/'            <<<"$changed" && recreate_nginx=true || true
  fi
fi

# Infra phải sống trước (backend nối network rag-infra). Không --build để khỏi đụng
# mlflow image; chỉ đảm bảo các service infra đang chạy.
echo ">> Đảm bảo infra stack đang chạy…"
$INFRA_COMPOSE up -d

# nginx bind-mount app.conf: đổi conf không tự recreate; ép recreate để nạp lại config
# (đủ cho cả đổi compose lẫn đổi cert path/route).
if $recreate_nginx; then
  echo ">> Infra đổi — recreate nginx…"
  $INFRA_COMPOSE up -d --force-recreate nginx
fi

services=()
$rebuild_backend  && services+=(backend retrieval-mcp) || true
$rebuild_frontend && services+=(frontend) || true

if [[ ${#services[@]} -eq 0 ]]; then
  echo ">> Không có thay đổi backend/frontend — chỉ đảm bảo app stack đang chạy."
  $COMPOSE up -d
else
  echo ">> Rebuild: ${services[*]}"
  $COMPOSE build "${services[@]}"
  $COMPOSE up -d "${services[@]}"
fi

# Dọn image cũ (dangling) để VM khỏi đầy đĩa qua nhiều lần deploy.
docker image prune -f >/dev/null 2>&1 || true

# Health check qua nginx. big-rag.dev ép HTTPS (HTTP :80 -> 301), nên gọi thẳng HTTPS;
# -k vì SNI 'localhost' không khớp CN big-rag.dev (cùng 1 server block 443).
echo ">> Health check https://localhost/api/health …"
for i in $(seq 1 30); do
  if curl -fsSk -o /dev/null https://localhost/api/health; then
    echo ">> OK — deploy xong."
    exit 0
  fi
  sleep 2
done

echo "!! Health check thất bại sau ~60s. Log gần nhất:"
$COMPOSE ps
$COMPOSE logs --tail=50 backend || true
exit 1
