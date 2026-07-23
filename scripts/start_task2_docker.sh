#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTAINER="task2-ros-noetic"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose is required (docker compose or docker-compose)." >&2
  exit 1
fi

if ! command -v gnome-terminal >/dev/null 2>&1; then
  echo "gnome-terminal is required to open the four task terminals." >&2
  exit 1
fi

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is not set; run this script from the Ubuntu desktop." >&2
  exit 1
fi

cd "${PACKAGE_DIR}"
xhost +si:localuser:root >/dev/null
"${COMPOSE[@]}" up -d --build

for _ in $(seq 1 60); do
  if [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)" == "true" ]]; then
    TASK2_CONTAINER="${CONTAINER}" exec "${SCRIPT_DIR}/start_task2_host.sh"
  fi
  sleep 1
done

echo "Container '${CONTAINER}' did not become ready within 60 seconds." >&2
exit 1
