#!/bin/bash
# Build EE image with China-friendly defaults (mirrors + cache).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_TAG="${IMAGE_TAG:-jumpserver/ansible-executor:latest}"
EE_FILE="${EE_FILE:-execution-environment.yml}"
GITHUB_MIRROR="${GITHUB_MIRROR:-https://ghfast.top/}"
USE_CHINA_MIRROR="${USE_CHINA_MIRROR:-1}"

if ! command -v ansible-builder >/dev/null 2>&1; then
  echo "ansible-builder not found. Install: pip install ansible-builder" >&2
  exit 1
fi

# Optional: rewrite GitHub zip URLs via mirror (speed up ansible-core / ansible-runner download).
# 临时 EE 必须放在 SCRIPT_DIR：ansible-builder 按 EE 文件所在目录解析 requirements-python.txt 等相对路径。
WORK_EE="$EE_FILE"
if [ "$USE_CHINA_MIRROR" = "1" ] && [ -n "$GITHUB_MIRROR" ]; then
  WORK_EE="$(mktemp "${SCRIPT_DIR}/.execution-environment.XXXXXX.yml")"
  sed \
    -e "s|https://github.com/|${GITHUB_MIRROR}https://github.com/|g" \
    "$EE_FILE" > "$WORK_EE"
  trap 'rm -f "$WORK_EE"' EXIT
fi

export DOCKER_BUILDKIT=1

echo "==> image: $IMAGE_TAG"
echo "==> ee file: $WORK_EE"
echo "==> github mirror: ${GITHUB_MIRROR:-disabled}"
echo "==> tip: configure Docker Desktop registry mirrors for quay.io / docker.io"

ansible-builder build \
  -f "$WORK_EE" \
  -t "$IMAGE_TAG" \
  --container-runtime docker \
  "$@"
