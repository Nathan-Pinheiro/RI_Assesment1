import sys
import math
import random
import time
import atexit

import numpy as np

from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray

from ri_a1.config import load_config


DEFAULTS = {
    'wheel_noise': False,
    'lidar_noise': False,
    'strength': 0.2,

    'seed': 43,
    'seuil': 50,
    'dist_stop': 0.1,
    'dist_slow': 0.5,
    'max_speed': 5.0,
    'min_speed': 1.0,
    'turn_gain': 2.5,
    'cruise_speed': 3.75,
    'cruise_curvature': 0.5 / 7.5,
    'reverse_turn': False,
    'sensor_angles_deg': [-50, -40, -30, -20, -10, 0,
                          10, 20, 30, 40, 50],
    'lookup': [
        [0.0,  1024],
        [0.05, 1000],
        [0.5,  800],
        [1.0,  600],
        [2.0,  300],
        [3.0,  120],
        [4.0,  0],
    ],
    'cmd_vel_timeout': 1.0,
}


def _normalize_layer(layer, label):
    layer = dict(layer or {})
    left = layer.pop('cruise_l', None)
    right = layer.pop('cruise_r', None)
    if left is None and right is None:
        return layer
    if left is None or right is None:
        print(f'[config] {label}: cruise_l et cruise_r doivent aller '
              f'ensemble, ignorés', file=sys.stderr, flush=True)
        return layer
    total = float(left) + float(right)
    layer.setdefault('cruise_speed', total / 2.0)
    layer.setdefault('cruise_curvature',
                     (float(left) - float(right)) / total if total else 0.0)
    return layer


def build_robot_config(cfg_full, name):
    cfg = dict(DEFAULTS)
    if 'seed' in cfg_full:
        cfg['seed'] = cfg_full['seed']
    noise = cfg_full.get('noise')
    if isinstance(noise, dict):
        for k in ('wheel_noise', 'lidar_noise', 'strength'):
            if k in noise:
                cfg[k] = noise[k]
    per_robot = (cfg_full.get('robots') or {}).get(name)
    if per_robot is None and cfg_full.get('robots'):
        print(f'[{name}] pas de section dans robots:, valeurs par défaut',
              file=sys.stderr, flush=True)
    for label, layer in (('robot', cfg_full.get('robot')),
                         (f'robots.{name}', per_robot)):
        layer = _normalize_layer(layer, label)
        unknown = set(layer) - set(DEFAULTS)
        if unknown:
            print(f'[config] {label}: clés inconnues {sorted(unknown)}',
                  file=sys.stderr, flush=True)
        cfg.update(layer)
    return cfg


def _acquire_ros_node(webots_node, name):
    for attr in (None, 'ros_node', '_node', '_ros_node', 'node', 'get_node'):
        obj = webots_node if attr is None else getattr(webots_node, attr, None)
        if obj is None:
            continue
        if callable(obj) and attr == 'get_node':
            try:
                obj = obj()
            except Exception:
                continue
        if hasattr(obj, 'create_publisher'):
            return obj, False

    try:
        import rclpy
        from rclpy.node import Node
        if not rclpy.ok():
            rclpy.init()
        node = Node(f'{name}_control')
        print(f'[{name}] WebotsNode has no rclpy Node, created "{name}_control"',
              file=sys.stderr, flush=True)
        return node, True
    except Exception as e:
        print(f'[{name}] cannot create fallback node: {e!r}',
              file=sys.stderr, flush=True)
        return None, False


class MyRobotDriver:

    def init(self, webots_node, properties):
        self.__sensor_pub = None
        self.__cmd_sub = None
        self.__wheel_pub = None
        self.__sensors = []
        self.__last_cmd_time = -1e9
        self.__cmd_left  = 0.0
        self.__cmd_right = 0.0
        self.__ready = False
        self.__owns_node = False
        self.__spin_warned = False
        self.__shutdown_registered = False

        self.following = False
        self.angular_error = float("nan")
        self.target_losses = 0
        self.previous_following = False
        self.near_collision_count = 0
        self.previous_near_collision = False

        self.__robot = webots_node.robot
        self.__name = self.__robot.getName()
        self.gps = self.__robot.getDevice("gps")
        self.gps.enable(32)

        self.__node, self.__owns_node = _acquire_ros_node(webots_node, self.__name)

        cfg = build_robot_config(load_config(), self.__name)

        self.wheel_noise = bool(cfg["wheel_noise"])
        self.lidar_noise = bool(cfg["lidar_noise"])
        self.noise_s = float(cfg["strength"])

        self.SEED              = int(cfg['seed'])
        self.SEUIL             = int(cfg['seuil'])
        self.DIST_STOP         = float(cfg['dist_stop'])
        self.DIST_SLOW         = float(cfg['dist_slow'])
        self.MAX_SPEED         = float(cfg['max_speed'])
        self.MIN_SPEED         = float(cfg['min_speed'])
        self.TURN_GAIN         = float(cfg['turn_gain'])
        self.CRUISE_SPEED      = float(cfg['cruise_speed'])
        self.CRUISE_CURVATURE  = float(cfg['cruise_curvature'])
        self.CRUISE_L = min(self.MAX_SPEED,
                            self.CRUISE_SPEED * (1.0 + self.CRUISE_CURVATURE))
        self.CRUISE_R = min(self.MAX_SPEED,
                            self.CRUISE_SPEED * (1.0 - self.CRUISE_CURVATURE))
        self.REVERSE_TURN      = bool(cfg['reverse_turn'])
        self.SENSOR_ANGLES_DEG = list(cfg['sensor_angles_deg'])
        self.LOOKUP            = [tuple(p) for p in cfg['lookup']]
        self.CMD_VEL_TIMEOUT   = float(cfg['cmd_vel_timeout'])
        self.__sin_angles = [math.sin(math.radians(a))
                             for a in self.SENSOR_ANGLES_DEG]

        robot_index = 0
        if '_' in self.__name:
            try:
                robot_index = int(self.__name.rsplit('_', 1)[1])
            except ValueError:
                robot_index = 0
        self.__rng = random.Random(self.SEED + robot_index)

        if self.__node is not None:
            try:
                self.__sensor_pub = self.__node.create_publisher(
                    Float32MultiArray,
                    f'/{self.__name}/sensor_readings', 10)
                
                self.__wheel_pub = self.__node.create_publisher(
                    Float32MultiArray,
                    f'/{self.__name}/wheel_speeds',
                    10
                )
                self.__cmd_sub = self.__node.create_subscription(
                    Twist, f'/{self.__name}/cmd_vel',
                    self.__on_cmd_vel, 10)
                print(f'[{self.__name}] ROS2 pub/sub OK '
                      f'(own_node={self.__owns_node})', flush=True)
            except Exception as e:
                print(f'[{self.__name}] ROS2 pub/sub FAILED: {e!r} '
                      f'(autonomous mode only)',
                      file=sys.stderr, flush=True)
                self.__sensor_pub = None
                self.__cmd_sub = None

        self.__left_motor  = self.__robot.getDevice('left wheel motor')
        self.__right_motor = self.__robot.getDevice('right wheel motor')
        if self.__left_motor is None or self.__right_motor is None:
            print(f'[{self.__name}] ERROR: motor(s) introuvable(s) '
                  f'left={self.__left_motor} right={self.__right_motor}',
                  file=sys.stderr, flush=True)
            return
        self.__left_motor.setPosition(float('inf'))
        self.__right_motor.setPosition(float('inf'))
        self.__left_motor.setVelocity(0.0)
        self.__right_motor.setVelocity(0.0)

        for i in range(len(self.SENSOR_ANGLES_DEG)):
            s = self.__robot.getDevice(f'ds_{i}')
            if s is None:
                print(f'[{self.__name}] ds_{i} INTROUVABLE',
                      file=sys.stderr, flush=True)
            else:
                s.enable(32)
                self.__sensors.append(s)

        if self.__owns_node and not self.__shutdown_registered:
            atexit.register(self.__shutdown_own)
            self.__shutdown_registered = True

        self.__ready = True
        print(f'[{self.__name}] init OK '
              f'({len(self.__sensors)} capteurs, seuil={self.SEUIL}, '
              f'speed={self.CRUISE_SPEED:.2f}, '
              f'curvature={self.CRUISE_CURVATURE:+.3f}, '
              f'L={self.CRUISE_L:.2f}, R={self.CRUISE_R:.2f}, '
              f'wheel_noise={self.wheel_noise}, '
              f'lidar_noise={self.lidar_noise}, '
              f'cmd_vel_timeout={self.CMD_VEL_TIMEOUT:.1f}s wall)',
              file=sys.stderr, flush=True)

    def __shutdown_own(self):
        try:
            import rclpy
            if not rclpy.ok():
                return
            try:
                if self.__cmd_sub is not None:
                    self.__node.destroy_subscription(self.__cmd_sub)
            except Exception:
                pass
            try:
                if self.__sensor_pub is not None:
                    self.__node.destroy_publisher(self.__sensor_pub)
            except Exception:
                pass
            try:
                self.__node.destroy_node()
            except Exception:
                pass
        except Exception:
            pass

    def __on_cmd_vel(self, msg):
        mean = float(msg.linear.x)
        diff = float(msg.angular.z)
        self.__cmd_left  = mean - diff
        self.__cmd_right = mean + diff
        self.__last_cmd_time = time.monotonic()

    def __set(self, l, r):
        if self.wheel_noise:
            l += float(np.random.normal(0.0, self.noise_s))
            r += float(np.random.normal(0.0, self.noise_s))
        m = self.MAX_SPEED

        left_speed = max(-m, min(m, l))
        right_speed = max(-m, min(m, r))

        self.__left_motor.setVelocity(left_speed)
        self.__right_motor.setVelocity(right_speed)

        # Publish wheel commands for logging
        if self.__wheel_pub is not None:
            msg = Float32MultiArray()

            msg.data = [
                float(self.__robot.getTime()),
                float(left_speed),
                float(right_speed),
                float(self.following),
                float(self.angular_error),
                float(self.target_losses),
                float(self.near_collision_count),
                self.__gps_x,
                self.__gps_y
            ]

            self.__wheel_pub.publish(msg)

    def __reading_to_distance(self, v):
        if v <= 0:
            return 4.0
        for i in range(len(self.LOOKUP) - 1):
            d1, v1 = self.LOOKUP[i]
            d2, v2 = self.LOOKUP[i + 1]
            if v1 >= v >= v2:
                if v1 == v2:
                    return d1
                t = (v1 - v) / (v1 - v2)
                d = d1 + t * (d2 - d1)
                if self.lidar_noise:
                    d += float(np.random.normal(0.0, self.noise_s))
                return d
        return 4.0

    def step(self):
        if not self.__ready:
            return

        position = self.gps.getValues()
        self.__gps_x = float(position[0])
        self.__gps_y = float(position[1])

        if self.__owns_node and self.__node is not None:
            try:
                import rclpy
                rclpy.spin_once(self.__node, timeout_sec=0)
            except Exception as e:
                if not self.__spin_warned:
                    print(f'[{self.__name}] spin_once failed: {e!r}',
                          file=sys.stderr, flush=True)
                    self.__spin_warned = True

        d = [s.getValue() for s in self.__sensors]
        max_d = max(d) if d else 0

        # 1. Following state
        self.following = max_d >= self.SEUIL

        # 2. Angular error
        if self.following:
            nearest = d.index(max_d)

            self.angular_error = abs(
                self.SENSOR_ANGLES_DEG[nearest]
            )
        else:
            self.angular_error = float("nan")

        # 3. Target losses
        if self.previous_following and not self.following:
            self.target_losses += 1

        # Store state for next timestep
        self.previous_following = self.following

        if self.__sensor_pub is not None:
            msg = Float32MultiArray()
            msg.data = [float(x) for x in d]
            self.__sensor_pub.publish(msg)

        if time.monotonic() - self.__last_cmd_time < self.CMD_VEL_TIMEOUT:
            self.previous_near_collision = False
            self.__set(self.__cmd_left, self.__cmd_right)
            return

        if max_d < self.SEUIL:
            self.previous_near_collision = False
            self.__set(self.CRUISE_L, self.CRUISE_R)
            return

        dist = self.__reading_to_distance(max_d)

        # Collision logging
        near_collision = dist <= self.DIST_STOP
        if near_collision and not self.previous_near_collision:
            self.near_collision_count += 1
        self.previous_near_collision = near_collision

        if dist <= self.DIST_STOP:
            self.__set(-2, 2)
            return
        elif dist < self.DIST_SLOW:
            t = (dist - self.DIST_STOP) / (self.DIST_SLOW - self.DIST_STOP)
            speed = max(self.MAX_SPEED * t, self.MIN_SPEED * 0.3)
        else:
            speed = self.MAX_SPEED

        nearest = d.index(max_d)
        bearing = math.radians(self.SENSOR_ANGLES_DEG[nearest])
        turn = math.sin(bearing)

        diff = self.TURN_GAIN * turn * speed
        if self.REVERSE_TURN:
            diff = -diff

        left  = max(0.0, min(self.MAX_SPEED, speed - diff))
        right = max(0.0, min(self.MAX_SPEED, speed + diff))
        self.__set(left, right)
