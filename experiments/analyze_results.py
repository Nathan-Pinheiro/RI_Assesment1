#!/usr/bin/env python3
"""Analyze the 18 configured ROS 2/Webots runs in experiments/results.

Run from any directory:
    python3 /path/to/experiments/analyze_results.py

Reads CSVs only. Writes tables, validation notes, and 300-DPI figures to
experiments/analysis_results/. Requires pandas, numpy, and matplotlib.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "results"
OUT = ROOT / "experiments" / "analysis_results"
SEEDS = (18, 19, 20)
ROBOTS = {f"robot_{i}" for i in range(5)}
REQUIRED_COLUMNS = {
    "simulation_time", "robot_id", "seed", "noise_s", "left_speed",
    "right_speed", "following", "angular_error", "target_losses",
    "collision_avoidance", "x", "y",
}
NAME_RE = re.compile(
    r"^seed_(?P<seed>\d+)_follow_(?P<follow>off|on)_gain_(?P<gain>-?\d+(?:\.\d+)?)"
    r"_noise_(?P<noise>\d+(?:\.\d+)?)_source_(?P<source>none|lidar|wheels|both)"
    r"_avoid_(?P<avoid>off|on)\.csv$"
)


def expected_names() -> dict[str, tuple]:
    expected = {}
    for seed in SEEDS:
        for follow, gain, source, noise, avoid in (
            ("off", 0.0, "none", 0.0, "off"),
            ("on", 0.5, "none", 0.0, "on"),
            ("on", 1.5, "none", 0.0, "on"),
            ("on", 1.5, "lidar", 0.2, "on"),
            ("on", 1.5, "wheels", 0.2, "on"),
            ("on", 1.5, "both", 0.2, "on"),
        ):
            name = f"seed_{seed}_follow_{follow}_gain_{gain:.1f}_noise_{noise:.1f}_source_{source}_avoid_{avoid}.csv"
            expected[name] = (seed, follow, gain, noise, source, avoid)
    return expected


def write_validation(lines: list[str]) -> None:
    (OUT / "validation_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_filename(path: Path) -> dict:
    match = NAME_RE.match(path.name)
    if not match:
        raise ValueError("filename does not match expected experiment naming pattern")
    data = match.groupdict()
    return {
        "seed": int(data["seed"]),
        "following_config": data["follow"],
        "gain": float(data["gain"]),
        "noise": float(data["noise"]),
        "noise_source": data["source"],
        "avoidance_config": data["avoid"],
    }


def time_weighted_robot_metrics(frame: pd.DataFrame, run_end: float) -> dict:
    frame = frame.sort_values("simulation_time").drop_duplicates("simulation_time", keep="last").copy()
    times = frame["simulation_time"].to_numpy(dtype=float)
    if len(times) < 2:
        return {"following_rate_pct": np.nan, "mean_abs_angular_error_deg": np.nan,
                "observed_duration_s": 0.0}
    next_times = np.r_[times[1:], max(times[-1], run_end)]
    weights = np.maximum(0.0, next_times - times)
    observed = float(weights.sum())
    if observed <= 0:
        return {"following_rate_pct": np.nan, "mean_abs_angular_error_deg": np.nan,
                "observed_duration_s": 0.0}
    following = frame["following"].to_numpy(dtype=float) == 1
    following_rate = 100.0 * float(weights[following].sum()) / observed
    angle = frame["angular_error"].to_numpy(dtype=float)
    valid_angle = following & np.isfinite(angle) & (weights > 0)
    angular_error = (
        float(np.average(np.abs(angle[valid_angle]), weights=weights[valid_angle]))
        if valid_angle.any() else np.nan
    )
    return {"following_rate_pct": following_rate,
            "mean_abs_angular_error_deg": angular_error,
            "observed_duration_s": observed}


def analyze_file(path: Path, metadata: dict, issues: list[str]) -> tuple[list[dict], dict | None, pd.DataFrame | None]:
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        issues.append(f"INCOMPLETE {path.name}: CSV read failed: {exc}")
        return [], None, None
    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing_columns:
        issues.append(f"INCOMPLETE {path.name}: missing columns {missing_columns}")
        return [], None, None
    if frame.empty:
        issues.append(f"INCOMPLETE {path.name}: no data rows")
        return [], None, None
    numeric = sorted(REQUIRED_COLUMNS - {"robot_id"})
    for col in numeric:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    validation_numeric = [column for column in numeric if column != "angular_error"]
    if frame[validation_numeric].isna().any().any():
        bad = {c: int(n) for c, n in frame[validation_numeric].isna().sum().items() if n}
        issues.append(f"INCOMPLETE {path.name}: missing/non-numeric values {bad}")
    invalid_following_angle = frame["following"].eq(1) & frame["angular_error"].isna()
    if invalid_following_angle.any():
        issues.append(f"INCOMPLETE {path.name}: {int(invalid_following_angle.sum())} following rows have no angular_error")
    frame = frame.dropna(subset=["simulation_time", "seed", "noise_s", "following", "x", "y"])
    frame["robot_id"] = frame["robot_id"].astype(str)
    if frame.empty:
        issues.append(f"INCOMPLETE {path.name}: no valid rows after numeric validation")
        return [], None, None

    if set(frame["seed"].astype(int).unique()) != {metadata["seed"]}:
        issues.append(f"INCOMPLETE {path.name}: row seed metadata does not match filename")
    if not np.allclose(frame["noise_s"].to_numpy(), metadata["noise"], atol=1e-6):
        issues.append(f"INCOMPLETE {path.name}: row noise_s does not match filename")
    unknown = sorted(set(frame["robot_id"]) - ROBOTS)
    missing_robots = sorted(ROBOTS - set(frame["robot_id"]))
    if unknown:
        issues.append(f"INCOMPLETE {path.name}: unexpected robot IDs {unknown}")
    if missing_robots:
        issues.append(f"INCOMPLETE {path.name}: no rows for {missing_robots}")
    end = float(frame["simulation_time"].max())
    start = float(frame["simulation_time"].min())
    per_robot = []
    for robot in sorted(ROBOTS & set(frame["robot_id"])):
        rf = frame[frame["robot_id"] == robot].sort_values("simulation_time").copy()
        timed = time_weighted_robot_metrics(rf, end)
        losses = rf["target_losses"].dropna()
        counts = rf["collision_avoidance"].dropna()
        robot_record = {
            **metadata, "robot_id": robot,
            **timed,
            # Counter columns are cumulative: take the final observed value per robot.
            "target_losses": float(losses.iloc[-1]) if not losses.empty else np.nan,
            "collision_events_reported": float(counts.iloc[-1]) if not counts.empty else np.nan,
            "rows": int(len(rf)),
        }
        per_robot.append(robot_record)
        if timed["observed_duration_s"] <= 0:
            issues.append(f"INCOMPLETE {path.name}: {robot} has no usable time span")
        counts_over_time = rf["collision_avoidance"].dropna().to_numpy()
        if len(counts_over_time) > 1 and np.any(np.diff(counts_over_time) < 0):
            issues.append(f"WARNING {path.name}: {robot} collision counter is non-monotonic")

    robot_df = pd.DataFrame(per_robot)
    if robot_df.empty:
        return [], None, None
    # Macro-average robots within each simulation; cumulative counts are summed
    # across robot final counters, never summed across repeated CSV rows.
    simulation = {
        **metadata,
        "following_rate_pct": float(robot_df["following_rate_pct"].mean()),
        "mean_abs_angular_error_deg": float(robot_df["mean_abs_angular_error_deg"].mean()),
        "target_losses": float(robot_df["target_losses"].sum(min_count=1)),
        "collision_events_reported": float(robot_df["collision_events_reported"].sum(min_count=1)),
        "avoidance_enabled_pct": 100.0 if metadata["avoidance_config"] == "on" else 0.0,
        "simulation_start_s": start,
        "simulation_end_s": end,
        "simulation_duration_s": end - start,
        "robots_present": int(robot_df["robot_id"].nunique()),
        "total_rows": int(len(frame)),
        "source_file": path.name,
    }
    if end - start < 150:
        issues.append(f"INCOMPLETE {path.name}: duration {end - start:.2f}s is below 150s")
    return per_robot, simulation, frame


def mean_std_table(simulations: pd.DataFrame, group_columns: list[str], metrics: list[str]) -> pd.DataFrame:
    rows = []
    for key, group in simulations.groupby(group_columns, dropna=False, sort=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(group_columns, key))
        for metric in metrics:
            values = group[metric].dropna()
            row[f"{metric}_mean"] = float(values.mean()) if len(values) else np.nan
            row[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else np.nan
            row[f"{metric}_n"] = int(len(values))
            row[f"{metric}_mean_pm_std"] = (
                f"{values.mean():.2f} ± {values.std(ddof=1):.2f}" if len(values) > 1
                else (f"{values.mean():.2f} ± NA" if len(values) == 1 else "NA")
            )
        rows.append(row)
    return pd.DataFrame(rows)


def save_table(df: pd.DataFrame, name: str, title: str) -> None:
    df.to_csv(OUT / f"{name}.csv", index=False)
    columns = [str(c) for c in df.columns]
    lines = [f"# {title}", "", "| " + " | ".join(columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for row in df.itertuples(index=False, name=None):
        cells = ["NA" if pd.isna(value) else str(value) for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    (OUT / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def grouped_bar(summary: pd.DataFrame, label_column: str, metric: str, ylabel: str,
                title: str, filename: str, labels: list[str] | None = None) -> None:
    names = labels if labels is not None else summary[label_column].astype(str).tolist()
    indexed = summary.set_index(label_column)
    means = np.array([indexed.at[name, f"{metric}_mean"] if name in indexed.index else np.nan for name in names], dtype=float)
    stds = np.array([indexed.at[name, f"{metric}_std"] if name in indexed.index else 0.0 for name in names], dtype=float)
    counts = np.array([indexed.at[name, f"{metric}_n"] if name in indexed.index else 0 for name in names], dtype=int)
    fig, ax = plt.subplots(figsize=(6.6, 4.2), constrained_layout=True)
    x = np.arange(len(names))
    bars = ax.bar(x, means, yerr=stds, capsize=4, color=["#365f91", "#4b8f8c", "#d39145", "#8a6aa8"][:len(names)],
                  edgecolor="black", linewidth=0.6)
    ax.set_xticks(x, names, rotation=15, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    for bar, n in zip(bars, counts):
        if n:
            ax.annotate(f"n={int(n)}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8)
    fig.savefig(OUT / filename, dpi=300, bbox_inches="tight")
    plt.close(fig)


def trajectory_figure(runs: dict[int, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharex=False, sharey=False, constrained_layout=True)
    colors = plt.get_cmap("tab10")
    for ax, seed in zip(axes, SEEDS):
        frame = runs.get(seed)
        ax.set_title(f"Seed {seed}")
        if frame is None:
            ax.text(0.5, 0.5, "Missing simulation", transform=ax.transAxes, ha="center", va="center")
            continue
        for index, robot in enumerate(sorted(ROBOTS)):
            rf = frame[frame["robot_id"] == robot].sort_values("simulation_time")
            if rf.empty:
                continue
            x = rf["x"].to_numpy(dtype=float)
            y = rf["y"].to_numpy(dtype=float)
            color = colors(index)
            ax.plot(x, y, color=color, linewidth=1.0, label=robot)
            ax.scatter(x[0], y[0], marker="o", s=24, color=color, edgecolor="black", linewidth=0.4, zorder=3)
            ax.scatter(x[-1], y[-1], marker="X", s=32, color=color, edgecolor="black", linewidth=0.4, zorder=3)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(alpha=0.2)
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.01), ncol=5, frameon=False)
    fig.suptitle("Robot trajectories: strong turning, no noise")
    fig.savefig(OUT / "strong_turning_trajectories_seeds_18_20.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def compare_trajectory_pair(baseline: pd.DataFrame, noisy: pd.DataFrame,
                           seed: int, source: str, robot: str) -> dict | None:
    """Compare paired robot positions at common simulation times."""
    base = baseline[baseline["robot_id"] == robot].sort_values("simulation_time").drop_duplicates("simulation_time")
    test = noisy[noisy["robot_id"] == robot].sort_values("simulation_time").drop_duplicates("simulation_time")
    if len(base) < 2 or len(test) < 2:
        return None
    start = max(float(base["simulation_time"].min()), float(test["simulation_time"].min()))
    end = min(float(base["simulation_time"].max()), float(test["simulation_time"].max()))
    if end <= start:
        return None
    base_t = base["simulation_time"].to_numpy(dtype=float)
    test_t = test["simulation_time"].to_numpy(dtype=float)
    times = np.unique(np.r_[start, base_t[(base_t > start) & (base_t < end)],
                            test_t[(test_t > start) & (test_t < end)], end])
    bx = np.interp(times, base_t, base["x"].to_numpy(dtype=float))
    by = np.interp(times, base_t, base["y"].to_numpy(dtype=float))
    nx = np.interp(times, test_t, test["x"].to_numpy(dtype=float))
    ny = np.interp(times, test_t, test["y"].to_numpy(dtype=float))
    displacement = np.hypot(nx - bx, ny - by)
    dt = np.diff(times)
    mean_dev = float(np.average((displacement[:-1] + displacement[1:]) / 2.0, weights=dt))
    rms_dev = float(np.sqrt(np.average((displacement[:-1] ** 2 + displacement[1:] ** 2) / 2.0, weights=dt)))
    base_length = float(np.hypot(np.diff(bx), np.diff(by)).sum())
    test_length = float(np.hypot(np.diff(nx), np.diff(ny)).sum())
    return {
        "seed": seed, "noise_source": source, "robot_id": robot,
        "comparison_duration_s": end - start,
        "mean_position_deviation_m": mean_dev,
        "rms_position_deviation_m": rms_dev,
        "maximum_position_deviation_m": float(displacement.max()),
        "final_position_deviation_m": float(displacement[-1]),
        "baseline_path_length_m": base_length,
        "noisy_path_length_m": test_length,
        "path_length_difference_m": test_length - base_length,
        "absolute_path_length_difference_m": abs(test_length - base_length),
    }


def trajectory_noise_comparison(runs: dict[tuple[int, str], pd.DataFrame],
                                issues: list[str]) -> None:
    """Plot noisy paths against paired noiseless paths and export deviations."""
    sources = ["lidar", "wheels", "both"]
    source_labels = {"lidar": "LiDAR noise", "wheels": "Wheel noise", "both": "Combined noise"}
    colors = plt.get_cmap("tab10")
    rows = []
    fig, axes = plt.subplots(len(SEEDS), len(sources), figsize=(13, 10.5),
                             sharex=False, sharey=False)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.91, bottom=0.12,
                        wspace=0.2, hspace=0.28)
    for row_index, seed in enumerate(SEEDS):
        baseline = runs.get((seed, "none"))
        for col_index, source in enumerate(sources):
            ax = axes[row_index, col_index]
            noisy = runs.get((seed, source))
            ax.set_title(f"Seed {seed} — {source_labels[source]} (σ=0.2)")
            if baseline is None or noisy is None:
                absent = "no-noise baseline" if baseline is None else f"{source} noise run"
                ax.text(0.5, 0.5, f"Missing {absent}", transform=ax.transAxes,
                        ha="center", va="center")
                issues.append(f"MISSING trajectory comparison: seed={seed}, source={source}; {absent} unavailable")
            else:
                for index, robot in enumerate(sorted(ROBOTS)):
                    color = colors(index)
                    base_robot = baseline[baseline["robot_id"] == robot].sort_values("simulation_time")
                    noisy_robot = noisy[noisy["robot_id"] == robot].sort_values("simulation_time")
                    if base_robot.empty or noisy_robot.empty:
                        issues.append(f"INCOMPLETE trajectory comparison: seed={seed}, source={source}, robot={robot}")
                        continue
                    ax.plot(base_robot["x"], base_robot["y"], color=color, linestyle="--",
                            linewidth=0.9, alpha=0.5)
                    ax.plot(noisy_robot["x"], noisy_robot["y"], color=color,
                            linewidth=1.1, label=robot if row_index == 0 and col_index == 0 else None)
                    ax.scatter(noisy_robot["x"].iloc[0], noisy_robot["y"].iloc[0],
                               marker="o", s=15, color=color, edgecolor="black", linewidth=0.3)
                    ax.scatter(noisy_robot["x"].iloc[-1], noisy_robot["y"].iloc[-1],
                               marker="X", s=22, color=color, edgecolor="black", linewidth=0.3)
                    comparison = compare_trajectory_pair(baseline, noisy, seed, source, robot)
                    if comparison is not None:
                        rows.append(comparison)
                    else:
                        issues.append(f"INCOMPLETE trajectory comparison: seed={seed}, source={source}, robot={robot}; no overlapping time interval")
            ax.set_xlabel("x (m)")
            ax.set_ylabel("y (m)")
            ax.set_aspect("equal", adjustable="datalim")
            ax.grid(alpha=0.2)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.025),
                   ncol=5, frameon=False, title="Robot (solid = noisy; dashed same-color path = no noise)")
    fig.suptitle("Trajectory differences: noisy runs versus no-noise baseline", y=0.98)
    fig.savefig(OUT / "trajectory_noise_comparison_seeds_18_20.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    deviations = pd.DataFrame(rows)
    if deviations.empty:
        issues.append("NO trajectory deviations could be calculated")
        return
    deviations.to_csv(OUT / "trajectory_noise_deviation_per_robot.csv", index=False)
    simulation_rows = []
    for (seed, source), group in deviations.groupby(["seed", "noise_source"]):
        row = {"seed": int(seed), "noise_source": source,
               "robots_compared": int(group["robot_id"].nunique())}
        for metric in ("mean_position_deviation_m", "rms_position_deviation_m",
                       "maximum_position_deviation_m", "final_position_deviation_m",
                       "baseline_path_length_m", "noisy_path_length_m",
                       "path_length_difference_m", "absolute_path_length_difference_m"):
            row[metric] = float(group[metric].mean())
        simulation_rows.append(row)
    per_simulation = pd.DataFrame(simulation_rows)
    per_simulation.to_csv(OUT / "trajectory_noise_deviation_per_simulation.csv", index=False)
    summary = mean_std_table(per_simulation, ["noise_source"], [
        "mean_position_deviation_m", "rms_position_deviation_m",
        "final_position_deviation_m", "baseline_path_length_m",
        "noisy_path_length_m", "path_length_difference_m",
        "absolute_path_length_difference_m",
    ])
    summary["noise_condition"] = summary["noise_source"].map(source_labels)
    save_table(summary, "trajectory_noise_deviation_summary",
               "Trajectory deviation from no-noise baseline")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    issues: list[str] = []
    expected = expected_names()
    paths = sorted(RESULTS.glob("*.csv"))
    by_name = {path.name: path for path in paths}
    missing = sorted(set(expected) - set(by_name))
    unexpected = sorted(set(by_name) - set(expected))
    if missing:
        issues.extend(f"MISSING simulation: {name}" for name in missing)
    if unexpected:
        issues.extend(f"UNEXPECTED CSV (not included): {name}" for name in unexpected)

    robot_records, simulation_records, trajectory_runs, comparison_runs = [], [], {}, {}
    for name, metadata_tuple in expected.items():
        path = by_name.get(name)
        if path is None:
            continue
        metadata = parse_filename(path)
        robot_rows, simulation, frame = analyze_file(path, metadata, issues)
        robot_records.extend(robot_rows)
        if simulation:
            simulation_records.append(simulation)
            if metadata["gain"] == 1.5 and metadata["noise_source"] == "none" and metadata["noise"] == 0 and metadata["avoidance_config"] == "on":
                trajectory_runs[metadata["seed"]] = frame
            if (metadata["gain"] == 1.5 and metadata["following_config"] == "on"
                    and metadata["avoidance_config"] == "on"
                    and metadata["noise_source"] in {"none", "lidar", "wheels", "both"}):
                comparison_runs[(metadata["seed"], metadata["noise_source"])] = frame

    per_robot = pd.DataFrame(robot_records)
    simulations = pd.DataFrame(simulation_records)
    if not per_robot.empty:
        per_robot.to_csv(OUT / "per_robot_metrics.csv", index=False)
    if not simulations.empty:
        simulations.to_csv(OUT / "per_simulation_metrics.csv", index=False)

    metrics = ["following_rate_pct", "mean_abs_angular_error_deg", "target_losses",
               "avoidance_enabled_pct", "collision_events_reported"]
    exp1 = simulations[
        (simulations["noise_source"] == "none") & (simulations["noise"] == 0)
        & (simulations["gain"].isin([0.0, 0.5, 1.5]))
    ].copy() if not simulations.empty else pd.DataFrame()
    if not exp1.empty:
        exp1["configuration"] = exp1["gain"].map({0.0: "No following (gain=0)", 0.5: "Weak turning (gain=0.5)", 1.5: "Strong turning (gain=1.5)"})
        summary1 = mean_std_table(exp1, ["configuration"], metrics)
        save_table(summary1, "experiment1_following_performance", "Experiment 1 — Following performance")

    noise_labels = {"none": "No noise", "lidar": "LiDAR noise", "wheels": "Wheel noise", "both": "Combined noise"}
    exp2 = simulations[(simulations["gain"] == 1.5) & (simulations["following_config"] == "on")].copy() if not simulations.empty else pd.DataFrame()
    if not exp2.empty:
        exp2["noise_condition"] = exp2["noise_source"].map(noise_labels)
        order = list(noise_labels.values())
        exp2["noise_condition"] = pd.Categorical(exp2["noise_condition"], categories=order, ordered=True)
        summary2 = mean_std_table(exp2.sort_values("noise_condition"), ["noise_condition"], metrics)
        save_table(summary2, "experiment2_noise_robustness", "Experiment 2 — Noise robustness")
        grouped_bar(summary2, "noise_condition", "following_rate_pct", "Following rate (%)",
                    "Following rate by noise condition", "noise_following_rate.png", order)
        grouped_bar(summary2, "noise_condition", "mean_abs_angular_error_deg", "Mean absolute angular error (degrees)",
                    "Angular error by noise condition", "noise_angular_error.png", order)
        grouped_bar(summary2, "noise_condition", "target_losses", "Target losses (sum across five robots)",
                    "Target losses by noise condition", "noise_target_losses.png", order)

    trajectory_figure(trajectory_runs)
    trajectory_noise_comparison(comparison_runs, issues)
    if len(expected) != 18:
        issues.append(f"INTERNAL ERROR: manifest contains {len(expected)} expected runs, not 18")
    if simulations.empty:
        issues.append("NO usable simulations were analyzed")
    issues.insert(0, f"Expected simulations: {len(expected)}; present CSVs: {len(set(expected) & set(by_name))}; usable simulations: {len(simulations)}")
    issues.insert(1, "Angular error is in degrees (controller stores abs(sensor_angles_deg[nearest]) as angular_error).")
    issues.insert(2, "CSV collision_avoidance contains the cumulative near_collision_count. It is reported as collision_events_reported; it is not used as an activation rate.")
    issues.insert(3, "avoidance_enabled_pct is derived from the filename configuration (100% enabled, 0% disabled), not a measured activation duty cycle.")
    issues.insert(4, "Following rate and angular error use time-weighted intervals per robot; simulation summaries macro-average the five robot metrics. Target losses and reported collision counts use each robot's final cumulative counter, summed across robots.")
    write_validation(issues or ["No missing or incomplete simulations detected."])
    print(f"Analyzed {len(simulations)} usable / {len(expected)} expected simulations.")
    print(f"Output: {OUT}")
    print(f"Validation: {OUT / 'validation_report.txt'}")
    if missing or any(line.startswith("INCOMPLETE") for line in issues):
        print("WARNING: missing or incomplete simulations are documented in validation_report.txt")
    print("Paper recommendation (4 IEEE pages): figures — the three-seed trajectory panel and the noisy-versus-noiseless trajectory comparison; tables — Experiment 1 following-performance comparison and Experiment 2 noise-robustness comparison. The trajectory deviation summary is a useful supplementary table.")
    return 1 if missing or any(line.startswith("INCOMPLETE") for line in issues) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        sys.exit(2)
