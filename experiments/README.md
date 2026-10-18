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
python3 src/RI_Assesment1/experiments/csv_logger.py --seed 18 --noise 0.2
```

Set `--seed` and `--noise` to the values actually used by the simulation. The example values match the current `config/config.yaml`; if the seed is overridden at launch, use that seed instead.

Press **Ctrl+C** in the logger terminal to stop logging. CSV files are saved in `experiments/results/`.

## CSV columns

`simulation_time`, `robot_id`, `seed`, `noise_s`, `left_speed`, `right_speed`, `following`, `angular_error`, `target_losses`, `collision_avoidance`, `x`, `y`.

`x` and `y` are the robot's horizontal position coordinates in Webots.
