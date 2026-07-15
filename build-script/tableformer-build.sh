#!/usr/bin/env bash
set -euo pipefail

# 이 스크립트는 프로젝트 루트에서 실행된다고 가정
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CONF_FILE="${BASE_DIR}/build-script/tableformer-build.config"
if [[ ! -f "$CONF_FILE" ]]; then
  echo "config file not found: $CONF_FILE"
  exit 1
fi

# shellcheck source=/dev/null
source "$CONF_FILE"

# 기본값
CONTEXT="${CONTEXT:-$BASE_DIR}"
DOCKERFILE="${DOCKERFILE:-docker/Dockerfile}"
IMAGE_NAME="${IMAGE_NAME:-doc-parser-tableformer}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-}"
MODE="${MODE:-accurate}"

if [[ -n "$REGISTRY" ]]; then
  FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
else
  FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo "[INFO] building image: $FULL_IMAGE"
echo "[INFO] context      : $CONTEXT"
echo "[INFO] dockerfile   : $DOCKERFILE"
echo "[INFO] mode         : $MODE"

docker build \
  --file "$DOCKERFILE" \
  --build-arg MODE="${MODE}" \
  --tag "$FULL_IMAGE" \
  "$CONTEXT"

echo "[INFO] build done: $FULL_IMAGE"

if [[ -n "$REGISTRY" ]]; then
  echo "[INFO] pushing to $FULL_IMAGE"
  docker push "$FULL_IMAGE"
fi
