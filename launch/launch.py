import os
from random import Random

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController

from ri_a1.config import load_config
from ri_a1.spawn import generate_spawn_poses, randomize_world


ROBOT_NAMES = ['robot_0', 'robot_1', 'robot_2', 'robot_3', 'robot_4']
GENERATED_WORLD = 'ri_a1_generated.wbt'


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'random_seed', default_value='',
            description='Override seed from config (int). Empty = config value.'),
        DeclareLaunchArgument(
            'mode', default_value='realtime',
            description='Webots start mode: realtime | fast | pause'),
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='false = headless (no rendering, fastest startup)'),
        OpaqueFunction(function=_launch_with_random_spawn),
    ])


def _launch_with_random_spawn(context):
    pkg = get_package_share_directory('ri_a1')
    world_dir = os.path.join(pkg, 'worlds')
    world_path = os.path.join(world_dir, 'world.wbt')
    urdf_path = os.path.join(pkg, 'resource', 'robot.urdf')

    cfg_full = load_config()
    cfg = cfg_full.get('spawn', {})

    seed = int(cfg_full.get('seed', 42))
    cli_seed = LaunchConfiguration('random_seed').perform(context)
    if cli_seed:
        seed = int(cli_seed)

    spawn_zone = (
        float(cfg.get('spawn_zone_x_min', -1.0)),
        float(cfg.get('spawn_zone_x_max', 1.0)),
        float(cfg.get('spawn_zone_y_min', -1.0)),
        float(cfg.get('spawn_zone_y_max', 1.0)),
    )
    min_dist = float(cfg.get('min_robot_distance', 0.25))
    max_attempts = int(cfg.get('max_placement_attempts', 1000))

    print(f'[spawn] seed={seed} zone={spawn_zone} min_dist={min_dist}')

    with open(world_path, encoding='utf-8') as f:
        world_content = f.read()

    rng = Random() if seed < 0 else Random(seed)
    poses = generate_spawn_poses(
        ROBOT_NAMES, rng, spawn_zone=spawn_zone,
        min_robot_distance=min_dist, max_attempts=max_attempts)
    randomized_world = randomize_world(world_content, poses)

    # Generated world stays beside worlds/protos/ (needed for relative PROTO
    # paths, incl. shared-folder mode). One fixed file name, overwritten at
    # each launch and removed at shutdown, so nothing piles up.
    generated = os.path.join(world_dir, GENERATED_WORLD)
    with open(generated, 'w', encoding='utf-8') as f:
        f.write(randomized_world)

    for name, (x, y, yaw) in poses.items():
        print(f'[spawn] {name}: x={x:.3f} y={y:.3f} yaw={yaw:.3f}')

    webots = WebotsLauncher(
        world=generated,
        mode=LaunchConfiguration('mode'),
        gui=LaunchConfiguration('gui').perform(context).lower() != 'false',
        ros2_supervisor=True,
    )

    # All controllers are declared in the same LaunchDescription, so ROS 2
    # spawns them in parallel with Webots. Each one blocks in the extern
    # connection until Webots is ready; Webots does not advance simulation
    # time until every synchronized extern robot has connected, so all robots
    # start moving at the same simulated instant.
    controllers = [
        WebotsController(
            robot_name=name,
            parameters=[{'robot_description': urdf_path}],
            output='screen',
        )
        for name in ROBOT_NAMES
    ]

    def _cleanup(*_):
        try:
            os.remove(generated)
        except OSError:
            pass

        return []

    return [
        webots,
        webots._supervisor,
        *controllers,
        RegisterEventHandler(
            event_handler=OnShutdown(on_shutdown=[OpaqueFunction(function=_cleanup)])
        ),
    ]
