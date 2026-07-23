# Week 3 Task 2：Gazebo 绕障飞行

基于 ROS Noetic、PX4 SITL、Gazebo Classic 和 MAVROS，实现自动起飞、绕障、到达目标点、返航降落，并使用 rosbag/CSV 记录飞行数据。

![最终轨迹分析](plots/task2_final_analysis.png)

## 1. 完成内容

- 自定义 Gazebo world：蓝色起降点、红色圆柱、绿色目标点、黄色禁飞区
- Iris 自动起飞至 2.5 m，绕过障碍和禁飞区后返航降落
- 记录位置、高度、速度、姿态和飞控状态
- 绘制并标注起点、航点、终点和最大误差
- 飞行高度、绕障和到点误差满足挑战规则

## 2. 环境准备

已验证环境：

- Ubuntu 20.04
- ROS Noetic
- PX4-Autopilot v1.14
- Gazebo Classic 11
- MAVROS
- Python 3、NumPy、Matplotlib

安装本包依赖：

```bash
sudo apt update
sudo apt install ros-noetic-mavros ros-noetic-mavros-extras \
  ros-noetic-gazebo-ros ros-noetic-plotjuggler-ros \
  python3-numpy python3-matplotlib
sudo /opt/ros/noetic/lib/mavros/install_geographiclib_datasets.sh
```

本项目默认 PX4 源码位于 `~/PX4-Autopilot`。没有 PX4 v1.14 时：

```bash
cd ~
git clone --branch v1.14.0 --recursive \
  https://github.com/PX4/PX4-Autopilot.git
bash ~/PX4-Autopilot/Tools/setup/ubuntu.sh
```

安装脚本结束后重启电脑。

## 3. 下载与编译

```bash
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
git clone https://github.com/GZY77-create/week3_gazebo_task2.git
cd ~/catkin_ws
catkin_make --pkg week3_gazebo_task2
source devel/setup.bash
```

主要目录：

```text
launch/   ROS 启动文件        scripts/  飞行、记录和绘图脚本
worlds/   Gazebo 场景         data/     CSV 与 rosbag
images/   验收截图            plots/    轨迹分析图
videos/   验收录屏
```

## 4. 启动仿真

启动前确认没有旧实例：

```bash
pgrep -a px4
pgrep -a gzserver
pgrep -a mavros_node
```

如果命令没有输出，依次打开四个终端。

### 终端 1：PX4 与 Gazebo

```bash
cd ~/catkin_ws
PX4_DIR="$HOME/PX4-Autopilot" \
  ./src/week3_gazebo_task2/scripts/start_task2_sim.sh
```

等待 Gazebo 中出现 Iris 和四类场景标记。

### 终端 2：MAVROS

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch week3_gazebo_task2 task2_mavros.launch
```

确认连接：

```bash
rostopic echo -n 1 /mavros/state
```

输出应包含 `connected: True`。

### 终端 3：记录数据

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
RUN_ID="$(date +%Y%m%d_%H%M%S)"
roslaunch week3_gazebo_task2 task2_record.launch \
  csv_file:="$HOME/catkin_ws/src/week3_gazebo_task2/data/task2_${RUN_ID}.csv" \
  bag_file:="$HOME/catkin_ws/src/week3_gazebo_task2/data/task2_${RUN_ID}.bag"
```

### 终端 4：执行任务

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch week3_gazebo_task2 task2_mission.launch start_mavros:=false
```

成功时终端显示：

```text
TASK2_COMPLETE: target reached, returned, landed
Armed state confirmed: False
```

降落后先在终端 3 按 `Ctrl+C`，等待 rosbag 正常结束，再关闭其他终端。

## 5. 任务说明

MAVROS 使用 ENU 坐标系：x 向东、y 向北、z 向上。航线依次经过青色航点、红柱南侧、紫红色航点、绿色目标点和禁飞区外围，最后返回起点并执行 `AUTO.LAND`。

安全规则：

- 未连接飞控时禁止解锁
- 先连续发送 setpoint，再切换 OFFBOARD 并解锁
- 巡航高度 2.5 m，不低于 1 m
- 航点容差 0.35 m，小于任务要求的 0.5 m
- 失去连接、退出 OFFBOARD 或航点超时时请求降落
- 检测接地后解除武装

## 6. 数据记录与可视化

最终验收数据：

- [`data/task2_final.csv`](data/task2_final.csv)
- [`data/task2_final.bag`](data/task2_final.bag)

rosbag 关键话题：

| 话题 | 含义 |
|---|---|
| `/mavros/local_position/pose` | 本地位置与高度 |
| `/mavros/local_position/velocity_local` | 三轴速度 |
| `/mavros/imu/data` | IMU 姿态 |
| `/mavros/state` | 连接、模式和解锁状态 |

检查 rosbag：

```bash
rosbag info ~/catkin_ws/src/week3_gazebo_task2/data/task2_final.bag
```

根据 CSV 重新生成轨迹图：

```bash
cd ~/catkin_ws
./src/week3_gazebo_task2/scripts/plot_flight.py \
  --input src/week3_gazebo_task2/data/task2_final.csv \
  --output src/week3_gazebo_task2/plots/task2_final_analysis.png
```

使用 PlotJuggler 打开最终 rosbag：

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch week3_gazebo_task2 task2_plotjuggler.launch
```

![PlotJuggler 位置曲线](images/task2_plotjuggler_position.png)

## 7. 验收结果

| 指标 | 结果 | 判定 |
|---|---:|---|
| 禁飞区内空中采样点 | 0 | 通过 |
| 圆柱最小净空 | 1.13 m | 通过 |
| 目标点最近距离 | 0.021 m | 通过 |
| 最大横向航迹误差 | 0.50 m | 转弯瞬态 |
| 最终返航 XY 误差 | 0.12 m | 通过 |

![Gazebo 场景](images/task2_gazebo_overview.jpg)

![任务完成并解除武装](images/task2_complete.jpg)

验收录屏：[videos/task2_demo.mp4](videos/task2_demo.mp4)

## 8. 常见问题

### 提示 PX4 或 Gazebo 已运行

说明上一次仿真没有退出。关闭旧 PX4、Gazebo 和 MAVROS 后重新启动，不要同时运行两套仿真。

### MAVROS 显示 `connected: False`

先启动终端 1，等待 PX4 和 Gazebo 完全启动，再运行 MAVROS。默认连接地址为 `udp://:14540@127.0.0.1:14580`。

### 提示 rosbag 文件已存在

rosbag 不覆盖已有文件。按本文使用带时间的 `RUN_ID`，或删除命令中的旧文件名后重新运行。

### Gazebo 没有界面

确认当前为图形桌面会话并且 `DISPLAY` 有值：

```bash
echo "$DISPLAY"
```

## 9. 验收标准对应

| 文档验收项 | 本项目内容 |
|---|---|
| 仿真复现 25 | 第 2～4 节环境、world、模型与启动命令 |
| 飞行任务 25 | 自动起飞、绕障、目标点、返航降落及录屏 |
| 数据记录 20 | rosbag、CSV 和关键话题说明 |
| 结果分析 15 | 轨迹图、PlotJuggler 图和误差表 |
| 工程表达 15 | ROS package、截图、命令和排错记录 |
