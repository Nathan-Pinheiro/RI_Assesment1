import os
import re
import tempfile
from random import Random

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController

from ri_a1.config import load_config
from ri_a1.spawn import generate_spawn_poses, randomize_world


ROBOT_NAMES = ['robot_0', 'robot_1', 'robot_2', 'robot_3', 'robot_4']


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'random_seed',
            default_value='',
            description='Override seed from config (int). Empty = use config value.',
        ),
        OpaqueFunction(function=_launch_with_random_spawn),
    ])


def _launch_with_random_spawn(context):
    pkg = get_package_share_directory('ri_a1')
    world_path = os.path.join(pkg, 'worlds', 'world.wbt')
    urdf_path = os.path.join(pkg, 'resource', 'robot.urdf')

    cfg_full = load_config()
    cfg = cfg_full.get('spawn', {})

    seed = int(cfg_full.get('seed', 42))
    cli_seed = LaunchConfiguration('random_seed').perform(context)
    if cli_seed:
        seed = int(cli_seed)

    spawn_zone = (
        float(cfg.get('spawn_zone_x_min', -1.2)),
        float(cfg.get('spawn_zone_x_max',  1.2)),
        float(cfg.get('spawn_zone_y_min', -1.2)),
        float(cfg.get('spawn_zone_y_max',  1.2)),
    )
    min_dist = float(cfg.get('min_robot_distance', 0.25))
    max_attempts = int(cfg.get('max_placement_attempts', 1000))

    print(f'[spawn] seed={seed} zone={spawn_zone} min_dist={min_dist}')

    with open(world_path, encoding='utf-8') as f:
        world_content = f.read()

    rng = Random() if seed < 0 else Random(seed)

    poses = generate_spawn_poses(
        ROBOT_NAMES, rng,
        spawn_zone=spawn_zone,
        min_robot_distance=min_dist,
        max_attempts=max_attempts,
    )
    randomized_world = randomize_world(world_content, poses)

    proto_abs = os.path.join(pkg, 'worlds', 'protos', 'TricycleRobot.proto')
    randomized_world = re.sub(
        r'EXTERNPROTO "[^"]*TricycleRobot\.proto"',
        f'EXTERNPROTO "{proto_abs}"',
        randomized_world,
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
    tmp_world_path = tmp.name

    for name, (x, y, yaw) in poses.items():
        print(f'[spawn] {name}: x={x:.3f} y={y:.3f} yaw={yaw:.3f}')

    webots = WebotsLauncher(world=tmp_world_path)

    actions = [webots]

    for name in ROBOT_NAMES:
        robot = WebotsController(
            robot_name=name,
            parameters=[{'robot_description': urdf_path}],
            output='screen',
        )
        actions.append(robot)

    return actions