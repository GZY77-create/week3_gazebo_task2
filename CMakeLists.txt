cmake_minimum_required(VERSION 3.0.2)
project(week3_gazebo_task2)

find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  mavros_msgs
  rospy
  sensor_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/task2_mission.py
  scripts/task2_logger.py
  scripts/plot_flight.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(PROGRAMS
  scripts/start_task2_sim.sh
  scripts/start_task2_all.sh
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch worlds
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
