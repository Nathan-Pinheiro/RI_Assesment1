#!/bin/bash
set -e

# commands/../../.. = ~/ros2_ws
WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$WS_DIR"

[ -z "$ROS_DISTRO" ] && source /opt/ros/jazzy/setup.bash

echo ">>> Nettoyage build/ri_a1 + install/ri_a1"
rm -rf build/ri_a1 install/ri_a1

echo ">>> Build ri_a1"
colcon build --packages-select ri_a1 --symlink-install

echo ">>> Build OK."