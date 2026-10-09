# Robotic Intelligents - Assesment 1

The objective of this Assesment is to make a simulation containing 5 bots, with a single reactive controller.

---

## Project structure

```
ri_a1/
├── commands/                   # Here are the commands to build/run.
│   ├── build.sh
│   ├── run.sh
│   └── build_and_run.sh
├── launch/                     # Contains file for launching
│   └── launch.py
├── ri_a1/                      # Here are all the python files
│   ├── __init__.py
│   └── controller.py           # The unique reactive controller for all bots
├── resource/
│   ├── ri_a1
│   └── robot.urdf              # Robot URDF description
├── worlds/
│   └── world.wbt               # The world, flat with 5 bots
├── package.xml
├── setup.py
├── setup.cfg
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
ros2 topic pub -r 10 /epuck_1/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.05}, angular: {z: 0.0}}"

# Make every robot spin on the spot
for i in 1 2 3 4 5; do
  ros2 topic pub -r 10 /epuck_$i/cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: 0.0}, angular: {z: 1.0}}" &
done
wait
```

---