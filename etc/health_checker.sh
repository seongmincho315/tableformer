#!/usr/bin/env bash
# Supervisor EventListener 프로토콜: READY/RESULT 로 통신
# 참고: https://supervisord.org/events.html

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${TABLEFORMER_PORT:-8080}/healthcheck}"
TIMEOUT="${HEALTH_TIMEOUT:-3}"
RETRIES="${HEALTH_RETRIES:-3}"

while true; do
  echo "READY"
  read -r line || exit 1
  headers=""
  while read -r h && [ "$h" != "" ]; do
    headers+="$h"$'\n'
  done

  ok=0
  for i in $(seq 1 "$RETRIES"); do
    if curl -fsS --max-time "$TIMEOUT" "$HEALTH_URL" >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 1
  done

  if [ $ok -eq 1 ]; then
    echo -ne "RESULT 2\nOK"
  else
    # supervisord.conf의 [program:tableformer] 이름과 반드시 일치해야 함
    # (paddle-ocr 레포에서 이 이름이 어긋나 재시작이 안 먹었던 버그가 있었음)
    /usr/bin/supervisorctl restart tableformer >/dev/null 2>&1 || true
    echo -ne "RESULT 13\nRESTARTED"
  fi
done
