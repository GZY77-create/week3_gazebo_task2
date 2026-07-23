#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "== Static checks =="
bash -n \
  "${SCRIPT_DIR}/start_task2_sim.sh" \
  "${SCRIPT_DIR}/start_task2_all.sh" \
  "${SCRIPT_DIR}/start_task2_host.sh" \
  "${SCRIPT_DIR}/start_task2_docker.sh" \
  "${PACKAGE_DIR}/docker/entrypoint.sh"

PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/task2_pycache" \
  python3 -m py_compile \
  "${SCRIPT_DIR}/task2_mission.py" \
  "${SCRIPT_DIR}/task2_logger.py" \
  "${SCRIPT_DIR}/plot_flight.py" \
  "${SCRIPT_DIR}/check_submission.py"

if command -v xmllint >/dev/null 2>&1; then
  xmllint --noout "${PACKAGE_DIR}/package.xml" "${PACKAGE_DIR}"/launch/*.launch
else
  echo "[WARN] xmllint is unavailable; XML syntax check skipped."
fi

for evidence in \
  data/task2_final.csv \
  data/task2_final.bag \
  plots/task2_final_analysis.png \
  images/task2_gazebo_overview.jpg \
  images/task2_complete.jpg \
  images/task2_plotjuggler_position.png \
  videos/task2_demo.mp4; do
  if [[ ! -s "${PACKAGE_DIR}/${evidence}" ]]; then
    echo "[FAIL] Missing or empty evidence: ${evidence}" >&2
    exit 1
  fi
  echo "[PASS] Evidence: ${evidence}"
done

echo
echo "== Flight-data checks =="
if [[ -f /opt/ros/noetic/setup.bash ]]; then
  set +u
  source /opt/ros/noetic/setup.bash
  set -u
else
  echo "[WARN] ROS Noetic is not installed in this shell; rosbag topic validation will be skipped."
fi
python3 "${SCRIPT_DIR}/check_submission.py"
