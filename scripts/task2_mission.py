#!/usr/bin/env python3
"""Independent MAVROS Offboard mission for Week 3 Task 2."""

import math
import subprocess
import threading

import rospy
from geometry_msgs.msg import PoseStamped, TwistStamped
from mavros_msgs.msg import ExtendedState, State
from mavros_msgs.srv import CommandBool, SetMode


class MissionError(RuntimeError):
    pass


class Task2Mission:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = State()
        self.extended = ExtendedState()
        self.pose = None
        self.velocity = None
        self.goal = PoseStamped()
        self.goal.header.frame_id = "map"
        self.goal.pose.orientation.w = 1.0

        self.rate_hz = float(rospy.get_param("~rate", 20.0))
        self.cruise_height = float(rospy.get_param("~cruise_height", 2.5))
        self.minimum_height = float(rospy.get_param("~minimum_height", 1.0))
        self.tolerance = float(rospy.get_param("~position_tolerance", 0.35))
        self.speed_tolerance = float(rospy.get_param("~speed_tolerance", 0.30))
        self.timeout = float(rospy.get_param("~waypoint_timeout", 35.0))
        self.hold_seconds = float(rospy.get_param("~hold_seconds", 0.5))
        self.use_gazebo_waypoints = bool(rospy.get_param("~use_gazebo_waypoints", True))
        self.gazebo_world = rospy.get_param("~gazebo_world", "task2_landmarks")
        self.spawn_offset_x = float(rospy.get_param("~spawn_offset_x", 1.01))
        self.spawn_offset_y = float(rospy.get_param("~spawn_offset_y", 0.98))
        if self.cruise_height < self.minimum_height:
            raise MissionError("cruise_height must be >= minimum_height")

        rospy.Subscriber("/mavros/state", State, self.state_cb, queue_size=10)
        rospy.Subscriber("/mavros/extended_state", ExtendedState,
                         self.extended_cb, queue_size=10)
        rospy.Subscriber("/mavros/local_position/pose", PoseStamped,
                         self.pose_cb, queue_size=20)
        rospy.Subscriber("/mavros/local_position/velocity_local", TwistStamped,
                         self.velocity_cb, queue_size=20)
        self.publisher = rospy.Publisher(
            "/mavros/setpoint_position/local", PoseStamped, queue_size=20)

        rospy.wait_for_service("/mavros/cmd/arming", timeout=20.0)
        rospy.wait_for_service("/mavros/set_mode", timeout=20.0)
        self.arm_service = rospy.ServiceProxy(
            "/mavros/cmd/arming", CommandBool)
        self.mode_service = rospy.ServiceProxy(
            "/mavros/set_mode", SetMode)

    def state_cb(self, msg):
        with self.lock:
            self.state = msg

    def extended_cb(self, msg):
        with self.lock:
            self.extended = msg

    def pose_cb(self, msg):
        with self.lock:
            self.pose = msg

    def velocity_cb(self, msg):
        with self.lock:
            self.velocity = msg

    def snapshot(self):
        with self.lock:
            return self.state, self.extended, self.pose, self.velocity

    def set_goal(self, x, y, z):
        self.goal.pose.position.x = x
        self.goal.pose.position.y = y
        self.goal.pose.position.z = z

    def publish_goal(self):
        self.goal.header.stamp = rospy.Time.now()
        self.publisher.publish(self.goal)

    @staticmethod
    def distance(pose, x, y, z):
        p = pose.pose.position
        return math.sqrt((p.x - x) ** 2 + (p.y - y) ** 2 + (p.z - z) ** 2)

    @staticmethod
    def speed(velocity):
        v = velocity.twist.linear
        return math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2)

    def wait_for_vehicle(self):
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown():
            state, _, pose, velocity = self.snapshot()
            if state.connected and pose is not None and velocity is not None:
                return pose
            rospy.loginfo_throttle(2.0, "Waiting for Task 2 FCU and local pose")
            rate.sleep()
        raise MissionError("ROS stopped before vehicle connection")

    def stream(self, seconds):
        end = rospy.Time.now() + rospy.Duration(seconds)
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown() and rospy.Time.now() < end:
            self.publish_goal()
            rate.sleep()

    def set_mode(self, mode, timeout=30.0):
        end = rospy.Time.now() + rospy.Duration(timeout)
        last_request = rospy.Time(0)
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown() and rospy.Time.now() < end:
            state, _, _, _ = self.snapshot()
            if not state.connected:
                raise MissionError("FCU disconnected during mode request")
            if state.mode == mode:
                rospy.loginfo("Mode confirmed: %s", mode)
                return
            if (rospy.Time.now() - last_request).to_sec() >= 2.0:
                try:
                    result = self.mode_service(base_mode=0, custom_mode=mode)
                    rospy.loginfo("Requested %s: sent=%s", mode, result.mode_sent)
                except rospy.ServiceException as exc:
                    rospy.logwarn("Mode request failed, retrying: %s", exc)
                last_request = rospy.Time.now()
            self.publish_goal()
            rate.sleep()
        raise MissionError("Mode switch timed out: " + mode)

    def arm(self, requested, timeout=30.0):
        end = rospy.Time.now() + rospy.Duration(timeout)
        last_request = rospy.Time(0)
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown() and rospy.Time.now() < end:
            state, _, _, _ = self.snapshot()
            if requested and not state.connected:
                raise MissionError("Refusing to arm without FCU connection")
            if state.armed == requested:
                rospy.loginfo("Armed state confirmed: %s", requested)
                return
            if (rospy.Time.now() - last_request).to_sec() >= 2.0:
                try:
                    result = self.arm_service(value=requested)
                    rospy.loginfo("Arm request: success=%s", result.success)
                except rospy.ServiceException as exc:
                    rospy.logwarn("Arm request failed, retrying: %s", exc)
                last_request = rospy.Time.now()
            self.publish_goal()
            rate.sleep()
        raise MissionError("Arm request timed out")

    def fly_to(self, name, x, y, z, hold=0.0):
        if name not in ("takeoff", "landing_return") and z < self.minimum_height:
            raise MissionError("Waypoint violates 1 m minimum-height rule")
        self.set_goal(x, y, z)
        rospy.loginfo("Task2 target %s: (%.2f, %.2f, %.2f)", name, x, y, z)
        end = rospy.Time.now() + rospy.Duration(self.timeout)
        stable_since = None
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown() and rospy.Time.now() < end:
            state, _, pose, velocity = self.snapshot()
            if not state.connected:
                raise MissionError("FCU disconnected in flight")
            if state.mode != "OFFBOARD":
                raise MissionError("Vehicle left OFFBOARD: " + state.mode)
            if pose is None or velocity is None:
                rate.sleep()
                continue
            error = self.distance(pose, x, y, z)
            speed = self.speed(velocity)
            if error <= self.tolerance and speed <= self.speed_tolerance:
                if stable_since is None:
                    stable_since = rospy.Time.now()
                if (rospy.Time.now() - stable_since).to_sec() >= hold:
                    rospy.loginfo("Reached %s, error %.2f m", name, error)
                    return
            else:
                stable_since = None
                rospy.loginfo_throttle(1.0, "%s error %.2f m", name, error)
            self.publish_goal()
            rate.sleep()
        raise MissionError("Waypoint timeout: " + name)

    def land(self):
        self.set_mode("AUTO.LAND")
        end = rospy.Time.now() + rospy.Duration(60.0)
        rate = rospy.Rate(self.rate_hz)
        while not rospy.is_shutdown() and rospy.Time.now() < end:
            state, extended, _, _ = self.snapshot()
            if not state.armed:
                rospy.loginfo("PX4 auto-disarmed after landing")
                return
            if extended.landed_state == ExtendedState.LANDED_STATE_ON_GROUND:
                self.arm(False, timeout=15.0)
                return
            rospy.loginfo_throttle(2.0, "AUTO.LAND: waiting for touchdown")
            rate.sleep()
        raise MissionError("Landing timeout")

    def gazebo_model_xy(self, model_name):
        command = [
            "gz", "model", "-w", self.gazebo_world,
            "-m", model_name, "-p",
        ]
        try:
            output = subprocess.check_output(
                command, stderr=subprocess.STDOUT, timeout=8.0,
                universal_newlines=True).strip()
            values = output.split()
            if len(values) < 2:
                raise ValueError("unexpected pose output: " + output)
            world_x, world_y = float(values[0]), float(values[1])
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            raise MissionError(
                "Cannot read Gazebo waypoint {}: {}".format(model_name, exc))
        return world_x - self.spawn_offset_x, world_y - self.spawn_offset_y

    def visual_route(self, cruise_z):
        cyan = self.gazebo_model_xy("waypoint_1_cyan")
        magenta = self.gazebo_model_xy("waypoint_2_magenta")
        green = self.gazebo_model_xy("green_target_point")
        for name, point in (
                ("cyan", cyan), ("magenta", magenta), ("green", green)):
            rospy.loginfo(
                "Visual waypoint %-8s local=(%.2f, %.2f)",
                name, point[0], point[1])

        # Two points pass south of the red cylinder at (5,0).
        # Two more pass around the right side of the no-fly rectangle.
        return [
            ("cyan", cyan[0], cyan[1], cruise_z),
            ("red_bypass_entry", 3.5, -2.0, cruise_z),
            ("red_bypass_exit", 6.5, -2.0, cruise_z),
            ("magenta", magenta[0], magenta[1], cruise_z),
            ("green", green[0], green[1], cruise_z),
            ("nofly_upper_right", 4.2, 7.2, cruise_z),
            ("nofly_upper_left", -0.5, 7.5, cruise_z),
            ("nofly_lower_left", -0.5, 2.5, cruise_z),
        ]

    def run(self):
        initial = self.wait_for_vehicle()
        x0 = initial.pose.position.x
        y0 = initial.pose.position.y
        cruise_z = initial.pose.position.z + self.cruise_height

        if self.use_gazebo_waypoints:
            mission_route = self.visual_route(cruise_z)
        else:
            mission_route = [
                ("cyan", 2.0, -2.0, cruise_z),
                ("red_bypass_entry", 3.5, -2.0, cruise_z),
                ("red_bypass_exit", 6.5, -2.0, cruise_z),
                ("magenta", 8.0, -2.0, cruise_z),
                ("green", 8.0, 5.0, cruise_z),
                ("nofly_upper_right", 4.2, 7.2, cruise_z),
                ("nofly_upper_left", -0.5, 7.5, cruise_z),
                ("nofly_lower_left", -0.5, 2.5, cruise_z),
            ]

        self.set_goal(x0, y0, cruise_z)
        self.stream(5.0)
        self.set_mode("OFFBOARD")
        self.arm(True)
        self.fly_to("takeoff", x0, y0, cruise_z, self.hold_seconds)
        for waypoint in mission_route:
            self.fly_to(*waypoint, hold=self.hold_seconds)
        self.fly_to("landing_return", x0, y0, cruise_z, hold=2.0)
        self.land()
        rospy.loginfo("TASK2_COMPLETE: target reached, returned, landed")


def main():
    rospy.init_node("task2_mission")
    mission = None
    try:
        mission = Task2Mission()
        mission.run()
    except (MissionError, rospy.ROSException) as exc:
        rospy.logerr("TASK2_ABORTED: %s", exc)
        if mission is not None:
            try:
                state, _, _, _ = mission.snapshot()
                if state.connected and state.armed:
                    mission.set_mode("AUTO.LAND", timeout=15.0)
            except Exception as landing_exc:
                rospy.logerr("Emergency landing request failed: %s", landing_exc)


if __name__ == "__main__":
    main()
