#!/usr/bin/env python3
"""Generate the Task 2 trajectory, altitude, and speed verification figure."""

import argparse
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np


PLANNED_XY = np.array([
    [0.0, 0.0], [2.0, 2.28358], [3.5, -2.0], [6.5, -2.0],
    [8.0, -2.0], [8.0, 5.0], [4.2, 7.2], [-0.5, 7.5],
    [-0.5, 2.5], [0.0, 0.0],
])
WAYPOINT_LABELS = [
    "Start", "Cyan", "Cylinder entry", "Cylinder exit", "Magenta",
    "Target", "No-fly upper right", "No-fly upper left",
    "No-fly lower left", "Return",
]


def load_csv(path):
    with open(path, newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("CSV contains no flight samples")
    numeric = {}
    for field in ("time_s", "x_m", "y_m", "z_m", "vx_mps", "vy_mps", "vz_mps"):
        numeric[field] = np.array([float(row[field]) for row in rows])
    numeric["armed"] = np.array([int(row["armed"]) for row in rows], dtype=bool)
    return numeric


def point_segment_distance(px, py, a, b):
    ab = b - a
    denominator = float(np.dot(ab, ab))
    if denominator == 0:
        return math.hypot(px - a[0], py - a[1])
    t = ((px - a[0]) * ab[0] + (py - a[1]) * ab[1]) / denominator
    t = min(1.0, max(0.0, t))
    closest = a + t * ab
    return math.hypot(px - closest[0], py - closest[1])


def tracking_error(x, y):
    route = PLANNED_XY
    return np.array([
        min(point_segment_distance(px, py, route[i], route[i + 1])
            for i in range(len(route) - 1))
        for px, py in zip(x, y)
    ])


def main():
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=os.path.join(
            package_dir, "data", "task2_final.csv"
        ),
    )
    parser.add_argument(
        "--output",
        default=os.path.join(
            package_dir, "plots", "task2_final_analysis.png"
        ),
    )
    args = parser.parse_args()

    data = load_csv(args.input)
    time = data["time_s"]
    x, y, z = data["x_m"], data["y_m"], data["z_m"]
    speed = np.sqrt(data["vx_mps"] ** 2 + data["vy_mps"] ** 2 + data["vz_mps"] ** 2)
    active = data["armed"] & (z > 0.5)
    if not np.any(active):
        raise ValueError("No airborne samples found")

    errors = tracking_error(x[active], y[active])
    active_indices = np.flatnonzero(active)
    max_local = int(np.argmax(errors))
    max_index = int(active_indices[max_local])
    max_error = float(errors[max_local])

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.edgecolor": "#374151",
        "text.color": "#1f2937",
        "axes.labelcolor": "#1f2937",
        "xtick.color": "#4b5563",
        "ytick.color": "#4b5563",
    })
    fig = plt.figure(figsize=(14, 7.5), facecolor="white")
    grid = fig.add_gridspec(2, 2, width_ratios=[1.25, 1.0], hspace=0.34, wspace=0.28)
    ax_path = fig.add_subplot(grid[:, 0])
    ax_alt = fig.add_subplot(grid[0, 1])
    ax_speed = fig.add_subplot(grid[1, 1])

    # XY evidence view: planned route, actual route, and physical constraints.
    ax_path.add_patch(Circle((5, 0), 0.75, facecolor="#f59e0b", edgecolor="#92400e",
                             linewidth=1.5, alpha=0.9, label="Cylinder obstacle"))
    ax_path.add_patch(Rectangle((0.5, 3.5), 3.0, 3.0, facecolor="#fde68a",
                                edgecolor="#92400e", hatch="//", linewidth=1.4,
                                alpha=0.75, label="No-fly zone"))
    ax_path.plot(PLANNED_XY[:, 0], PLANNED_XY[:, 1], color="#6b7280",
                 linestyle="--", linewidth=1.8, label="Planned route")
    ax_path.plot(x[active], y[active], color="#2563eb", linewidth=2.0,
                 label="Recorded airborne trajectory")

    unique_waypoints = PLANNED_XY
    ax_path.scatter(unique_waypoints[:, 0], unique_waypoints[:, 1], s=55,
                    facecolors="white", edgecolors="#111827", linewidths=1.5,
                    zorder=5, label="Mission waypoints")
    for label, point in zip(WAYPOINT_LABELS, unique_waypoints):
        ax_path.annotate(label, point, xytext=(5, 7), textcoords="offset points",
                         fontsize=8, color="#111827")
    ax_path.scatter([x[max_index]], [y[max_index]], color="#dc2626", marker="x",
                    s=75, linewidths=2.0, zorder=6)
    ax_path.annotate("Max cross-track error\n{:.2f} m".format(max_error),
                     (x[max_index], y[max_index]), xytext=(28, -35),
                     textcoords="offset points",
                     arrowprops={"arrowstyle": "->", "color": "#dc2626"},
                     color="#991b1b", fontsize=9,
                     bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#fecaca"})
    ax_path.set_title("Task 2 XY flight trajectory")
    ax_path.text(0.0, 1.01, "ENU local frame (m); airborne samples only",
                 transform=ax_path.transAxes, fontsize=9, color="#6b7280")
    ax_path.set_xlabel("East x (m)")
    ax_path.set_ylabel("North y (m)")
    ax_path.set_aspect("equal", adjustable="box")
    ax_path.grid(True, color="#e5e7eb", linewidth=0.8)
    ax_path.legend(loc="upper left", frameon=True, framealpha=0.95, fontsize=8)

    ax_alt.plot(time, z, color="#2563eb", linewidth=1.5)
    ax_alt.axhline(1.0, color="#f59e0b", linestyle="--", linewidth=1.3,
                   label="1 m local-z rule reference")
    ax_alt.set_title("Local altitude over time")
    ax_alt.set_ylabel("Local z (m)")
    ax_alt.grid(True, color="#e5e7eb", linewidth=0.8)
    ax_alt.legend(loc="lower right", fontsize=8)
    ax_alt.text(0.0, 1.01, "MAVROS ENU local z; includes estimator-origin shift before takeoff",
                transform=ax_alt.transAxes, fontsize=8, color="#6b7280")

    ax_speed.plot(time, speed, color="#d97706", linewidth=1.4)
    ax_speed.set_title("3D speed over time")
    ax_speed.set_xlabel("Elapsed recording time (s)")
    ax_speed.set_ylabel("Speed (m/s)")
    ax_speed.grid(True, color="#e5e7eb", linewidth=0.8)
    ax_speed.text(0.98, 0.92, "Peak {:.2f} m/s".format(float(np.max(speed))),
                  transform=ax_speed.transAxes, ha="right", va="top",
                  bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#fed7aa"},
                  color="#92400e")

    fig.suptitle("Week 3 Task 2 — Flight data verification", x=0.06, y=0.985,
                 ha="left", fontsize=15, fontweight="bold", color="#111827")
    fig.text(0.06, 0.02,
             "Source: {} | {} samples | {:.1f} s | max cross-track error {:.2f} m"
             .format(
                 os.path.basename(args.input), len(time),
                 float(time[-1] - time[0]), max_error
             ),
             fontsize=9, color="#4b5563")
    fig.savefig(args.output, dpi=180, bbox_inches="tight", facecolor="white")
    print("saved:", os.path.abspath(args.output))
    print("samples:", len(time))
    print("duration_s: {:.3f}".format(float(time[-1] - time[0])))
    print("max_cross_track_error_m: {:.4f}".format(max_error))
    print("max_speed_mps: {:.4f}".format(float(np.max(speed))))


if __name__ == "__main__":
    main()
