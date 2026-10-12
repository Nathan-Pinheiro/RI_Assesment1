import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController


ROBOT_NAMES = ['robot_0', 'robot_1', 'robot_2', 'robot_3', 'robot_4']


def generate_launch_description():
    pkg = get_package_share_directory('ri_a1')
    world_path = os.path.join(pkg, 'worlds', 'world.wbt')
    urdf_path = os.path.join(pkg, 'resource', 'robot.urdf')

    webots = WebotsLauncher(world=world_path)

    ld = LaunchDescription()
    ld.add_action(webots)

    for name in ROBOT_NAMES:
        robot = WebotsController(
            robot_name=name,
            parameters=[{'robot_description': urdf_path}],
            output='screen',  # <-- ajoute ça pour voir les logs de chaque robot
        )
        ld.add_action(robot)

    return ld