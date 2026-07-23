#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${TASK2_CONTAINER:-ros-noetic}"
WORKSPACE="/root/catkin_ws"
PACKAGE="${WORKSPACE}/src/week3_gazebo_task2"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
CSV_FILE="${PACKAGE}/data/task2_run_${RUN_ID}.csv"
BAG_FILE="${PACKAGE}/data/task2_run_${RUN_ID}.bag"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed on the host." >&2
  exit 1
fi

if ! command -v gnome-terminal >/dev/null 2>&1; then
  echo "gnome-terminal is not installed on the host." >&2
  exit 1
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)" != "true" ]]; then
  echo "ROS container '${CONTAINER}' is not running." >&2
  echo "Start the container first, or set TASK2_CONTAINER to its name." >&2
  exit 1
fi

if docker exec "${CONTAINER}" bash -lc \
  "pgrep -x px4 >/dev/null || pgrep -x gzserver >/dev/null || pgrep -x mavros_node >/dev/null"; then
  echo "PX4, Gazebo, or MAVROS is already running in '${CONTAINER}'." >&2
  echo "Stop the old run before starting a new one." >&2
  exit 1
fi

docker exec "${CONTAINER}" mkdir -p "${PACKAGE}/data"

SCREEN_SIZE="$(
  xrandr --current 2>/dev/null |
    awk '/\*/ {print $1; exit}' || true
)"
SCREEN_SIZE="${TASK2_SCREEN_SIZE:-${SCREEN_SIZE:-1920x1080}}"
SCREEN_WIDTH="${SCREEN_SIZE%x*}"
SCREEN_HEIGHT="${SCREEN_SIZE#*x}"
RIGHT_X=$((SCREEN_WIDTH / 2 + 10))
BOTTOM_Y=$((SCREEN_HEIGHT / 2 + 10))

open_host_terminal() {
  local title="$1"
  local command="$2"
  local x="$3"
  local y="$4"

  gnome-terminal --window --title="${title}" \
    --geometry="68x18+${x}+${y}" -- \
    bash -lc "docker exec -it ${CONTAINER@Q} bash -lc ${command@Q}; exec bash"
}

echo "Task 2 run ID: ${RUN_ID}"
echo "CSV: ${CSV_FILE}"
echo "bag: ${BAG_FILE}"

open_host_terminal "1 PX4 + Gazebo" \
  "cd ${WORKSPACE}; source /opt/ros/noetic/setup.bash; ${PACKAGE}/scripts/start_task2_sim.sh" \
  10 40

open_host_terminal "2 MAVROS" \
  "source /opt/ros/noetic/setup.bash; export ROS_PACKAGE_PATH=${WORKSPACE}/src:\${ROS_PACKAGE_PATH}; sleep 10; roslaunch week3_gazebo_task2 task2_mavros.launch" \
  "${RIGHT_X}" 40

open_host_terminal "3 rosbag + CSV" \
  "source /opt/ros/noetic/setup.bash; export ROS_PACKAGE_PATH=${WORKSPACE}/src:\${ROS_PACKAGE_PATH}; sleep 15; roslaunch week3_gazebo_task2 task2_record.launch csv_file:=${CSV_FILE} bag_file:=${BAG_FILE}" \
  10 "${BOTTOM_Y}"

open_host_terminal "4 Task 2 Flight Control" \
  "source /opt/ros/noetic/setup.bash; export ROS_PACKAGE_PATH=${WORKSPACE}/src:\${ROS_PACKAGE_PATH}; sleep 22; roslaunch week3_gazebo_task2 task2_mission.launch start_mavros:=false" \
  "${RIGHT_X}" "${BOTTOM_Y}"

echo "Four host terminals opened."
echo "After landing, press Ctrl+C in terminal 3 to finalize rosbag."
