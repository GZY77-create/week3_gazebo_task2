# Week 3 Task 2：Gazebo 绕障飞行

基于 ROS Noetic、PX4 SITL、Gazebo Classic 和 MAVROS，实现自动起飞、绕障、到达目标点、返航降落，并使用 rosbag/CSV 记录和分析飞行数据。

![最终轨迹、高度与速度分析](plots/task2_final_analysis.png)

## 完成内容

- 自定义 Gazebo world：蓝色起降点、红色圆柱、绿色目标点、黄色禁飞区
- Iris 自动起飞至相对高度 2.5 m，绕障后到达目标点并返航降落
- 记录位置、高度、速度、姿态和飞控状态
- 轨迹图标注起点、航点、终点和最大横向误差
- 挑战规则：巡航高度不低于 1 m、必须绕障、航点容差 0.35 m

![Gazebo 自定义场景](images/task2_gazebo_overview.jpg)

## 复现环境

已验证的软件组合：

- Ubuntu 20.04
- ROS Noetic
- PX4-Autopilot v1.14
- Gazebo Classic 11
- MAVROS
- Python 3、NumPy、Matplotlib

先确认基础环境：

```bash
test -f /opt/ros/noetic/setup.bash
test -f "$HOME/PX4-Autopilot/Makefile"
gazebo --version
source /opt/ros/noetic/setup.bash
rospack find mavros
```

安装本包依赖：

```bash
sudo apt update
sudo apt install ros-noetic-mavros ros-noetic-mavros-extras \
  ros-noetic-gazebo-ros ros-noetic-plotjuggler-ros \
  python3-numpy python3-matplotlib
sudo /opt/ros/noetic/lib/mavros/install_geographiclib_datasets.sh
```

如果没有 PX4 v1.14：

```bash
cd ~
git clone --branch v1.14.0 --recursive \
  https://github.com/PX4/PX4-Autopilot.git
bash ~/PX4-Autopilot/Tools/setup/ubuntu.sh
```

安装完成后重启电脑。以下步骤默认 PX4 位于 `~/PX4-Autopilot`，catkin 工作空间位于 `~/catkin_ws`。

## 宿主机从零复现（无需 Docker，推荐）

### 1. 克隆并编译

```bash
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/src
git clone https://github.com/GZY77-create/week3_gazebo_task2.git
cd ~/catkin_ws
catkin_make --pkg week3_gazebo_task2
source devel/setup.bash
```

### 2. 启动 PX4 SITL 和 Gazebo

打开终端 1：

```bash
cd ~/catkin_ws
PX4_DIR="$HOME/PX4-Autopilot" \
  ./src/week3_gazebo_task2/scripts/start_task2_sim.sh
```

等待 Gazebo 出现 Iris、蓝色起降点、红色圆柱、绿色目标点和黄色禁飞区，并等待 PX4 显示 `Ready for takeoff!`。

### 3. 启动 MAVROS

打开终端 2：

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch week3_gazebo_task2 task2_mavros.launch
```

出现 `Got HEARTBEAT, connected` 后，可在新终端确认：

```bash
source /opt/ros/noetic/setup.bash
rostopic echo -n 1 /mavros/state
```

输出中的 `connected` 应为 `True`。

### 4. 记录 rosbag 和 CSV

打开终端 3：

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
RUN_ID="$(date +%Y%m%d_%H%M%S)"
roslaunch week3_gazebo_task2 task2_record.launch \
  csv_file:="$HOME/catkin_ws/src/week3_gazebo_task2/data/task2_${RUN_ID}.csv" \
  bag_file:="$HOME/catkin_ws/src/week3_gazebo_task2/data/task2_${RUN_ID}.bag"
```

### 5. 执行飞行任务

打开终端 4：

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch week3_gazebo_task2 task2_mission.launch start_mavros:=false
```

正常日志依次包含各航点，最后显示：

```text
TASK2_COMPLETE: target reached, returned, landed
Armed state confirmed: False
```

### 6. 验收和正常关闭

可在额外终端检查：

```bash
rostopic hz /mavros/setpoint_position/local
rostopic echo /mavros/state
rostopic echo /mavros/local_position/pose
```

降落后先在终端 3 按 `Ctrl+C`，等待 rosbag 正常建立索引；再关闭任务和 MAVROS，最后在 PX4 控制台输入 `shutdown`。

## Docker 一键复现（可选）

此方式适用于已有 ROS Noetic 容器，并且容器内已安装 PX4 v1.14、Gazebo、MAVROS 和本项目依赖的电脑。容器需要：

- 名称为 `ros-noetic`，或通过 `TASK2_CONTAINER` 指定
- 宿主机工作空间挂载到容器 `/root/catkin_ws`
- 使用 host 网络
- 挂载 `/tmp/.X11-unix` 并传入 `DISPLAY`

首次创建容器时可参考：

```bash
cd ~/ros-noetic-workspace
xhost +si:localuser:root
docker run -it --name ros-noetic \
  --network host --ipc host \
  -e DISPLAY="$DISPLAY" -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$PWD":/root/catkin_ws:rw \
  <已安装ROS与PX4的镜像> bash
```

仓库不提供大型 Docker 镜像，因此 `<已安装ROS与PX4的镜像>` 需要替换为本机镜像名。

容器已存在时，在宿主机执行：

```bash
docker start ros-noetic
xhost +si:localuser:root
cd ~/ros-noetic-workspace/src/week3_gazebo_task2
./scripts/start_task2_host.sh
```

容器名不是 `ros-noetic` 时：

```bash
TASK2_CONTAINER=实际容器名 ./scripts/start_task2_host.sh
```

脚本会在宿主机自动排列四个终端：

1. PX4 SITL 与 Gazebo
2. MAVROS
3. rosbag 与 CSV 记录
4. 飞行控制节点

每次数据保存为 `data/task2_run_时间.csv/.bag`。飞机降落后仍需在第 3 个终端按 `Ctrl+C`。

## 飞行流程与任务规则

MAVROS 使用 ENU 坐标系：x 向东、y 向北、z 向上。

```text
起飞点
  → 青色航点
  → 红柱南侧入口与出口
  → 紫红色航点
  → 绿色目标点
  → 禁飞区右上、左上和左下
  → 起飞点
  → AUTO.LAND
```

控制与安全逻辑：

1. 等待 FCU 连接和有效本地位置，未连接时禁止解锁。
2. 以 20 Hz 预发送 setpoint 5 秒，再请求 `OFFBOARD` 和解锁。
3. 巡航高度为相对起点 2.5 m，巡航航点不低于 1 m。
4. 航点容差为 0.35 m，同时要求速度低于 0.30 m/s。
5. 失去连接、退出 OFFBOARD 或航点超时时中止并请求 `AUTO.LAND`。
6. 检测接地后才解除武装。

## 数据记录

最终验收文件：

- [`data/task2_final.csv`](data/task2_final.csv)
- [`data/task2_final.bag`](data/task2_final.bag)

| 话题 | 类型 | 含义 |
|---|---|---|
| `/mavros/local_position/pose` | `geometry_msgs/PoseStamped` | ENU 本地位置与高度 |
| `/mavros/local_position/velocity_local` | `geometry_msgs/TwistStamped` | 本地三轴速度 |
| `/mavros/imu/data` | `sensor_msgs/Imu` | 姿态四元数和 IMU 数据 |
| `/mavros/state` | `mavros_msgs/State` | FCU 连接、模式和解锁状态 |

检查记录：

```bash
rosbag info ~/catkin_ws/src/week3_gazebo_task2/data/task2_final.bag
head ~/catkin_ws/src/week3_gazebo_task2/data/task2_final.csv
```

最终 rosbag 共 8567 条消息，包含以上四类关键话题；CSV 共 1546 条记录，覆盖 77.22 s。

## 轨迹和高度变化图

根据 CSV 重新生成分析图：

```bash
cd ~/catkin_ws
./src/week3_gazebo_task2/scripts/plot_flight.py \
  --input src/week3_gazebo_task2/data/task2_final.csv \
  --output src/week3_gazebo_task2/plots/task2_final_analysis.png
```

分析图包含：

- XY 实际轨迹与规划航线
- 起点、各航点、终点和最大误差位置
- 高度随时间变化
- 三维速度随时间变化
- 红色圆柱和黄色禁飞区位置

使用 PlotJuggler 查看 rosbag：

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
roslaunch week3_gazebo_task2 task2_plotjuggler.launch
```

![PlotJuggler 中的 x、y、z 位置曲线](images/task2_plotjuggler_position.png)

## 结果分析

分析范围为 `armed=True` 且本地高度 `z>0.5 m` 的空中样本，共 936 条，持续 46.74 s。

| 指标 | 结果 | 解释 |
|---|---:|---|
| 禁飞区内空中采样点 | 0 | 实际轨迹没有进入黄色区域 |
| 圆柱最小净空 | 1.13 m | 已扣除圆柱 0.75 m 半径，具有明显安全余量 |
| 绿色目标点最近距离 | 0.021 m | 小于 0.35 m 航点容差 |
| 最大横向航迹误差 | 0.50 m | 出现在航段转弯处，为短时惯性偏离 |
| 95% 横向航迹误差 | 0.43 m | 95% 空中样本误差不超过该值 |
| 平均横向航迹误差 | 0.12 m | 大部分时间贴近规划航线 |
| 平均空中高度 | 2.39 m | 接近相对起点 2.5 m 的巡航设定 |
| 最大空中高度 | 2.70 m | 无持续高度发散 |
| 平均三维速度 | 0.97 m/s | 航线执行平稳 |
| 最大三维速度 | 4.18 m/s | 出现在航段切换加速过程 |
| 最终返航 XY 误差 | 0.12 m | 小于 0.35 m 航点容差 |

### 误差与异常解释

- **最大横向误差 0.50 m：** 出现在航点切换的急转弯处。飞行器存在惯性，位置控制器不能瞬间改变速度方向，因此实际轨迹短时偏离规划折线；平均误差只有 0.12 m，说明不是持续跟踪发散。
- **高度低于 1 m：** 只出现在起飞和自动降落阶段，挑战规则约束的是巡航阶段。巡航航点均为相对起点 2.5 m。
- **平均高度为 2.39 m：** PX4 EKF 建立本地原点时会产生少量 z 偏移，控制节点使用启动时实际高度作为基准，因此图中的绝对 local z 与相对巡航高度存在小差异。
- **速度峰值 4.18 m/s：** 出现在较长航段或航点切换加速阶段，随后速度正常回落，没有伴随持续位置误差或高度发散。
- **禁飞区采样点为 0：** 绿色目标点后先经过右上绕行点，再飞向禁飞区上方和左侧，避免直线切过黄色区域。

最终飞行完成起飞、绕障、目标点、返航和自动降落，结束状态为 `armed=False`。

![任务完成并解除武装](images/task2_complete.jpg)

## 实际排错记录

### 1. 重复启动 PX4、Gazebo 或 MAVROS

**现象：**

```text
PX4, Gazebo, or MAVROS is already running
PX4 server already running for instance 0
```

**原因：** 上一轮仿真进程未完全退出，再次启动会发生端口和实例冲突。

**解决：** 确认飞机已经接地且 `armed: False`，正常关闭旧终端；Docker 环境可重启容器后只运行一次启动脚本：

```bash
docker restart ros-noetic
./scripts/start_task2_host.sh
```

### 2. MAVROS 一直显示 `connected: False`

**原因：** PX4 尚未启动完成，或 MAVROS 使用的 UDP 地址不正确。

**检查：**

```bash
rostopic echo -n 1 /mavros/state
```

**解决：** 先等待 PX4 显示 `Ready for takeoff!`，再启动 MAVROS。本项目默认地址为 `udp://:14540@127.0.0.1:14580`。

### 3. rosbag 文件打不开或没有索引

**原因：** 录制终端被直接关闭，`.bag.active` 没有正常结束；或者重复使用了已有文件名。

**解决：** 飞机降落后在记录终端按 `Ctrl+C`。已有未完成文件时：

```bash
rosbag reindex 文件名.bag.active
```

每次运行使用 README 中带时间戳的文件名，避免覆盖。

### 4. Gazebo 有服务但没有窗口

**原因：** Docker 容器没有获得宿主机 X11 权限。

**解决：**

```bash
xhost +si:localuser:root
echo "$DISPLAY"
```

容器需要挂载 `/tmp/.X11-unix` 并传入相同的 `DISPLAY`。

### 5. `PositionTargetGlobal failed because no origin`

这是 MAVROS 全局位置插件缺少全球原点的警告。本任务只使用 `/mavros/local_position/*` 和本地位置 setpoint，不影响 ENU 局部航线执行。

### 6. `Time jump detected. Resetting time synchroniser`

Gazebo 启动或仿真时间重置时，MAVROS 会重新同步时间。若随后 `/mavros/state` 为 `connected: True` 且位置话题持续更新，该提示不影响任务；若连接中断，应停止旧仿真并重新按顺序启动。

## 验收材料

- 轨迹分析图：[`plots/task2_final_analysis.png`](plots/task2_final_analysis.png)
- PlotJuggler 截图：[`images/task2_plotjuggler_position.png`](images/task2_plotjuggler_position.png)
- Gazebo 截图：[`images/task2_gazebo_overview.jpg`](images/task2_gazebo_overview.jpg)
- 完成状态截图：[`images/task2_complete.jpg`](images/task2_complete.jpg)
- 完整录屏：[`videos/task2_demo.mp4`](videos/task2_demo.mp4)

| 验收项 | 对应内容 |
|---|---|
| 仿真复现 25 | 无 Docker 和 Docker 两套环境与启动步骤 |
| 飞行任务 25 | 自动起飞、绕障、目标点、返航降落及录屏 |
| 数据记录 20 | rosbag、CSV、关键话题和检查命令 |
| 结果分析 15 | 轨迹/高度/速度图及误差与异常解释 |
| 工程表达 15 | ROS package、截图、命令和实际排错记录 |
