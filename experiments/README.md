# CSV Logger

`csv_logger.py` records data from all five robots (`robot_0` to `robot_4`), including their Webots x/y positions.

## Prerequisites

The logger requires the project ROS 2 environment and the Webots ROS 2 driver.
NumPy is used by the controller and analysis; pandas and Matplotlib are needed
for the analysis script. The project configuration loader uses PyYAML. Install the
project's system packages with the same Python/ROS installation you use to run
the simulation (do not install `rclpy` with pip):

```bash
source /opt/ros/jazzy/setup.bash  # replace jazzy if you use another ROS 2 distribution
sudo apt update
sudo apt install python3-colcon-common-extensions \
  ros-$ROS_DISTRO-webots-ros2 ros-$ROS_DISTRO-geometry-msgs \
  ros-$ROS_DISTRO-std-msgs python3-yaml python3-numpy \
  python3-pandas python3-matplotlib
```

You also need Webots R2025a and a built ROS 2 workspace. From the workspace
root, build and source the package if it has not already been built:

```bash
cd ~/ros2_ws
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --packages-select ri_a1 --symlink-install
source install/setup.bash
```

The ROS installation supplies `rclpy`, `std_msgs`, `geometry_msgs`, `launch`,
and `webots_ros2_driver`. The analysis libraries are only needed when
generating the summary tables and plots. No `requirements.txt` is currently
provided.

## Run

In the first terminal, start the simulation from the ROS 2 workspace:

```bash
cd ~/ros2_ws
source /opt/ros/$ROS_DISTRO/setup.bash
source install/setup.bash
ros2 launch ri_a1 launch.py
```

In a second terminal, start the logger from the project directory:

```bash
cd ~/ros2_ws
source /opt/ros/$ROS_DISTRO/setup.bash
source install/setup.bash
python3 src/RI_Assesment1/experiments/csv_logger.py \
  --seed 18 --noise 0.2 --source lidar --gain 1.5 \
  --following on --avoidance on
```

Before launching, configure the actual simulation in `config/config.yaml`. Set `seed` (unless explicitly overridden with the supported `random_seed:=...` launch argument), and configure `robot.turn_gain`, `robot.following_behaviour`, `robot.collision_avoidance`, `robot.lidar_noise`, `robot.wheel_noise`, and `robot.strength` for the experiment. Per-robot values under `robots:` override corresponding defaults under `robot:`. The launch file supports `random_seed`, `mode`, and `gui`; it does not accept noise, gain, following, or avoidance launch arguments. `ri_a1.config` looks for `config.yaml` in the installed ROS 2 package share first, then falls back to the source tree, so make sure the config actually loaded by ROS 2 contains your edits (rebuild/re-source the workspace if needed).

The logger's `--seed` and `--noise` are metadata only. Its `--source`, `--gain`, `--following`, and `--avoidance` options also only describe the run and determine the CSV filename; none of these options changes Webots or controller settings. Set them to match the configuration that is actually running, or the CSV will be mislabeled. `--source` accepts `none`, `lidar`, `wheels`, or `both`; `--following` and `--avoidance` accept `on` or `off`.

Press **Ctrl+C** in the logger terminal to stop logging. CSV files are saved in `experiments/results/`.

## CSV columns

`simulation_time`, `robot_id`, `seed`, `noise_s`, `left_speed`, `right_speed`, `following`, `angular_error`, `target_losses`, `collision_avoidance`, `x`, `y`.

`x` and `y` are the robot's horizontal position coordinates in Webots.

## What is in this folder?

- `csv_logger.py` subscribes to `/robot_0/wheel_speeds` through
  `/robot_4/wheel_speeds` and saves the fields above. It does **not** start or
  configure Webots; start the simulation separately and stop the logger with
  **Ctrl+C** when the run is complete.
- `results/` contains the simulation CSV files. The current set has 18 runs
  for seeds 18, 19, and 20: no/weak/strong following and no noise, LiDAR
  noise, wheel noise, or combined noise. Filenames record seed, following
  mode, gain, noise level/source, and avoidance setting.
- `experiments_article.txt` lists the logger metadata for the 18 planned
  configurations. It is a reference, not a script to execute: simulation
  settings must also be changed in `config/config.yaml` for each run. Follow
  “Run the experiment set” below for the run order.
- `analyze_results.py` validates the expected CSV set and summarizes each
  robot and simulation. It writes tables, validation notes, noise comparison
  plots, and trajectory plots into `analysis_results/`.
- `analysis_results/` contains the generated tables, figures, and
  `validation_report.txt`. The trajectory comparison includes a no-noise
  baseline against LiDAR, wheel, and combined noise for each seed, plus a
  table of position and path-length differences.
- `position_supervisor.py` is a small Webots Supervisor helper that looks up
  the five robot nodes by their DEF names. It does not currently run an
  experiment or save results.

## Run the experiment set

1. Before **each** run, set the real simulation parameters in the loaded
   `config/config.yaml`: `seed`, `robot.turn_gain`,
   `robot.following_behaviour`, `robot.collision_avoidance`,
   `robot.lidar_noise`, `robot.wheel_noise`, and `robot.strength`. For the
   three noise conditions, enable only the matching noise flag (or both for
   combined noise). Set the flags to `false` for the no-noise condition.
   Per-robot overrides under `robots:` take precedence for keys they specify.
   The launch file's optional `random_seed` argument changes spawn generation;
   use the YAML `seed` and omit that override when following this procedure.
   Check that ROS 2 loads the file you edited; without `--symlink-install`, a
   rebuild may be needed after changing the source YAML.
2. In terminal 1, start a new simulation from the ROS 2 workspace:

   ```bash
   cd ~/ros2_ws
   source /opt/ros/$ROS_DISTRO/setup.bash
   source install/setup.bash
   ros2 launch ri_a1 launch.py
   ```

   Wait for Webots and the robot controllers to start before starting the
   logger. Do not launch the next simulation while this one is running.
3. In terminal 2, start the logger with metadata that matches the YAML
   settings. For example, for seed 18 with LiDAR-distance noise enabled:

   ```bash
   cd ~/ros2_ws
   source /opt/ros/$ROS_DISTRO/setup.bash
   source install/setup.bash
   python3 src/RI_Assesment1/experiments/csv_logger.py \
     --seed 18 --noise 0.2 --source lidar --gain 1.5 \
     --following on --avoidance on
   ```

4. Let the Webots simulation run for the duration required by your protocol.
   `csv_logger.py` records Webots simulation time but has no duration limit;
   stop it with **Ctrl+C** when the trial is complete. Then stop the ROS 2
   launch with **Ctrl+C** in terminal 1 and wait for it to exit before editing
   the YAML and starting another run.
5. Repeat for every condition and seed listed in `experiments_article.txt` and
   the analysis manifest. The text file's background-launch examples are not
   a safe automation script; use the sequential steps above. The manifest
   expects six conditions per seed (18 CSVs total for seeds 18, 19, and 20).
   The logger arguments only label the CSV;
   they do not apply the simulation settings. Check the `Logging to ...`
   message for the output filename. Repeating an identical logger argument
   set overwrites its existing CSV, so preserve or rename results before
   repeating a condition.

The logger creates `experiments/results/` automatically and flushes each CSV
row as it is written. Finish and close the logger before shutting down Webots
or starting another experiment. The current project does not automate the
18-run sequence or stop runs at an exact simulation-time target.

The logger's `--seed`, `--noise`, `--source`, `--gain`, `--following`, and
`--avoidance` arguments describe the run in the CSV filename and metadata;
they do not change the active simulation configuration. Keep the logger
arguments and the config file actually loaded by ROS 2 in agreement. The logger opens
its matching CSV filename for writing, so running the same combination again
overwrites that file.

## Analyze the results

After collecting the required CSV files, run the analyzer from the repository
root:

```bash
python3 experiments/analyze_results.py
```

The analysis uses pandas, NumPy, and Matplotlib. It expects the 18 named CSVs
for seeds 18–20, reports missing or incomplete runs in
`experiments/analysis_results/validation_report.txt`, and writes plots at
300 DPI. It calculates following rate and angular error per robot before
averaging robots; cumulative target-loss and reported collision counters use
the final counter value per robot.

The script creates `experiments/analysis_results/` and writes per-robot and
per-simulation CSVs, Experiment I and II summary tables in CSV and Markdown,
three noise comparison bar charts, three-seed trajectory plots, trajectory
noise comparison plots, trajectory-deviation tables, and a validation report.
The CSV filename pattern and metadata must match the analyzer's expected
conditions; incomplete or missing runs are listed in the validation report.

In these CSVs, `collision_avoidance` is the reported `near_collision_count`
from the controller: a LiDAR-derived distance crossing the configured
threshold. It is not a Webots physical-contact signal or a measure of how
often avoidance was active. The analysis labels this as reported collision
events and derives configured avoidance from the filename.
