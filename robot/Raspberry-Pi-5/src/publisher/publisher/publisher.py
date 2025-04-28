import rclpy

from std_msgs.msg import String

from rclpy.node import Node

class PublisherNode(Node):
    def __init__(self):
        super().__init__('node_publiser')

        # create topic name and define queue size
        self.publisher_ = self.create_publisher(String, 'chatter', 15)
        commRate = 1 # in seconds
        self.timer = self.create_timer(commRate, self.callbackFunction)
        self.count = 0

    def callbackFunction(self):
        message = String()
        message.data = 'Counter %d' % self.count
        self.publisher_.publish(message)
        self.get_logger().info('Publiser node is publishing: "%s"' % message.data)
        self.count += 1

def main(args=None):
    rclpy.init(args=args)
    node_publisher = PublisherNode()

    rclpy.spin(node_publisher)
    node_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
