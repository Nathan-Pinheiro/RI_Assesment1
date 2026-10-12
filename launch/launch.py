import os
import tempfile
from random import Random

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController

from ri_a1.spawn import generate_spawn_poses, randomize_world


ROBOT_NAMES = ['robot_0', 'robot_1', 'robot_2', 'robot_3', 'robot_4']


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'random_seed',
            default_value='42',
            description=(
                'Seed for reproducible spawn positions. '
                'Use -1 for a random seed at each launch.'
            ),
        ),
        OpaqueFunction(function=_launch_with_random_spawn),
    ])


def _launch_with_random_spawn(context):
    pkg = get_package_share_directory('ri_a1')
    world_path = os.path.join(pkg, 'worlds', 'world.wbt')
    urdf_path = os.path.join(pkg, 'resource', 'robot.urdf')

    with open(world_path, encoding='utf-8') as f:
        world_content = f.read()

    seed = int(LaunchConfiguration('random_seed').perform(context))
    rng = Random() if seed < 0 else Random(seed)

    poses = generate_spawn_poses(ROBOT_NAMES, rng)
    randomized_world = randomize_world(world_content, poses)

    # Remplace le chemin relatif du PROTO par un chemin absolu
    proto_abs = os.path.join(pkg, 'worlds', 'protos', 'TricycleRobot.proto')
    randomized_world = randomized_world.replace(
        'EXTERNPROTO "protos/TricycleRobot.proto"',
        f'EXTERNPROTO "{proto_abs}"',
    )

    tmp = tempfile.NamedTemporaryFile(
        mode='w',
        prefix='ri_a1_random_',
        suffix='.wbt',
        encoding='utf-8',
        delete=False,
    )
    with tmp:
        tmp.write(randomized_world)
    world_path = tmp.name

    for name, (x, y, yaw) in poses.items():
        print(f'[spawn] {name}: x={x:.3f} y={y:.3f} yaw={yaw:.3f}')

    webots = WebotsLauncher(world=world_path)

    actions = [webots]

    for name in ROBOT_NAMES:
        robot = WebotsController(
            robot_name=name,
            parameters=[{'robot_description': urdf_path}],
            output='screen',
        )
        actions.append(robot)

    return actions