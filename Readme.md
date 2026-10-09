# ri_a1 — ROS 2 + Webots Project

ROS 2 (ament_python) project for simulating and controlling a swarm of e-puck robots in Webots.
The `ri_a1` package contains the robot controller plugin, the launch file, the URDF model and the Webots world.

---

## Requirements

- **Ubuntu** 22.04 or 24.04
- **ROS 2** Jazzy (adjust `$ROS_DISTRO` if you use another distro)
- **Webots** (R2023b recommended with `webots_ros2`; R2025a may work but is not officially supported)
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
ri_a1/
├── commands/
│   ├── build.sh                # Build only
│   ├── run.sh                  # Run only
│   └── build_and_run.sh        # Build then run
├── launch/
│   └── launch.py               # Main launch file (Webots + 5 controllers)
├── ri_a1/                      # Python package
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
git clone <repo-url> ri_a1
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

This starts Webots with `world.wbt` and connects one `WebotsController` per e-puck (`epuck_1` … `epuck_5`).

---

## Helper scripts

Three scripts are provided in `commands/` to simplify the workflow.
Make them executable once:

```bash
chmod +x ~/ros2_ws/src/ri_a1/commands/*.sh
```

Then, from the repo root (`ri_a1/`):

```bash
./commands/build.sh          # Build only
./commands/run.sh            # Run only (assumes a previous build)
./commands/build_and_run.sh  # Build then run
```

Each script automatically locates the workspace root, so it can be called from anywhere.

---

## Check that the nodes are running

In a second terminal:

```bash
source ~/ros2_ws/install/setup.bash
ros2 node list
ros2 topic list
```

Expected:

```
/epuck_1/epuck_1
/epuck_2/epuck_2
...
```

Topics:

```
/epuck_1/cmd_vel
/epuck_2/cmd_vel
...
```

### Useful commands

```bash
# View published topics
ros2 topic echo /epuck_1/cmd_vel

# Drive one robot forward
ros2 topic pub -r 10 /epuck_1/cmd_vel geometry_msgs/msg/TwistStamped \
  "{twist: {linear: {x: 0.05}, angular: {z: 0.0}}}"

# Make every robot spin on the spot
for i in 1 2 3 4 5; do
  ros2 topic pub -r 10 /epuck_$i/cmd_vel geometry_msgs/msg/TwistStamped \
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