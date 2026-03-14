#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
WEB_PORT="${WEB_PORT:-5000}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
START_SERVICES="${START_SERVICES:-1}"

mkdir -p "$LOG_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python runtime not found: $PYTHON_BIN"
  echo "Create the venv first, for example: python3.9 -m venv .venv && .venv/bin/pip install -r requirements_dev.txt -c constraints/py39.txt"
  exit 1
fi

if [[ "$START_SERVICES" == "1" ]]; then
  docker compose -f docker-compose.services.yml up -d
fi

pids=()

cleanup() {
  if [[ ${#pids[@]} -gt 0 ]]; then
    echo "Stopping ZSpider processes..."
    kill "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

start_component() {
  local name="$1"
  shift
  echo "Starting $name ..."
  if [[ "$name" == "web" ]]; then
    ZSPIDER_WEB_HOST="$WEB_HOST" "$PYTHON_BIN" -m "$@" > "$LOG_DIR/${name}.log" 2>&1 &
  else
    "$PYTHON_BIN" -m "$@" > "$LOG_DIR/${name}.log" 2>&1 &
  fi
  pids+=("$!")
}

start_component dispatcher zspider.dispatcher
start_component crawler zspider.crawler
start_component web zspider.web "$WEB_PORT"

echo
cat <<MSG
ZSpider is starting.

Web admin: http://127.0.0.1:${WEB_PORT}
First login: any username + password creates the initial admin account when the user table is empty.
Logs:
  - $LOG_DIR/dispatcher.log
  - $LOG_DIR/crawler.log
  - $LOG_DIR/web.log

Press Ctrl+C to stop all local processes started by this script.
MSG

echo
wait -n "${pids[@]}"
