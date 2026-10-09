#!/bin/bash
set -e

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$WS_DIR"

[ -z "$ROS_DISTRO" ] && source /opt/ros/jazzy/setup.bash
source install/setup.bash

echo ">>> Launch ri_a1"
ros2 launch ri_a1 launch.py