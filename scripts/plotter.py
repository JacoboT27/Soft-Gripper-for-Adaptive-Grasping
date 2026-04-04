import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.gridspec as gridspec
import sys
import os

# ── Config ────────────────────────────────────────────────────────────────────
CSV_FILE   = "data/cylinder_7.csv"   # Change to your saved file name
TRIAL_NAME = "Trial 1 - Cylinder"  # Label shown on plots

GRASP_DETECT_THRESH = 1200      #2000
GRASP_STOP_THRESH   = 3000      #3500

# Create output folder based on trial name
output_folder = TRIAL_NAME.replace(" ", "_").replace("-", "_")
output_folder = os.path.join("data", output_folder)
os.makedirs(output_folder, exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
# Lines starting with '#' or '---' are comments/separators — skip them
df = pd.read_csv(
    CSV_FILE,
    comment="#",
    skipinitialspace=True,
    skiprows=1,
)
df = df[df["time_ms"].apply(lambda x: str(x).strip()) != "---"]
df = df[df["time_ms"].apply(lambda x: str(x).strip()) != "time_ms"]  # skip duplicate headers
df = df.apply(pd.to_numeric, errors="coerce").dropna()
df["time_s"] = df["time_ms"] / 1000.0

# Find transition moments
grasp_detect_time = df.loc[df["is_grasped"] == 1, "time_s"].min()
grasp_detect_angle = df.loc[df["is_grasped"] == 1, "angle"].min()

# ── Plot 1: Sensor readings + angle vs time (stacked) ─────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
fig.suptitle(f"Grasp Event — {TRIAL_NAME}", fontsize=13, fontweight="bold")

# Sensor readings
ax1.plot(df["time_s"], df["S1"],  label="S1", linewidth=1.5, color="blue")
ax1.plot(df["time_s"], df["S2"],  label="S2", linewidth=1.5, color="red")
ax1.plot(df["time_s"], df["max"], label="Max", linewidth=1.8, color="black", linestyle="--")
ax1.axhline(GRASP_DETECT_THRESH, color="orange", linestyle=":", linewidth=1.2, label=f"Detect threshold ({GRASP_DETECT_THRESH})")
ax1.axhline(GRASP_STOP_THRESH,   color="green",  linestyle=":", linewidth=1.2, label=f"Stop threshold ({GRASP_STOP_THRESH})")
if not pd.isna(grasp_detect_time):
    ax1.axvline(grasp_detect_time, color="purple", linestyle="--", linewidth=1, alpha=0.7, label="isGrasped ON")
ax1.set_ylabel("ADC Value (0–4095)")
ax1.set_ylim(-100, 4200)
ax1.legend(fontsize=8, loc="upper left")
ax1.grid(True, alpha=0.3)

# Servo angle
ax2.plot(df["time_s"], df["angle"], label="Servo angle", linewidth=1.8, color="mediumpurple")
if not pd.isna(grasp_detect_time):
    ax2.axvline(grasp_detect_time, color="orange", linestyle="--", linewidth=1, alpha=0.7, label="isGrasped ON")
ax2.set_ylabel("Angle (°)")
ax2.set_xlabel("Time (s)")
ax2.set_ylim(-2, 60)
ax2.legend(fontsize=8, loc="upper left")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(output_folder, "plot_time_series.png"), dpi=150)
plt.show()
print(f"Saved: {os.path.join(output_folder, 'plot_time_series.png')}")

# ── Plot 2: Angle vs sensor reading ───────────────────────────────────────────
fig2, ax = plt.subplots(figsize=(12, 4))
ax.plot(df["angle"], df["S1"],  label="S1",  linewidth=2, color="blue")
ax.plot(df["angle"], df["S2"],  label="S2",  linewidth=2, color="red")
ax.plot(df["angle"], df["max"], label="Max", linewidth=2, color="black", linestyle="--")
ax.axhline(GRASP_DETECT_THRESH, color="orange", linestyle=":", linewidth=2, label=f"Detect threshold ({GRASP_DETECT_THRESH})")
ax.axhline(GRASP_STOP_THRESH,   color="green",  linestyle=":", linewidth=2, label=f"Stop threshold ({GRASP_STOP_THRESH})")
if not pd.isna(grasp_detect_angle):
    ax.axvline(grasp_detect_angle, color="purple", linestyle="--", linewidth=2, alpha=0.7, label=f"Contact angle ({int(grasp_detect_angle)}°)")
stopped_angle = df["angle"].max()
ax.axvline(stopped_angle, color="red", linestyle="--", linewidth=2, alpha=0.7, label=f"Stopped angle ({int(stopped_angle)}°)")
ax.set_xlabel("Servo Angle (°)", fontsize=16)
ax.set_ylabel("ADC Value (0–4095)", fontsize=16)
ax.set_title(f"Sensor Reading vs. Angle — {TRIAL_NAME}", fontsize=18, fontweight="bold")
ax.legend(fontsize=15)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_folder, "plot_angle_vs_sensor.png"), dpi=150)
plt.show()
print(f"Saved: {os.path.join(output_folder, 'plot_angle_vs_sensor.png')}")

# ── Plot 3: Grasp Repeatability — all geometries ─────────────────────────────
# Fill in your recorded angles below (one value per trial)
data = {
    "Sphere": {
        "contact": [45, 42, 44, 41, 42, 41, 41, 41, 41, 41],  # angle when max >= GRASP_DETECT_THRESH
        "stop":    [54, 53, 53, 53, 50, 49, 50, 50, 50, 50],  # angle when max >= GRASP_STOP_THRESH
    },
    "Cylinder": {
        "contact": [38, 39, 40, 41, 41, 38, 39, 38, 38, 38],
        "stop":    [52, 49, 48, 48, 48, 49, 49, 50, 50, 52],
    },
    "Icosahedron": {
        "contact": [45, 41, 41, 41, 43, 47, 47, 47, 46, 44],
        "stop":    [54, 52, 52, 52, 53, 54, 54, 54, 54, 54],
    },
}
 
n_trials    = 10
n_geometries = len(data)
geometries  = list(data.keys())
colors      = {
    "Sphere":   {"contact": "#5b9bd5", "stop": "#2e6da4"},
    "Cylinder": {"contact": "#f4a460", "stop": "#c0622a"},
    "Icosahedron":{"contact": "#82c982", "stop": "#3a8a3a"},
}
 
# Each geometry occupies a group of n_trials positions, with a gap between groups
group_width = n_trials + 2  # 2-unit gap between geometry groups
bar_width   = 0.35
x_trials    = np.arange(n_trials)
 
fig, ax = plt.subplots(figsize=(16, 5))
 
for g_idx, geometry in enumerate(geometries):
    offset = g_idx * group_width
    x = x_trials + offset
 
    contact = np.array(data[geometry]["contact"])
    stop    = np.array(data[geometry]["stop"])
 
    ax.bar(x - bar_width / 2, contact, bar_width,
           color=colors[geometry]["contact"], zorder=2,
           label=f"{geometry} — Contact" if g_idx == 0 else f"{geometry} — Contact")
    ax.bar(x + bar_width / 2, stop, bar_width,
           color=colors[geometry]["stop"], zorder=2,
           label=f"{geometry} — Stop")
 
    # Mean lines scoped to each geometry group
    ax.hlines(np.mean(contact), offset - 0.5, offset + n_trials - 0.5,
              colors=colors[geometry]["contact"], linestyles="--", linewidth=1.5,
              label=f"{geometry} mean contact: {np.mean(contact):.1f}°")
    ax.hlines(np.mean(stop), offset - 0.5, offset + n_trials - 0.5,
              colors=colors[geometry]["stop"], linestyles="--", linewidth=1.5,
              label=f"{geometry} mean stop: {np.mean(stop):.1f}°")
 
    # Geometry label centred under its group
    ax.text(offset + (n_trials - 1) / 2, -4, geometry,
            ha="center", va="top", fontsize=12, fontweight="bold")
 
# X axis: trial numbers 1–10 repeated for each geometry
all_x      = np.concatenate([x_trials + g * group_width for g in range(n_geometries)])
all_labels = [str(t + 1) for t in range(n_trials)] * n_geometries
ax.set_xticks(all_x)
ax.set_xticklabels(all_labels, fontsize=8)
 
ax.set_ylabel("Angle (°)", fontsize=13)
ax.set_title("Grasp Repeatability — All Geometries", fontsize=14, fontweight="bold")
ax.set_ylim(0, 65)
ax.legend(fontsize=8, ncol=3, loc="upper right")
ax.grid(True, axis="y", alpha=0.3, zorder=1)
 
plt.tight_layout()
plt.savefig(os.path.join("data", "plot_repeatability.png"), dpi=150)
plt.show()
print("Saved: data/plot_repeatability.png")

# ── Plot 4: Grasp Angle Frequency — all geometries ───────────────────────────
# Fill in your recorded angles below (one value per trial, 10 trials each)
data = {
    "Sphere": {
        "contact": [45, 42, 44, 41, 42, 41, 41, 41, 41, 41],  # angle when max >= GRASP_DETECT_THRESH
        "stop":    [54, 53, 53, 53, 50, 49, 50, 50, 50, 50],  # angle when max >= GRASP_STOP_THRESH
    },
    "Cylinder": {
        "contact": [38, 39, 40, 41, 41, 38, 39, 38, 38, 38],
        "stop":    [52, 49, 48, 48, 48, 49, 49, 50, 50, 52],
    },
    "Icosahedron": {
        "contact": [45, 41, 41, 41, 43, 47, 47, 47, 46, 44],
        "stop":    [54, 52, 52, 52, 53, 54, 54, 54, 54, 54],
    },
}
 
geometries   = list(data.keys())
colors       = {
    "Sphere":       {"contact": "#5b9bd5", "stop": "#2e6da4"},
    "Cylinder":     {"contact": "#f4a460", "stop": "#c0622a"},
    "Icosahedron":  {"contact": "#82c982", "stop": "#3a8a3a"},
}
 
fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=True)
fig.suptitle("Grasp Angle Distribution — All Geometries", fontsize=16, fontweight="bold")
 
for ax, geometry in zip(axes, geometries):
    contact = np.array(data[geometry]["contact"])
    stop    = np.array(data[geometry]["stop"])
 
    # Get all unique angle values across both arrays to define bins
    all_angles  = np.union1d(contact, stop)
    angle_range = np.arange(all_angles.min() - 1, all_angles.max() + 2)  # integer bins
 
    # Count frequency of each angle value
    contact_counts = np.array([np.sum(contact == a) for a in angle_range])
    stop_counts    = np.array([np.sum(stop    == a) for a in angle_range])
 
    bar_width = 0.5
    x = np.arange(len(angle_range))
 
    ax.bar(x - bar_width / 2, contact_counts, bar_width,
           color=colors[geometry]["contact"], zorder=2, label="Contact angle")
    ax.bar(x + bar_width / 2, stop_counts,    bar_width,
           color=colors[geometry]["stop"],    zorder=2, label="Stop angle")
 
    # Mean lines — convert mean angle to x-axis position
    mean_contact_x = np.interp(np.mean(contact), angle_range, x)
    mean_stop_x    = np.interp(np.mean(stop),    angle_range, x)
    ax.axvline(mean_contact_x, color=colors[geometry]["contact"], linestyle="--",
               linewidth=1.8, label=f"Mean contact: {np.mean(contact):.1f}°")
    ax.axvline(mean_stop_x,    color=colors[geometry]["stop"],    linestyle="--",
               linewidth=1.8, label=f"Mean stop: {np.mean(stop):.1f}°")
 
    ax.set_xticks(x)
    ax.set_xticklabels(angle_range, fontsize=11)
    ax.set_xlabel("Angle (°)", fontsize=15)
    ax.set_title(geometry, fontsize=15, fontweight="bold")
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.legend(fontsize=15, loc="upper center")
    ax.grid(True, axis="y", alpha=0.3, zorder=1)
 
axes[0].set_ylabel("Frequency (trials)", fontsize=15)
 
plt.tight_layout()
plt.savefig(os.path.join("data", "plot_repeatability.png"), dpi=150)
plt.show()
print("Saved: data/plot_repeatability.png")