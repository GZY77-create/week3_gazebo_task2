# Week 3 Task 2：Gazebo 绕障飞行

基于 ROS Noetic、PX4 SITL、Gazebo Classic 和 MAVROS，实现自动起飞、绕障、到达目标点、返航降落，并记录 rosbag/CSV。

![最终轨迹分析](plots/task2_final_analysis.png)

## 功能

- 自定义 Gazebo 场景和可拖动航点
- 自动执行 OFFBOARD 航线并避开圆柱和黄色禁飞区
- 自动返航、降落并解除武装
- 记录位置、速度、姿态和飞控状态
- 生成带起点、航点、终点和最大误差的轨迹图

## 环境

- Ubuntu 20.04
- ROS Noetic
- PX4-Autopilot v1.14
- Gazebo Classic 11
- MAVROS
- Python 3、NumPy、Matplotlib

安装 ROS 依赖：

```bash
sudo apt-get install ros-noetic-mavros ros-noetic-mavros-extras \
  ros-noetic-gazebo-ros python3-matplotlib python3-numpy
sudo /opt/ros/noetic/lib/mavros/install_geographiclib_datasets.sh
```

## 宿主机复现

默认 PX4 位于 `~/PX4-Autopilot`。

```bash
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
git clone https://github.com/GZY77-create/week3_gazebo_task2.git
cd ..
catkin_make --pkg week3_gazebo_task2
source devel/setup.bash
```

依次打开四个终端。

终端 1：启动 PX4 和 Gazebo：

```bash
cd ~/catkin_ws
PX4_DIR="$HOME/PX4-Autopilot" \
  ./src/week3_gazebo_task2/scripts/start_task2_sim.sh
```

终端 2：启动 MAVROS：

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch week3_gazebo_task2 task2_mavros.launch
```

终端 3：记录数据：

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
RUN_ID="$(date +%Y%m%d_%H%M%S)"
roslaunch week3_gazebo_task2 task2_record.launch \
  csv_file:="$HOME/catkin_ws/src/week3_gazebo_task2/data/task2_${RUN_ID}.csv" \
  bag_file:="$HOME/catkin_ws/src/week3_gazebo_task2/data/task2_${RUN_ID}.bag"
```

终端 4：执行飞行任务：

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch week3_gazebo_task2 task2_mission.launch start_mavros:=false
```

看到以下日志表示任务完成：

```text
TASK2_COMPLETE: target reached, returned, landed
Armed state confirmed: False
```

飞机降落后先在记录终端按 `Ctrl+C`，确保 rosbag 正常保存。

## Docker 一键启动（可选）

已有名为 `ros-noetic` 的容器时，在宿主机运行：

```bash
cd ~/ros-noetic-workspace/src/week3_gazebo_task2
./scripts/start_task2_host.sh
```

容器名称不同时：

```bash
TASK2_CONTAINER=容器名 ./scripts/start_task2_host.sh
```

## 数据与可视化

最终数据：

- [`data/task2_final.csv`](data/task2_final.csv)
- [`data/task2_final.bag`](data/task2_final.bag)

rosbag 包含以下关键话题：

| 话题 | 含义 |
|---|---|
| `/mavros/local_position/pose` | 位置和高度 |
| `/mavros/local_position/velocity_local` | 三轴速度 |
| `/mavros/imu/data` | 姿态 |
| `/mavros/state` | 连接、模式和解锁状态 |

生成轨迹图：

```bash
cd ~/catkin_ws
./src/week3_gazebo_task2/scripts/plot_flight.py
```

使用 PlotJuggler 查看 rosbag：

```bash
sudo apt-get install ros-noetic-plotjuggler-ros
roslaunch week3_gazebo_task2 task2_plotjuggler.launch
```

![PlotJuggler 位置曲线](images/task2_plotjuggler_position.png)

## 验收结果

| 指标 | 结果 |
|---|---:|
| 禁飞区内空中采样点 | 0 |
| 圆柱最小净空 | 1.13 m |
| 目标点最近距离 | 0.021 m |
| 最大横向航迹误差 | 0.50 m |
| 最终返航 XY 误差 | 0.12 m |

![Gazebo 场景](images/task2_gazebo_overview.jpg)

![任务完成并解除武装](images/task2_complete.jpg)

验收录屏：[videos/task2_demo.mp4](videos/task2_demo.mp4)
