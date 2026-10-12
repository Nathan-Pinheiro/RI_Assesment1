# ri_a1 — ROS 2 + Webots Project

ROS 2 Humble (ament_python) project for simulating and controlling five tricycle robots in Webots R2025a.
The `ri_a1` package contains the robot controller plugin, the launch file, the URDF model and the Webots world.

---

## Requirements

- **Ubuntu** 22.04
- **ROS 2** Humble
- **Webots** R2025a
- `webots_ros2` :
  ```bash
  sudo apt install ros-$ROS_DISTRO-webots-ros2
  ```
- `colcon` :
  ```bash
  sudo apt install python3-colcon-common-extensions
  ```

---

## Project structure

```
RI_Assesment1/
├── commands/                   # Here are the commands to build/run.
│   ├── build.sh
│   ├── run.sh
│   └── build_and_run.sh
├── launch/                     # Contains file for launching
│   └── launch.py
├── ri_a1/                      # Here are all the python files
│   ├── __init__.py
│   └── controller.py           # Webots plugin controlling each e-puck
├── resource/
│   ├── ri_a1
│   ├── robot.urdf              # Robot URDF description
│   └── robot.yml               # ros2_control parameters
├── worlds/
│   └── world.wbt               # Webots world (5 e-pucks, extern controllers)
├── package.xml
├── setup.py
├── setup.cfg
├── LICENSE
└── README.md
```

---

## Installation

### 1. Clone into a ROS 2 workspace

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone <repo-url> RI_Assesment1
```

### 2. Build

```bash
cd ~/ros2_ws
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --packages-select ri_a1 --symlink-install
source install/setup.bash
```

---

## Launch

```bash
ros2 launch ri_a1 launch.py
```

This starts the randomized world and connects one `WebotsController` for each robot (`robot_0` … `robot_4`).

### Ubuntu and Webots on the same machine

Source ROS 2 and the workspace, then launch normally:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch ri_a1 launch.py
```

### Ubuntu VM with Webots on macOS

Install `webots_ros2_driver` in the VM and Webots R2025a on macOS. Configure
`WEBOTS_SHARED_FOLDER` on both sides to the shared directory used by
`local_simulation_server.py`, and ensure the VM can reach the server's TCP
port. Start the server on macOS using the command supplied by your
`webots_ros2_driver` installation, for example:

```bash
python3 local_simulation_server.py --port 1234
```

Then, in the VM, export the shared-folder path and launch:

```bash
export WEBOTS_SHARED_FOLDER=/path/to/the/shared/folder
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch ri_a1 launch.py
```

The shared folder must be writable by the VM and visible to the native Mac
Webots process. The launch file keeps the generated world beside the packaged
`worlds/protos/` directory, allowing `WebotsLauncher` to transfer
`TricycleRobot.proto` automatically; no source-code path changes are needed
for either machine.

---

## Helper scripts

Three scripts are provided in `commands/` to simplify the workflow.
Make them executable once:

```bash
chmod +x ~/ros2_ws/src/RI_Assesment1/commands/*.sh
```

Then, from the repo root (`RI_Assesment1/`):

```bash
./commands/build.sh          # Build only
./commands/run.sh            # Run only (assumes a previous build)
./commands/build_and_run.sh  # Build then run
```

Each script automatically locates the workspace root, so it can be called from anywhere.


## Use your GPU

by default, the webot use the CPU, which is bad. This script will make it use the GPU

```bash
cd ~/ros2_ws/src/RI_Assesment1
chmod +x commands/*.sh
./commands/setup_gpu.sh
```

---

## Per-robot tuning

Cruise behaviour (when no obstacle is detected) is set in `config/config.yaml`:

- `robot:` holds the defaults shared by every robot.
- `robots:` is optional and keyed by robot name (`robot_0` … `robot_4`). Only the keys listed there override the defaults.

```yaml
robot:
  cruise_speed: 3.75       # mean wheel speed (rad/s)
  cruise_curvature: 0.0667 # (L-R)/(L+R): >0 curves right, <0 curves left, 0 = straight

robots:
  robot_1: { cruise_speed: 3.0, cruise_curvature: 0.10 }
```

Wheel speeds are `L = speed·(1+curvature)` and `R = speed·(1−curvature)`, capped at `max_speed`.
Each robot draws its path on the floor with a pen in its own colour (`trail: true` in `robot:`, or per robot in `robots:`; set `false` to disable). Ink never evaporates, so restart the simulation to clear it.
The legacy `cruise_l` / `cruise_r` pair is still accepted and converted. Each robot logs its effective values at start (`init OK ... speed=... curvature=...`).

---

## Check that the nodes are running

In a second terminal:

```bash
source ~/ros2_ws/install/setup.bash
ros2 node list
ros2 topic list
```

Expected robot nodes:

```
/robot_0/robot_0
/robot_1/robot_1
/robot_2/robot_2
/robot_3/robot_3
/robot_4/robot_4
```

Topics:

```
/robot_0/cmd_vel
/robot_1/cmd_vel
...
```

### Useful commands

```bash
# Confirm all five controller connections
for i in 0 1 2 3 4; do ros2 node list | grep -q "/robot_${i}" && echo "robot_${i}: connected"; done

# View published topics
ros2 topic list | grep robot_

# Drive one robot forward
ros2 topic pub -r 10 /robot_0/cmd_vel geometry_msgs/msg/TwistStamped \
  "{twist: {linear: {x: 0.05}, angular: {z: 0.0}}}"

# Make every robot spin on the spot
for i in 0 1 2 3 4; do
  ros2 topic pub -r 10 /robot_$i/cmd_vel geometry_msgs/msg/TwistStamped \
    "{twist: {linear: {x: 0.0}, angular: {z: 1.0}}}" &
done
wait
```

---

## Development

- Python controller: `ri_a1/controller.py` (Webots plugin, called by `webots_ros2_driver`)
- Webots world: `worlds/world.wbt`
- URDF: `resource/robot.urdf`
- Launch: `launch/launch.py`

Because the build uses `--symlink-install`, changes to Python files, launch files, and world files are picked up without rebuilding.
You only need to rebuild when modifying `package.xml`, `setup.py`, `entry_points`, or adding new files:

```bash
cd ~/ros2_ws
colcon build --packages-select ri_a1 --symlink-install
source install/setup.bash
```

---

## Notes on the Webots plugin

`controller.py` is **not** a standalone ROS 2 node — it is a plugin loaded by `webots_ros2_driver` via the `<plugin>` tag in `robot.urdf`:

```xml
<webots>
  <plugin type="ri_a1.controller.Controller" />
</webots>
```

The driver instantiates one `Controller` per robot declared in the world. That is why `ros2 run ri_a1 controller` is not applicable — the plugin runs inside the Webots controller process started by the launch file.

---

## License

See the [LICENSE](LICENSE) file.
