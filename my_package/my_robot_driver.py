import rclpy
from geometry_msgs.msg import Twist


class MyRobotDriver:
    def init(self, webots_node, properties):
        self.__robot = webots_node.robot

        # Récupère les moteurs de l'e-puck
        self.__left_motor = self.__robot.getDevice('left wheel motor')
        self.__right_motor = self.__robot.getDevice('right wheel motor')

        # Mode vitesse (position infinie)
        self.__left_motor.setPosition(float('inf'))
        self.__left_motor.setVelocity(0.0)
        self.__right_motor.setPosition(float('inf'))
        self.__right_motor.setVelocity(0.0)

        # Client ROS 2
        rclpy.init(args=None)
        self.__node = rclpy.create_node('my_robot_driver')
        self.__node.create_subscription(Twist, 'cmd_vel', self.__cmd_vel_callback, 1)

        self.__target_twist = Twist()

    def __cmd_vel_callback(self, twist):
        self.__target_twist = twist

    def step(self):
        rclpy.spin_once(self.__node, timeout_sec=0)

        forward_speed = self.__target_twist.linear.x
        angular_speed = self.__target_twist.angular.z

        # Conversion en vitesses de roues (e-puck : roues de 2cm de rayon)
        left_speed = (forward_speed - angular_speed * 0.5) / 0.02
        right_speed = (forward_speed + angular_speed * 0.5) / 0.02

        # Limite à la vitesse max de l'e-puck (~6.28 rad/s)
        max_speed = 6.28
        left_speed = max(min(left_speed, max_speed), -max_speed)
        right_speed = max(min(right_speed, max_speed), -max_speed)

        self.__left_motor.setVelocity(left_speed)
        self.__right_motor.setVelocity(right_speed)