# CSV Logger

`csv_logger.py` records data from all five robots (`robot_0` to `robot_4`), including their Webots x/y positions.

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
- `run_exp.txt` is the manual run plan for those 18 configurations. It lists
  the logger commands, but the simulation configuration must also be set in
  `config/config.yaml` before launching each run.
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

1. Edit the simulation settings in `config/config.yaml`, then start a fresh
   simulation (see `../Readme.md` for the ROS 2 launch command). The logger
   flags do not apply these settings. Only `random_seed` is a supported launch
   override for the seed; noise and robot behaviour must be set in the loaded
   config file.
2. In another terminal, start `csv_logger.py` with matching metadata. For
   example:

   ```bash
   python3 src/RI_Assesment1/experiments/csv_logger.py \
     --seed 18 --noise 0.2 --source lidar --gain 1.5 \
     --following on --avoidance on
   ```

3. Stop the logger with **Ctrl+C** after the simulation. Repeat with each
   configuration in `run_exp.txt`.

The logger's `--seed`, `--noise`, `--source`, `--gain`, `--following`, and
`--avoidance` arguments describe the run in the CSV filename and metadata;
they do not change the active simulation configuration. Keep the logger
arguments and the config file actually loaded by ROS 2 in agreement. The logger opens
its matching CSV filename for writing, so running the same combination again
overwrites that file.

## Analyze the results

From the repository root, run:

```bash
python3 experiments/analyze_results.py
```

The analysis uses pandas, NumPy, and Matplotlib. It expects the 18 named CSVs
for seeds 18–20, reports missing or incomplete runs in
`experiments/analysis_results/validation_report.txt`, and writes plots at
300 DPI. It calculates following rate and angular error per robot before
averaging robots; cumulative target-loss and reported collision counters use
the final counter value per robot.

In these CSVs, `collision_avoidance` is the reported `near_collision_count`
from the controller: a LiDAR-derived distance crossing the configured
threshold. It is not a Webots physical-contact signal or a measure of how
often avoidance was active. The analysis labels this as reported collision
events and derives configured avoidance from the filename.
