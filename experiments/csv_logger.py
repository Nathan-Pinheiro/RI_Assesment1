import csv
import argparse
from pathlib import Path
from functools import partial

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


class CSVLogger(Node):

    def __init__(self, seed, noise_s, source, gain, following, avoidance):
        super().__init__("csv_logger")

        self.seed = seed
        self.noise_s = noise_s
        self.start_time = self.get_clock().now().nanoseconds / 1e9
        self.source = source
        self.gain = gain
        self.following_mode = following
        self.avoidance = avoidance

        results_dir = Path(__file__).resolve().parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        filename = results_dir / (
                    f"seed_{seed}_"
                    f"follow_{following}_"
                    f"gain_{gain}_"
                    f"noise_{noise_s}_"
                    f"source_{source}_"
                    f"avoid_{avoidance}.csv"
                )

        self.file = open(filename, "w", newline="")
        self.writer = csv.writer(self.file)

        self.writer.writerow([
            "simulation_time",
            "robot_id",
            "seed",
            "noise_s",
            "left_speed",
            "right_speed",
            "following",
            "angular_error",
            "target_losses",
            "collision_avoidance",
            "x",
            "y"
        ])

        self.subscriptions_list = []

        for i in range(5):
            robot_id = f"robot_{i}"

            sub = self.create_subscription(
                Float32MultiArray,
                f"/{robot_id}/wheel_speeds",
                partial(self.wheel_callback, robot_id=robot_id),
                10
            )

            self.subscriptions_list.append(sub)

        self.get_logger().info(f"Logging to {filename}")

    def wheel_callback(self, msg, robot_id):

        if len(msg.data) < 9:
            return

        self.writer.writerow([
            msg.data[0],         # Simulation time
            robot_id,
            self.seed,
            self.noise_s,
            msg.data[1],         # Left speed
            msg.data[2],         # Right speed
            int(msg.data[3]),    # Following
            msg.data[4],         # Angular error
            int(msg.data[5]),    # Target losses
            int(msg.data[6]),    # Collision avoidance
            msg.data[7],         # X position
            msg.data[8]          # Y position
        ])

        self.file.flush()

    def destroy_node(self):
        self.file.close()
        return super().destroy_node()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--noise", type=float, required=True)

    parser.add_argument(
        "--source",
        choices=["none", "lidar", "wheels", "both"],
        default="none"
    )

    parser.add_argument("--gain", type=float, default=1.5)

    parser.add_argument(
        "--following",
        choices=["on", "off"],
        default="on"
    )

    parser.add_argument(
        "--avoidance",
        choices=["on", "off"],
        default="on"
    )

    args = parser.parse_args()

    rclpy.init()

    node = CSVLogger(
        args.seed,
        args.noise,
        args.source,
        args.gain,
        args.following,
        args.avoidance
    )

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        print("Logger stopped by user")

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()
            

if __name__ == "__main__":
    main()
