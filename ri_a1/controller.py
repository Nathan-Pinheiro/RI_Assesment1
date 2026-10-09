from geometry_msgs.msg import TwistStamped
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range


class MonControleur(Node):
    def __init__(self):
        super().__init__('ri_a1_controller')

        # --- Récupération du nom du robot (passé par le launch file) ---
        self.declare_parameter('robot_name', 'epuck_1')
        self.robot_name = self.get_parameter('robot_name').get_parameter_value().string_value

        self.get_logger().info(f'🤖 Contrôleur initialisé pour {self.robot_name}')

        # --- Abonnement aux capteurs avec namespace ---
        self.distances = [0.0] * 8
        for i in range(8):
            self.create_subscription(
                Range, f'/{self.robot_name}/ps{i}',
                lambda msg, idx=i: self._range_callback(msg, idx),
                10
            )

        # --- Publication des commandes moteurs avec namespace ---
        self.cmd_pub = self.create_publisher(
            TwistStamped, f'/{self.robot_name}/cmd_vel', 10
        )

        # --- Timer de décision ---
        self.create_timer(0.1, self._decide)
        self.last_log_time = 0.0

        # --- Paramètres de comportement (à ajuster) ---
        self.DETECTION_THRESHOLD = 300.0   # mm : distance à laquelle on "voit" un robot
        self.DANGER_THRESHOLD = 100.0      # mm : trop près, on s'arrête
        self.CRUISE_SPEED = 0.06           # m/s : vitesse de suivi
        self.SEARCH_SPEED = 0.03           # m/s : vitesse en mode recherche
        self.SEARCH_TURN = 0.6             # rad/s : rotation en mode recherche
        self.ALIGN_GAIN = 0.005            # gain de la correction angulaire

    def _range_callback(self, msg, idx):
        self.distances[idx] = msg.range * 1000  # convertir en mm

    def _decide(self):
        cmd = TwistStamped()
        cmd.header.stamp = self.get_clock().now().to_msg()

        # Capteurs avant gauche (0) et avant droit (7) de l'e-puck
        front_left = self._distance(0)
        front_right = self._distance(7)
        closest_front = min(front_left, front_right)

        if closest_front < self.DETECTION_THRESHOLD:
            # ---------- MODE SUIVI ----------
            if closest_front < self.DANGER_THRESHOLD:
                # Trop près : on recule légèrement pour garder de la distance
                cmd.twist.linear.x = -0.02
                cmd.twist.angular.z = 0.0
                self._log_throttled(f'⚠️ [{self.robot_name}] Trop près, je recule.')
            else:
                # Suivi : avancer + s'aligner sur le robot devant
                cmd.twist.linear.x = self.CRUISE_SPEED
                # Correction : si le robot est plus à droite, on tourne à droite
                error = front_right - front_left
                cmd.twist.angular.z = error * self.ALIGN_GAIN
                self._log_throttled(f'👣 [{self.robot_name}] Je suis un robot.')
        else:
            # ---------- MODE RECHERCHE ----------
            cmd.twist.linear.x = self.SEARCH_SPEED
            cmd.twist.angular.z = self.SEARCH_TURN
            self._log_throttled(f'🔍 [{self.robot_name}] Je cherche un robot.')

        self.cmd_pub.publish(cmd)

    def _distance(self, index):
        distance = self.distances[index]
        # Webots renvoie parfois 0.0 quand rien n'est détecté -> on met une grande valeur
        return distance if distance > 0.0 else 1000.0

    def _log_throttled(self, message):
        now = self.get_clock().now().nanoseconds / 1e9
        if now - self.last_log_time >= 2.0:
            self.get_logger().info(message)
            self.last_log_time = now


def main(args=None):
    rclpy.init(args=args)
    node = MonControleur()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
