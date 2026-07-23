#!/usr/bin/env python3
"""Record Task 2 pose, velocity, attitude, and flight state to CSV."""

import csv
import math
import os
import threading

import rospy
import rospkg
from geometry_msgs.msg import PoseStamped, TwistStamped
from mavros_msgs.msg import State
from sensor_msgs.msg import Imu


class Task2Logger:
    FIELDS = [
        "time_s", "x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps",
        "qx", "qy", "qz", "qw", "roll_deg", "pitch_deg", "yaw_deg",
        "mode", "armed",
    ]

    def __init__(self):
        default_path = os.path.join(
            rospkg.RosPack().get_path("week3_gazebo_task2"),
            "data", "task2_flight.csv",
        )
        self.output_file = os.path.abspath(
            os.path.expanduser(rospy.get_param("~output_file", default_path))
        )
        self.sample_hz = float(rospy.get_param("~sample_hz", 20.0))
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        self.lock = threading.Lock()
        self.pose = None
        self.velocity = None
        self.imu = None
        self.state = State()
        self.start_time = None
        self.rows = 0

        rospy.Subscriber("/mavros/local_position/pose", PoseStamped,
                         self.pose_cb, queue_size=30)
        rospy.Subscriber("/mavros/local_position/velocity_local", TwistStamped,
                         self.velocity_cb, queue_size=30)
        rospy.Subscriber("/mavros/imu/data", Imu, self.imu_cb, queue_size=30)
        rospy.Subscriber("/mavros/state", State, self.state_cb, queue_size=10)

    def pose_cb(self, msg):
        with self.lock:
            self.pose = msg

    def velocity_cb(self, msg):
        with self.lock:
            self.velocity = msg

    def imu_cb(self, msg):
        with self.lock:
            self.imu = msg

    def state_cb(self, msg):
        with self.lock:
            self.state = msg

    @staticmethod
    def euler_degrees(q):
        sinr = 2.0 * (q.w * q.x + q.y * q.z)
        cosr = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        roll = math.atan2(sinr, cosr)
        sinp = 2.0 * (q.w * q.y - q.z * q.x)
        pitch = math.copysign(math.pi / 2.0, sinp) if abs(sinp) >= 1 else math.asin(sinp)
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny, cosy)
        return tuple(math.degrees(value) for value in (roll, pitch, yaw))

    def run(self):
        rospy.loginfo("Task 2 CSV output: %s", self.output_file)
        with open(self.output_file, "w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.FIELDS)
            writer.writeheader()
            rate = rospy.Rate(self.sample_hz)
            while not rospy.is_shutdown():
                with self.lock:
                    pose, velocity, imu, state = (
                        self.pose, self.velocity, self.imu, self.state
                    )
                if pose is None or velocity is None or imu is None:
                    rospy.loginfo_throttle(2.0, "Logger waiting for MAVROS data")
                    rate.sleep()
                    continue
                stamp = pose.header.stamp
                if self.start_time is None:
                    self.start_time = stamp
                p = pose.pose.position
                v = velocity.twist.linear
                q = imu.orientation
                roll, pitch, yaw = self.euler_degrees(q)
                writer.writerow({
                    "time_s": "{:.3f}".format((stamp - self.start_time).to_sec()),
                    "x_m": "{:.4f}".format(p.x), "y_m": "{:.4f}".format(p.y),
                    "z_m": "{:.4f}".format(p.z), "vx_mps": "{:.4f}".format(v.x),
                    "vy_mps": "{:.4f}".format(v.y), "vz_mps": "{:.4f}".format(v.z),
                    "qx": "{:.6f}".format(q.x), "qy": "{:.6f}".format(q.y),
                    "qz": "{:.6f}".format(q.z), "qw": "{:.6f}".format(q.w),
                    "roll_deg": "{:.3f}".format(roll),
                    "pitch_deg": "{:.3f}".format(pitch),
                    "yaw_deg": "{:.3f}".format(yaw),
                    "mode": state.mode, "armed": int(state.armed),
                })
                self.rows += 1
                if self.rows % int(max(1.0, self.sample_hz)) == 0:
                    stream.flush()
                rate.sleep()


if __name__ == "__main__":
    rospy.init_node("task2_logger")
    Task2Logger().run()
