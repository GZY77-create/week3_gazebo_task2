FROM ros:noetic-ros-base-focal

ARG DEBIAN_FRONTEND=noninteractive
ARG PX4_TAG=v1.14.0

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    gazebo11 \
    libgazebo11-dev \
    python3-catkin-tools \
    python3-matplotlib \
    python3-numpy \
    python3-pip \
    python3-rospkg \
    ros-noetic-gazebo-ros \
    ros-noetic-gazebo-ros-pkgs \
    ros-noetic-mavros \
    ros-noetic-mavros-extras \
    ros-noetic-plotjuggler-ros \
    xterm \
    && rm -rf /var/lib/apt/lists/*

RUN /opt/ros/noetic/lib/mavros/install_geographiclib_datasets.sh

RUN git clone --branch "${PX4_TAG}" --depth 1 \
      https://github.com/PX4/PX4-Autopilot.git /root/PX4-Autopilot \
    && cd /root/PX4-Autopilot \
    && git submodule update --init --recursive \
    && bash Tools/setup/ubuntu.sh --no-nuttx

RUN mkdir -p /root/catkin_ws/src
COPY . /root/catkin_ws/src/week3_gazebo_task2
RUN source /opt/ros/noetic/setup.bash \
    && cd /root/catkin_ws \
    && catkin_make --pkg week3_gazebo_task2

COPY docker/entrypoint.sh /ros_entrypoint_task2.sh
RUN chmod +x /ros_entrypoint_task2.sh

WORKDIR /root/catkin_ws
ENTRYPOINT ["/ros_entrypoint_task2.sh"]
CMD ["bash"]
