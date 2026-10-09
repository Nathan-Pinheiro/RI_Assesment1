import os

from launch import LaunchDescription
from ament_index_python.packages import get_package_share_directory
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController


def generate_launch_description():
    package_dir = get_package_share_directory('ri_a1')

    world = os.path.join(package_dir, 'worlds', 'world.wbt')
    urdf = os.path.join(package_dir, 'resource', 'robot.urdf')
    webots = WebotsLauncher(world=world)

    robots = []
    for i in range(1, 6):
        robot = WebotsController(
            robot_name=f'epuck_{i}',
            parameters=[{'robot_description': urdf}],
            namespace=f'epuck_{i}',
        )
        robots.append(robot)

    return LaunchDescription([webots, *robots])