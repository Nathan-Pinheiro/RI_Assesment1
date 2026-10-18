import sys
import math
import random
import numpy as np

from ri_a1.config import load_config


DEFAULTS = {
    'wheel_noise': False, # Gaussian noise wheels
    'lidar_noise': False, # Gaussian noise lidar
    'strength': 0.6, # Varians

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
}

def _normalize_layer(layer, label):
    """Convert legacy cruise_l/cruise_r in a config layer to speed/curvature."""
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
    """DEFAULTS < robot: < robots[name]."""
    cfg = dict(DEFAULTS)
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


class MyRobotDriver:

    def init(self, webots_node, properties):
        self.__robot = webots_node.robot
        self.__name = self.__robot.getName()

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

        robot_index = 0
        if '_' in self.__name:
            try:
                robot_index = int(self.__name.rsplit('_', 1)[1])
            except ValueError:
                robot_index = 0
        random.seed(self.SEED + robot_index)

        self.__left_motor = self.__robot.getDevice('left wheel motor')
        self.__right_motor = self.__robot.getDevice('right wheel motor')
        self.__left_motor.setPosition(float('inf'))
        self.__right_motor.setPosition(float('inf'))
        self.__left_motor.setVelocity(0.0)
        self.__right_motor.setVelocity(0.0)

        n = len(self.SENSOR_ANGLES_DEG)
        self.__sensors = []
        for i in range(n):
            s = self.__robot.getDevice(f'ds_{i}')
            if s is None:
                print(f'[{self.__name}] ds_{i} INTROUVABLE',
                      file=sys.stderr, flush=True)
            else:
                s.enable(32)
                self.__sensors.append(s)

        print(f'[{self.__name}] init OK '
              f'({len(self.__sensors)} capteurs, seuil={self.SEUIL}, '
              f'speed={self.CRUISE_SPEED:.2f}, '
              f'curvature={self.CRUISE_CURVATURE:+.3f}, '
              f'L={self.CRUISE_L:.2f}, R={self.CRUISE_R:.2f})',
              file=sys.stderr, flush=True)


    def __set(self, l, r):
        if self.wheel_noise:
            l += np.random.normal(0, self.noise_s)
            r += np.random.normal(0, self.noise_s)

        self.__left_motor.setVelocity(l)
        self.__right_motor.setVelocity(r)

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

                if self.lidar_noise:
                    return (d1 + t * (d2 - d1)) + np.random.normal(0, self.noise_s)
                
                return d1 + t * (d2 - d1)
        return 4.0

    def step(self):
        d = [s.getValue() for s in self.__sensors]
        max_d = max(d) if d else 0

        if max_d < self.SEUIL:
            self.__set(self.CRUISE_L, self.CRUISE_R)
            return

        dist = self.__reading_to_distance(max_d)

        if dist <= self.DIST_STOP:
            self.__set(-1.5, 1.5)
            return
        elif dist < self.DIST_SLOW:
            t = (dist - self.DIST_STOP) / (self.DIST_SLOW - self.DIST_STOP)
            speed = self.MAX_SPEED * t
            speed = max(speed, self.MIN_SPEED * 0.3)
        else:
            speed = self.MAX_SPEED

        # Nearest target: strongest sensor gives its bearing (sensor angle)
        nearest = d.index(max_d)
        bearing = math.radians(self.SENSOR_ANGLES_DEG[nearest])
        turn = math.sin(bearing)

        diff = self.TURN_GAIN * turn * speed
        if self.REVERSE_TURN:
            diff = -diff

        left  = max(0.0, min(self.MAX_SPEED, speed - diff))
        right = max(0.0, min(self.MAX_SPEED, speed + diff))

        self.__set(left, right)