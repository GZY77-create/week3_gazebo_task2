#!/usr/bin/env python3
"""Validate Task 2 evidence files and calculate acceptance metrics."""

import argparse
import csv
import math
import os
import subprocess
import sys


REQUIRED_FIELDS = {
    "time_s", "x_m", "y_m", "z_m",
    "vx_mps", "vy_mps", "vz_mps",
    "qx", "qy", "qz", "qw",
    "roll_deg", "pitch_deg", "yaw_deg",
    "mode", "armed",
}
REQUIRED_TOPICS = {
    "/mavros/local_position/pose",
    "/mavros/local_position/velocity_local",
    "/mavros/imu/data",
    "/mavros/state",
}
PLANNED_XY = [
    (0.0, 0.0), (2.0, 2.28358), (3.5, -2.0), (6.5, -2.0),
    (8.0, -2.0), (8.0, 5.0), (4.2, 7.2), (-0.5, 7.5),
    (-0.5, 2.5), (0.0, 0.0),
]


class Checks:
    def __init__(self):
        self.failed = 0

    def check(self, condition, label, detail=""):
        status = "PASS" if condition else "FAIL"
        suffix = ": {}".format(detail) if detail else ""
        print("[{}] {}{}".format(status, label, suffix))
        if not condition:
            self.failed += 1

    @staticmethod
    def warn(label, detail=""):
        suffix = ": {}".format(detail) if detail else ""
        print("[WARN] {}{}".format(label, suffix))


def point_segment_distance(point, start, end):
    ab_x, ab_y = end[0] - start[0], end[1] - start[1]
    denominator = ab_x * ab_x + ab_y * ab_y
    if denominator == 0.0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    t = ((point[0] - start[0]) * ab_x
         + (point[1] - start[1]) * ab_y) / denominator
    t = min(1.0, max(0.0, t))
    nearest = (start[0] + t * ab_x, start[1] + t * ab_y)
    return math.hypot(point[0] - nearest[0], point[1] - nearest[1])


def cross_track_error(point):
    return min(
        point_segment_distance(point, PLANNED_XY[index], PLANNED_XY[index + 1])
        for index in range(len(PLANNED_XY) - 1)
    )


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or [])
        rows = list(reader)
    return fields, rows


def value(row, name):
    return float(row[name])


def check_csv(path, checks):
    fields, rows = load_csv(path)
    checks.check(REQUIRED_FIELDS <= fields, "CSV fields",
                 "{} required fields present".format(len(REQUIRED_FIELDS)))
    checks.check(len(rows) >= 1000, "CSV sample count", str(len(rows)))
    if not rows or not REQUIRED_FIELDS <= fields:
        return

    duration = value(rows[-1], "time_s") - value(rows[0], "time_s")
    airborne = [
        row for row in rows
        if int(row["armed"]) == 1 and value(row, "z_m") > 0.5
    ]
    checks.check(duration >= 60.0, "Recording duration", "{:.2f} s".format(duration))
    checks.check(len(airborne) >= 500, "Airborne samples", str(len(airborne)))
    if not airborne:
        return

    no_fly = [
        row for row in airborne
        if 0.5 <= value(row, "x_m") <= 3.5
        and 3.5 <= value(row, "y_m") <= 6.5
    ]
    clearances = [
        math.hypot(value(row, "x_m") - 5.0, value(row, "y_m")) - 0.75
        for row in airborne
    ]
    target_errors = [
        math.hypot(value(row, "x_m") - 8.0, value(row, "y_m") - 5.0)
        for row in airborne
    ]
    track_errors = [
        cross_track_error((value(row, "x_m"), value(row, "y_m")))
        for row in airborne
    ]
    return_error = math.hypot(value(rows[-1], "x_m"), value(rows[-1], "y_m"))

    checks.check(len(no_fly) == 0, "No-fly-zone samples", str(len(no_fly)))
    checks.check(min(clearances) > 0.5, "Cylinder clearance",
                 "{:.3f} m".format(min(clearances)))
    checks.check(min(target_errors) < 0.35, "Target-point error",
                 "{:.3f} m".format(min(target_errors)))
    checks.check(max(track_errors) < 0.75, "Maximum cross-track error",
                 "{:.3f} m".format(max(track_errors)))
    checks.check(return_error < 0.35, "Final return error",
                 "{:.3f} m".format(return_error))
    checks.check(int(rows[-1]["armed"]) == 0, "Final armed state",
                 rows[-1]["armed"])


def check_bag(path, checks):
    try:
        result = subprocess.run(
            ["rosbag", "info", path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError:
        checks.warn("rosbag command",
                    "unavailable; run this check inside the ROS Noetic environment")
        return
    checks.check(result.returncode == 0, "rosbag index", os.path.basename(path))
    if result.returncode != 0:
        return
    missing = sorted(topic for topic in REQUIRED_TOPICS if topic not in result.stdout)
    checks.check(not missing, "rosbag topics",
                 "all 4 present" if not missing else "missing {}".format(", ".join(missing)))


def main():
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=os.path.join(package_dir, "data", "task2_final.csv"))
    parser.add_argument("--bag", default=os.path.join(package_dir, "data", "task2_final.bag"))
    args = parser.parse_args()

    checks = Checks()
    checks.check(os.path.isfile(args.csv), "CSV evidence", args.csv)
    checks.check(os.path.isfile(args.bag), "rosbag evidence", args.bag)
    if os.path.isfile(args.csv):
        check_csv(args.csv, checks)
    if os.path.isfile(args.bag):
        check_bag(args.bag, checks)

    print()
    if checks.failed:
        print("TASK2_ACCEPTANCE_CHECK: FAIL ({} checks failed)".format(checks.failed))
        return 1
    print("TASK2_ACCEPTANCE_CHECK: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
