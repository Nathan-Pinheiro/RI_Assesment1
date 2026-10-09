import rclpy
from geometry_msgs.msg import Twist

class Controller:
    def init(self, webots_node, properties):
        self.__robot = webots_node.robot

        self.__left_motor = self.__robot.getDevice('left wheel motor')
        self.__right_motor = self.__robot.getDevice('right wheel motor')

        self.__left_motor.setPosition(float('inf'))
        self.__right_motor.setPosition(float('inf'))

        self.__left_motor.setVelocity(-3.0)
        self.__right_motor.setVelocity(3.0)

    def step(self):
        pass