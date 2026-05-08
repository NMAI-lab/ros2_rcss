import rclpy
from rclpy.node import Node

from ros2_rcss_msgs.msg import (
    SeePercept,
    SeenObject,
    SeenPlayer,
    HearPercept,
    BodyPercept,

    DashCommand,
    TurnCommand,
    KickCommand,
    SayCommand,
    CatchCommand
)

from ros2_rcss.tools.udp_client import UDPClient
from ros2_rcss.tools.parser import Parser

POSITIONS = {
    "1":  (-50, 0),    # goalie
    "2":  (-30, -20),  # defender
    "3":  (-30, 0),    # defender
    "4":  (-30, 20),   # defender
    "5":  (-20, -10),  # midfielder
    "6":  (-20, 10),   # midfielder
    "7":  (-10, -20),  # midfielder
    "8":  (-10, 0),    # midfielder
    "9":  (-10, 20),   # midfielder
    "10": (0,  -10),   # forward
    "11": (0,   10),   # forward
}

class RCSSClientNode(Node):

    def __init__(self):

        super().__init__("rcss_client")

        self.client = UDPClient()
        self.parser = Parser()

        self.declare_parameter('team_name')
        
        self.team_name = self.get_parameter('team_name').get_parameter_value().string_value

        #
        # Publishers
        #

        self.see_pub = self.create_publisher(
            SeePercept,
            'see',
            10
        )

        self.hear_pub = self.create_publisher(
            HearPercept,
            'hear',
            10
        )

        self.body_pub = self.create_publisher(
            BodyPercept,
            'body',
            10
        )

        #
        # Action command subscribers
        #

        self.create_subscription(
            DashCommand,
            'cmd/dash',
            self.dash_callback,
            10
        )

        self.create_subscription(
            TurnCommand,
            'cmd/turn',
            self.turn_callback,
            10
        )

        self.create_subscription(
            KickCommand,
            'cmd/kick',
            self.kick_callback,
            10
        )

        self.create_subscription(
            SayCommand,
            'cmd/say',
            self.say_callback,
            10
        )

        self.create_subscription(
            CatchCommand,
            'cmd/catch',
            self.catch_callback,
            10
        )

        #
        # Poll timer
        #

        self.timer = self.create_timer(
            0.1,
            self.poll_server
        )

    def init_player(self):
        self.client.send(f"(init {self.team_name} (version 15))")

        while True:
            msg = self.client.recv()
            self.get_logger().info(f"[init] received: {msg}")
            if msg and "before_kick_off" in msg:
                self.number = msg.split()[2]
                break

        self.move_player_to_position()

    # PERCEPTIONS
    
    def poll_server(self):

        raw_msg = self.client.recv()

        if raw_msg is None:
            return

        # Handle before_kick_off positioning
        if "before_kick_off" in raw_msg:
            self.move_player_to_position()
            return
        
        percept = self.parser.parse_message(raw_msg)

        if percept is None:
            return

        #
        # SEE
        #

        if percept["type"] == "see":

            ros_msg = SeePercept()
            ros_msg.cycle = percept["cycle"]

            #
            # Objects
            #

            for obj in percept["objects"]:

                seen_obj = SeenObject()

                seen_obj.object_type = obj["object_type"]

                seen_obj.distance = obj.get("distance", 0.0)
                seen_obj.direction = obj.get("direction", 0.0)

                seen_obj.distance_change = obj.get(
                    "distance_change",
                    0.0
                )

                seen_obj.direction_change = obj.get(
                    "direction_change",
                    0.0
                )

                ros_msg.objects.append(seen_obj)

            #
            # Players
            #

            for player in percept["players"]:

                seen_player = SeenPlayer()

                seen_player.team_name = player.get(
                    "team_name",
                    ""
                )

                seen_player.uniform_number = player.get(
                    "uniform_number",
                    -1
                )

                seen_player.goalie = player.get(
                    "goalie",
                    False
                )

                seen_player.distance = player.get(
                    "distance",
                    0.0
                )

                seen_player.direction = player.get(
                    "direction",
                    0.0
                )

                seen_player.distance_change = player.get(
                    "distance_change",
                    0.0
                )

                seen_player.direction_change = player.get(
                    "direction_change",
                    0.0
                )

                seen_player.body_direction = player.get(
                    "body_direction",
                    0.0
                )

                seen_player.head_direction = player.get(
                    "head_direction",
                    0.0
                )

                ros_msg.players.append(seen_player)

            self.see_pub.publish(ros_msg)

        #
        # HEAR
        #

        elif percept["type"] == "hear":

            ros_msg = HearPercept()
            ros_msg.cycle = percept["cycle"]

            ros_msg.sender = percept.get(
                "sender",
                ""
            )

            ros_msg.direction = percept.get(
                "direction",
                0.0
            )

            ros_msg.message = percept.get(
                "message",
                ""
            )

            self.hear_pub.publish(ros_msg)

        #
        # BODY
        #

        elif percept["type"] == "body":

            ros_msg = BodyPercept()
            ros_msg.cycle = percept["cycle"]

            ros_msg.stamina = percept.get(
                "stamina",
                0.0
            )

            ros_msg.effort = percept.get(
                "effort",
                0.0
            )

            ros_msg.speed = percept.get(
                "speed",
                0.0
            )

            ros_msg.speed_direction = percept.get(
                "speed_direction",
                0.0
            )

            ros_msg.neck_direction = percept.get(
                "neck_direction",
                0.0
            )

            ros_msg.view_mode = percept.get(
                "view_mode",
                ""
            )

            self.body_pub.publish(ros_msg)

    # ACTION CALLBACKS

    def dash_callback(self, msg: DashCommand):

        cmd = f"(dash {msg.power} {msg.direction})"

        self.client.send(cmd)

    def turn_callback(self, msg: TurnCommand):

        cmd = f"(turn {msg.moment})"

        self.client.send(cmd)

    def kick_callback(self, msg: KickCommand):

        cmd = f"(kick {msg.power} {msg.direction})"

        self.client.send(cmd)

    def say_callback(self, msg: SayCommand):

        cmd = f'(say "{msg.message}")'

        self.client.send(cmd)

    def catch_callback(self, msg: CatchCommand):

        cmd = f"(catch {msg.direction})"

        self.client.send(cmd)

    # HELPERS

    def move_player_to_position(self):
        x, y = POSITIONS.get(self.number, (-10, 0))
        self.client.send(f"(move {x} {y})")


def main(args=None):

    rclpy.init(args=args)

    node = RCSSClientNode()
    node.init_player()
    
    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()