# RI Assessment 1 — Multi-robot Webots simulation

ROS 2 package for simulating and controlling five tricycle robots in Webots.
The package generates a randomized spawn layout, starts one Webots controller
per robot, publishes distance-sensor readings, and accepts velocity commands
through ROS 2 topics.

## Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Build](#build)
- [Run the simulation](#run-the-simulation)
- [Launch arguments](#launch-arguments)
- [Helper scripts](#helper-scripts)
- [Configuration](#configuration)
- [ROS 2 interfaces](#ros-2-interfaces)
- [Project structure](#project-structure)
- [Development](#development)
- [Authors and contributors](#authors-and-contributors)
- [License](#license)

## Features

- Five robots (`robot_0` through `robot_4`) in a Webots world.
- Random, non-overlapping robot placement at startup.
- Configurable random seed, obstacle avoidance, speed, curvature, and noise.
- ROS 2 control topics for each robot.
- Optional headless and accelerated Webots modes.
- Support for launching Webots on the host while ROS 2 runs in a VM, when
  `webots_ros2_driver` shared-folder mode is configured.

## Prerequisites

The project is intended for a Linux ROS 2 workspace and Webots R2025a.

Install:

- ROS 2 (the distribution matching the `webots_ros2` installation).
- Webots R2025a.
- `colcon` and the ROS 2 Webots driver:

  ```bash
  sudo apt update
  sudo apt install python3-colcon-common-extensions
  sudo apt install ros-$ROS_DISTRO-webots-ros2
  ```

`ROS_DISTRO` must be set before running the second command. For example:

```bash
source /opt/ros/jazzy/setup.bash
echo "$ROS_DISTRO"
```

The helper scripts use `/opt/ros/jazzy/setup.bash` when no ROS environment is
already sourced. If another distribution is installed, source it explicitly
before using the scripts.

## Installation

Create a workspace and clone the repository into its `src` directory:

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/Nathan-Pinheiro/RI_Assesment1.git RI_Assesment1
```

## Build

Source ROS 2, build the package, then source the generated workspace:

```bash
cd ~/ros2_ws
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --packages-select ri_a1 --symlink-install
source install/setup.bash
```

The `--symlink-install` option makes changes to Python, launch, YAML, and
world files available without copying them into the install space. Rebuild
after changing package metadata or adding files that must be installed.

## Run the simulation

After building and sourcing the workspace:

```bash
ros2 launch ri_a1 launch.py
```

This command:

1. Reads `config/config.yaml`.
2. Generates a randomized copy of `worlds/world.wbt`.
3. Starts Webots and five `WebotsController` instances.
4. Removes the generated world when the launch process shuts down.

To verify that the package is available before launching:

```bash
ros2 pkg prefix ri_a1
ros2 launch ri_a1 launch.py --show-args
```

### Webots on another machine or in a VM

For a VM running ROS 2 and a host running Webots, configure
`webots_ros2_driver`'s shared-folder mode first. The shared directory must be
writable from the VM and visible to Webots on the host. Then set the shared
folder in the ROS 2 environment and launch the package:

```bash
export WEBOTS_SHARED_FOLDER=/path/to/shared/folder
source /opt/ros/$ROS_DISTRO/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch ri_a1 launch.py
```

The launch file keeps the generated world next to
`worlds/protos/TricycleRobot.proto`, so the relative PROTO path remains valid
in shared-folder mode. Follow the `webots_ros2_driver` documentation for the
host-side simulation server and its TCP port.

## Launch arguments

The launch file provides the following arguments:

| Argument | Default | Description |
| --- | --- | --- |
| `random_seed` | Empty | Overrides `seed` from `config/config.yaml`. |
| `mode` | `realtime` | Webots mode: `realtime`, `fast`, or `pause`. |
| `gui` | `true` | Set to `false` for headless execution. |

Examples:

```bash
# Repeatable spawn layout with a specific seed
ros2 launch ri_a1 launch.py random_seed:=45

# Run without Webots rendering
ros2 launch ri_a1 launch.py gui:=false

# Run as fast as possible
ros2 launch ri_a1 launch.py mode:=fast
```

## Helper scripts

The `commands/` directory contains scripts for the common workflow. Make them
executable once:

```bash
cd ~/ros2_ws/src/RI_Assesment1
chmod +x commands/*.sh
```

Use them from the repository root or from another directory:

```bash
./commands/build.sh
./commands/run.sh
./commands/build_and_run.sh
```

- `build.sh` removes this package's previous build and install directories,
  then rebuilds it.
- `run.sh` launches the simulation and requires a successful build.
- `build_and_run.sh` rebuilds the package, sources the workspace, and launches
  the simulation.
- `setup_gpu.sh` configures Mesa D3D12 GPU acceleration for WSL2 only. On
  native Linux, Webots normally uses the system GPU directly:

  ```bash
  ./commands/setup_gpu.sh
  source ~/.bashrc
  ```

The build and run scripts locate the workspace from the repository path. They
fall back to Jazzy only when `ROS_DISTRO` is not already set; source the
desired ROS 2 distribution first when using another distribution.

## Configuration

Runtime settings are stored in
[`config/config.yaml`](config/config.yaml). The main sections are:

- `seed`: spawn and controller seed. A negative value creates a new spawn
  layout on every launch.
- `spawn`: spawn area, minimum distance, and placement-attempt limit.
- `noise`: global noise settings.
- `robot`: defaults shared by all robots.
- `robots`: optional per-robot overrides.

For example:

```yaml
robot:
  cruise_speed: 3.75
  cruise_curvature: 0.0667

robots:
  robot_1:
    cruise_speed: 3.0
    cruise_curvature: 0.10
```

Wheel speeds are calculated as follows:

```text
left  = cruise_speed * (1 + cruise_curvature)
right = cruise_speed * (1 - cruise_curvature)
```

The values are capped by `max_speed`. The legacy `cruise_l` and `cruise_r`
configuration keys are also accepted as a pair.

## ROS 2 interfaces

Once the simulation is running, inspect the available nodes and topics:

```bash
source ~/ros2_ws/install/setup.bash
ros2 node list
ros2 topic list
```

Each robot exposes:

- `/<robot_name>/cmd_vel`
  (`geometry_msgs/msg/Twist`) — velocity commands.
- `/<robot_name>/sensor_readings`
  (`std_msgs/msg/Float32MultiArray`) — distance-sensor readings.

Example commands:

```bash
# Move robot_0 forward
ros2 topic pub -r 10 /robot_0/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.05}, angular: {z: 0.0}}"

# Rotate robot_0 in place
ros2 topic pub -r 10 /robot_0/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 1.0}}"
```

The controller applies `cmd_vel_timeout` from the configuration. Stop
publishing before that timeout expires and the robot returns to its autonomous
behaviour.

Expected controller nodes are:

```text
/robot_0/robot_0
/robot_1/robot_1
/robot_2/robot_2
/robot_3/robot_3
/robot_4/robot_4
```

`ri_a1/controller.py` is a Webots plugin loaded by
`webots_ros2_driver`; it is not a standalone executable. Therefore,
`ros2 run ri_a1 controller` is not a valid way to start the controller.

## Project structure

```text
RI_Assesment1/
├── commands/                 # Build, run, and WSL2 GPU helper scripts
├── config/config.yaml       # Runtime and per-robot configuration
├── launch/launch.py         # Webots and controller launch description
├── resource/
│   ├── ri_a1                # ROS 2 package resource marker
│   ├── robot.urdf           # Robot description and Webots plugin entry point
│   └── ...
├── ri_a1/
│   ├── config.py            # Configuration loading and merging
│   ├── controller.py        # Webots ROS 2 controller plugin
│   └── spawn.py             # Spawn pose and world generation helpers
├── worlds/
│   ├── world.wbt            # Webots world
│   └── protos/              # Custom Webots PROTO definitions
├── package.xml
├── setup.py
└── setup.cfg
```

## Development

The package uses `ament_python`. With `--symlink-install`, changes to Python,
launch, configuration, and world files are picked up from the source tree.
Rebuild when changing `package.xml`, `setup.py`, installation data, or adding
new package files:

```bash
cd ~/ros2_ws
colcon build --packages-select ri_a1 --symlink-install
source install/setup.bash
```

Useful source files:

- [`ri_a1/controller.py`](ri_a1/controller.py)
- [`ri_a1/config.py`](ri_a1/config.py)
- [`ri_a1/spawn.py`](ri_a1/spawn.py)
- [`launch/launch.py`](launch/launch.py)
- [`resource/robot.urdf`](resource/robot.urdf)
- [`worlds/world.wbt`](worlds/world.wbt)

## Authors and contributions

Here bellow are the members of this RI Assessment 1 project :

| LASTNAME | Firstname | Contributions
|----------|-----------|--------------
| PINHEIRO | Nathan    | Initialization of the ROS 2 project, creation of the robot models, implementation of basic locomotion (curvature and turning), and some writing in the article.
| JOHANSEN | Magnus    | Implementation of LiDAR and wheel noise, data logging and analysis, result visualization, and some writing in the article.
| SANTOS   | Júlio     | Contributed to locomation logic, ensuring speed and curvature for each robot. Also contributed to the article in some sections and edit the video
| COLOMBU  | Jules     | Setup of the project and of the simulation principles, implementation of the basics for controller/yaml/world, formating the readme