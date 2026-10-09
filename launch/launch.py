import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node
import webots_ros2_driver.utils as webots_utils
from webots_ros2_driver.webots_controller import WebotsController
from webots_ros2_driver.webots_launcher import WebotsLauncher


ROBOTS = ['epuck_1', 'epuck_2', 'epuck_3', 'epuck_4', 'epuck_5']


def generate_launch_description():
    package_dir = get_package_share_directory('ri_a1')
    robot_description_path = os.path.join(package_dir, 'resource', 'robot.urdf')
    ros2_control_params = os.path.join(package_dir, 'resource', 'robot.yml')
    world_path = os.path.join(package_dir, 'worlds', 'world.wbt')

    # Lire le CONTENU du fichier URDF (obligatoire pour robot_state_publisher)
    with open(robot_description_path, encoding='utf-8') as f:
        robot_description = f.read()

    # Fix WSL
    local_webots_home = '/usr/local/webots'
    if os.path.isfile(os.path.join(local_webots_home, 'webots')):
        configured_webots_home = os.environ.get('WEBOTS_HOME', '')
        configured_webots = os.path.join(configured_webots_home, 'webots')
        if not os.path.isfile(configured_webots):
            os.environ['ROS2_WEBOTS_HOME'] = local_webots_home

    webots_utils.is_wsl = lambda: False

    webots = WebotsLauncher(world=world_path)

    controller_manager_timeout = ['--controller-manager-timeout', '60']

    drivers = []
    rsp_nodes = []
    spawners = []
    control_nodes = []

    for robot in ROBOTS:
        # --- Driver Webots ---
        driver = WebotsController(
            robot_name=robot,
            namespace=robot,
            parameters=[{
                'robot_description': robot_description_path,  # chemin OK pour le driver
                'use_sim_time': False,
                'set_robot_state_publisher': False,
            }, ros2_control_params],
            remappings=[
                ('diffdrive_controller/cmd_vel', f'/{robot}/cmd_vel'),
                ('diffdrive_controller/odom', f'/{robot}/odom'),
            ],
            respawn=True,
        )
        drivers.append(driver)

        # --- robot_state_publisher par robot ---
        rsp = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            namespace=robot,
            output='screen',
            parameters=[{
                'robot_description': robot_description,   # <-- CONTENU, pas chemin
                'use_sim_time': False,
            }],
        )
        rsp_nodes.append(rsp)

        # --- Spawners ---
        diffdrive_spawner = Node(
            package='controller_manager',
            executable='spawner',
            output='screen',
            namespace=robot,
            arguments=['diffdrive_controller'] + controller_manager_timeout,
            parameters=[{'use_sim_time': False}],
        )
        joint_state_spawner = Node(
            package='controller_manager',
            executable='spawner',
            output='screen',
            namespace=robot,
            arguments=['joint_state_broadcaster'] + controller_manager_timeout,
            parameters=[{'use_sim_time': False}],
        )
        spawners.extend([diffdrive_spawner, joint_state_spawner])

        # --- Contrôleur de suivi ---
        control_node = Node(
            package='ri_a1',
            executable='controller',
            name=f'controleur_{robot}',
            output='screen',
            parameters=[{'robot_name': robot, 'use_sim_time': False}],
        )
        control_nodes.append(control_node)

    # Démarrage différé
    delayed_nodes = TimerAction(
        period=15.0,
        actions=rsp_nodes + spawners + control_nodes,
    )

    return LaunchDescription([
        webots,
        *drivers,
        delayed_nodes,
    ])
