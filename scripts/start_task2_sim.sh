#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORLD_FILE="${PACKAGE_DIR}/worlds/task2_landmarks.world"
PX4_DIR="${PX4_DIR:-/root/PX4-Autopilot}"

if [[ ! -f "${WORLD_FILE}" ]]; then
  echo "Task 2 world not found: ${WORLD_FILE}" >&2
  exit 1
fi

if [[ ! -f "${PX4_DIR}/Makefile" ]]; then
  echo "PX4 source tree not found: ${PX4_DIR}" >&2
  echo "Set PX4_DIR to the PX4-Autopilot directory." >&2
  exit 1
fi

if pgrep -x px4 >/dev/null || pgrep -x gzserver >/dev/null; then
  echo "PX4 or gzserver is already running; stop the old simulation first." >&2
  exit 1
fi

echo "Starting PX4 SITL with the independent Task 2 world:"
echo "  ${WORLD_FILE}"
cd "${PX4_DIR}"
export PX4_SITL_WORLD="${WORLD_FILE}"
exec make px4_sitl gazebo-classic_iris
