from math import hypot
from random import Random
import re
from typing import Sequence


DEFAULT_SPAWN_ZONE = (-1.2, 1.2, -1.2, 1.2)
DEFAULT_MIN_ROBOT_DISTANCE = 0.25
DEFAULT_MAX_PLACEMENT_ATTEMPTS = 1000

_ROBOT_POSE = re.compile(
    r'(?P<indent>^[ \t]*)translation '
    r'(?P<old_x>[-+0-9.eE]+) (?P<old_y>[-+0-9.eE]+) (?P<z>[-+0-9.eE]+)'
    r'(?P<newline>\r?\n)'
    r'(?P=indent)rotation 0 0 1 [-+0-9.eE]+(?P<newline2>\r?\n)'
    r'(?P=indent)name "(?P<name>[^"]+)"',
    re.MULTILINE,
)


def generate_spawn_poses(
    robot_names: Sequence[str],
    rng: Random,
    spawn_zone: tuple[float, float, float, float] = DEFAULT_SPAWN_ZONE,
    min_robot_distance: float = DEFAULT_MIN_ROBOT_DISTANCE,
    max_attempts: int = DEFAULT_MAX_PLACEMENT_ATTEMPTS,
) -> dict[str, tuple[float, float, float]]:
    """Return non-overlapping ``(x, y, yaw)`` poses inside ``spawn_zone``."""
    min_x, max_x, min_y, max_y = spawn_zone
    poses: dict[str, tuple[float, float, float]] = {}

    for name in robot_names:
        for _ in range(max_attempts):
            x = rng.uniform(min_x, max_x)
            y = rng.uniform(min_y, max_y)
            if all(
                hypot(x - other_x, y - other_y) >= min_robot_distance
                for other_x, other_y, _ in poses.values()
            ):
                poses[name] = (
                    x, y,
                    rng.uniform(-3.141592653589793, 3.141592653589793),
                )
                break
        else:
            raise RuntimeError(
                f'Unable to place {name!r} in the configured spawn zone '
                f'after {max_attempts} attempts'
            )

    return poses


def randomize_world(
    world_content: str,
    poses: dict[str, tuple[float, float, float]],
) -> str:
    """Replace the translations and headings of named external robots."""
    found: set[str] = set()

    def replace_pose(match: re.Match[str]) -> str:
        name = match.group('name')
        if name not in poses:
            return match.group(0)
        x, y, yaw = poses[name]
        found.add(name)
        newline = match.group('newline')
        indent = match.group('indent')
        return (
            f'{indent}translation {x:.4f} {y:.4f} {match.group("z")}{newline}'
            f'{indent}rotation 0 0 1 {yaw:.4f}{match.group("newline2")}'
            f'{indent}name "{name}"'
        )

    result = _ROBOT_POSE.sub(replace_pose, world_content)
    missing = set(poses) - found
    if missing:
        raise ValueError(f'Robots not found in world: {sorted(missing)}')
    return result