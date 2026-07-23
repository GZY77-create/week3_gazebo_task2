#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="/root/catkin_ws"
PACKAGE="${WORKSPACE}/src/week3_gazebo_task2"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
CSV_FILE="${PACKAGE}/data/task2_run_${RUN_ID}.csv"
BAG_FILE="${PACKAGE}/data/task2_run_${RUN_ID}.bag"

if [[ -z "${DISPLAY:-}" ]]; then
  echo "DISPLAY is not set; run this command from the Ubuntu desktop terminal." >&2
  exit 1
fi

if command -v gnome-terminal >/dev/null 2>&1; then
  TERMINAL="gnome-terminal"
elif command -v xterm >/dev/null 2>&1; then
  TERMINAL="xterm"
  echo "gnome-terminal was not found; falling back to xterm." >&2
else
  echo "A terminal emulator is required (gnome-terminal or xterm)." >&2
  exit 1
fi

open_terminal() {
  local title="$1"
  local command="$2"

  if [[ "${TERMINAL}" == "gnome-terminal" ]]; then
    gnome-terminal --window --title="${title}" -- bash -lc "${command}"
  else
    xterm -hold -T "${title}" -e bash -lc "${command}"
  fi
}

if pgrep -x px4 >/dev/null || pgrep -x gzserver >/dev/null || pgrep -x mavros_node >/dev/null; then
  echo "PX4, Gazebo, or MAVROS is already running. Stop the old run first." >&2
  exit 1
fi

mkdir -p "${PACKAGE}/data"
echo "Task 2 run ID: ${RUN_ID}"
echo "CSV: ${CSV_FILE}"
echo "bag: ${BAG_FILE}"

open_terminal "1 PX4 + Gazebo" \
  "cd ${WORKSPACE}; source /opt/ros/noetic/setup.bash; ${PACKAGE}/scripts/start_task2_sim.sh; exec bash" &

open_terminal "2 MAVROS" \
  "source /opt/ros/noetic/setup.bash; export ROS_PACKAGE_PATH=${WORKSPACE}/src:\${ROS_PACKAGE_PATH}; sleep 10; roslaunch week3_gazebo_task2 task2_mavros.launch; exec bash" &

open_terminal "3 rosbag + CSV" \
  "source /opt/ros/noetic/setup.bash; export ROS_PACKAGE_PATH=${WORKSPACE}/src:\${ROS_PACKAGE_PATH}; sleep 15; roslaunch week3_gazebo_task2 task2_record.launch csv_file:=${CSV_FILE} bag_file:=${BAG_FILE}; exec bash" &

open_terminal "4 Task 2 Flight Control" \
  "source /opt/ros/noetic/setup.bash; export ROS_PACKAGE_PATH=${WORKSPACE}/src:\${ROS_PACKAGE_PATH}; sleep 22; roslaunch week3_gazebo_task2 task2_mission.launch start_mavros:=false; exec bash" &

echo "Four terminals opened. After landing, press Ctrl+C in terminal 3 to finalize rosbag."
wait
