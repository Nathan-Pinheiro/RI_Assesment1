import sys
import math
import random


class MyRobotDriver:

    SENSOR_ANGLES_DEG = [-50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50]

    SEED = 43

    SEUIL = 50

    DIST_STOP = 0.1
    DIST_SLOW = 0.5

    MAX_SPEED = 5.0
    MIN_SPEED = 1.0
    TURN_GAIN = 2.5
    CRUISE_L = 4.0
    CRUISE_R = 3.5

    REVERSE_TURN = False

    LOOKUP = [
        (0.0,  1024),
        (0.05, 1000),
        (0.5,  800),
        (1.0,  600),
        (2.0,  300),
        (3.0,  120),
        (4.0,  0),
    ]

    def init(self, webots_node, properties):
        self.__robot = webots_node.robot
        self.__name = self.__robot.getName()

        robot_index = 0
        if '_' in self.__name:
            try:
                robot_index = int(self.__name.rsplit('_', 1)[1])
            except ValueError:
                robot_index = 0
        random.seed(self.SEED + robot_index)

        angle = random.uniform(0.0, 2.0 * math.pi)
        try:
            self_node = self.__robot.getSelf()
            if self_node is not None:
                self_node.getField('rotation').setSFRotation([0, 0, 1, angle])
                print(f'[{self.__name}] angle = {angle:.2f} rad',
                      file=sys.stderr, flush=True)
        except Exception as e:
            print(f'[{self.__name}] erreur rotation: {e}',
                  file=sys.stderr, flush=True)

        self.__left_motor = self.__robot.getDevice('left wheel motor')
        self.__right_motor = self.__robot.getDevice('right wheel motor')
        self.__left_motor.setPosition(float('inf'))
        self.__right_motor.setPosition(float('inf'))
        self.__left_motor.setVelocity(0.0)
        self.__right_motor.setVelocity(0.0)

        self.__sensors = []
        for i in range(11):
            s = self.__robot.getDevice(f'ds_{i}')
            if s is None:
                print(f'[{self.__name}] ds_{i} INTROUVABLE',
                      file=sys.stderr, flush=True)
            else:
                s.enable(32)
                self.__sensors.append(s)

        self.__sin_angles = [
            math.sin(math.radians(a)) for a in self.SENSOR_ANGLES_DEG
        ]

        print(f'[{self.__name}] init OK ({len(self.__sensors)} capteurs)',
              file=sys.stderr, flush=True)

    def __set(self, l, r):
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
            self.__set(0.0, 0.0)
            return
        elif dist < self.DIST_SLOW:
            t = (dist - self.DIST_STOP) / (self.DIST_SLOW - self.DIST_STOP)
            speed = self.MAX_SPEED * t
            speed = max(speed, self.MIN_SPEED * 0.3)
        else:
            speed = self.MAX_SPEED

        turn = 0.0
        for i, di in enumerate(d):
            if di > self.SEUIL:
                turn += (di / 1024.0) * self.__sin_angles[i]
        turn = max(-1.0, min(1.0, turn))

        diff = self.TURN_GAIN * turn * speed
        if self.REVERSE_TURN:
            diff = -diff

        left  = max(0.0, min(self.MAX_SPEED, speed - diff))
        right = max(0.0, min(self.MAX_SPEED, speed + diff))

        self.__set(left, right)