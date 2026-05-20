import rclpy
from rclpy.node import Node

from collections import deque
from threading import Lock

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
from ros2_rcss.tools.yaml_parser import load_yaml

INITIAL_POSITIONS = {
    '1':  (-50, 0),    # goalie
    '2':  (-30, -20),  # defender
    '3':  (-30, 0),    # defender
    '4':  (-30, 20),   # defender
    '5':  (-20, -10),  # midfielder
    '6':  (-20, 10),   # midfielder
    '7':  (-10, -20),  # midfielder
    '8':  (-10, 0),    # midfielder
    '9':  (-10, 20),   # midfielder
    '10': (0, -10),    # forward
    '11': (0, 10),     # forward
}

QUEUE_SIZE = 5

class RCSSClientNode(Node):

    def __init__(self):

        super().__init__('rcss_client')

        self.client = UDPClient()
        self.parser = Parser()
        
        self._action_queue = deque()
        self._queue_lock = Lock()

        # Declare the parameters
        self.declare_parameter('team_name')
        self.declare_parameter('rcss_client_params')
        self.declare_parameter('is_goalie')

        # Get the value from parameter server
        self.rcss_client_params = load_yaml(self.get_parameter('rcss_client_params').get_parameter_value().string_value)
        self.team_name = self.get_parameter('team_name').get_parameter_value().string_value
        self.is_goalie = self.get_parameter('is_goalie').get_parameter_value().bool_value

        # Perception Publishers

        self.see_pub = self.create_publisher(
            SeePercept,
            'see',
            self.rcss_client_params['queue_size']
        )

        self.hear_pub = self.create_publisher(
            HearPercept,
            'hear',
            self.rcss_client_params['queue_size']
        )

        self.body_pub = self.create_publisher(
            BodyPercept,
            'body',
            self.rcss_client_params['queue_size']
        )

        # Action command subscribers

        self.create_subscription(
            DashCommand,
            'cmd/dash',
            self.dash_callback,
            self.rcss_client_params['queue_size']
        )

        self.create_subscription(
            TurnCommand,
            'cmd/turn',
            self.turn_callback,
            self.rcss_client_params['queue_size']
        )

        self.create_subscription(
            KickCommand,
            'cmd/kick',
            self.kick_callback,
            self.rcss_client_params['queue_size']
        )

        self.create_subscription(
            SayCommand,
            'cmd/say',
            self.say_callback,
            self.rcss_client_params['queue_size']
        )

        self.create_subscription(
            CatchCommand,
            'cmd/catch',
            self.catch_callback,
            self.rcss_client_params['queue_size']
        )

        self.timer = self.create_timer(
            self.rcss_client_params['update_rate'],
            self.poll_server
        )

    def _enqueue(self, cmd: str):
        with self._queue_lock:
            if len(self._action_queue) >= QUEUE_SIZE:
                self.get_logger().warn("Action queue full, dropping oldest command")
                self._action_queue.popleft()
            self._action_queue.append(cmd)

    def _flush_queue(self):
        with self._queue_lock:
            if self._action_queue:
                cmd = self._action_queue.popleft()
                self.get_logger().debug(f"Sending: {cmd}")
                self.client.send(cmd)

    def init_player(self):
        player_desc = f"(init {self.team_name}"
        if self.is_goalie:
            player_desc += " goalie"
        self.client.send(f"{player_desc} (version 15))")
        self._positioned = False

        while True:
            msg = self.client.recv()
            self.get_logger().info(f"[init] received: {msg}")
            if msg and "before_kick_off" in msg:
                parts = msg.split()
                self.side = parts[1]    # 'l' or 'r'
                self.number = parts[2]  # uniform number
                break

        self.move_player_to_position()

    # PERCEPTIONS
    
    def poll_server(self):

        while True:
            raw_msg = self.client.recv()

            # No more messages to process
            if raw_msg is None:
                break

            # Handle before_kick_off positioning
            if 'before_kick_off' in raw_msg and not self._positioned:
                self.move_player_to_position()
                return
            elif 'kick_off' in raw_msg and self._positioned:
                self._positioned = False
                
            # Update perceptions
            percept = self.parser.parse_message(raw_msg)

            if percept is None:
                return
            elif percept['type'] == 'see':
                ros_msg = SeePercept()
                ros_msg.cycle = percept['cycle']
                for obj in percept['objects']:
                    seen_obj = SeenObject()
                    seen_obj.object_type = obj['object_type']
                    seen_obj.distance = obj.get('distance', 0.0)
                    seen_obj.direction = obj.get('direction', 0.0)
                    seen_obj.distance_change = obj.get('distance_change', 0.0)
                    seen_obj.direction_change = obj.get('direction_change', 0.0)
                    ros_msg.objects.append(seen_obj)
                for player in percept['players']:
                    seen_player = SeenPlayer()
                    seen_player.team_name = player.get('team_name') or ''
                    seen_player.uniform_number = player.get('uniform_number') or -1
                    seen_player.goalie = player.get('goalie', False)
                    seen_player.distance = player.get('distance', 0.0)
                    seen_player.direction = player.get('direction', 0.0)
                    seen_player.distance_change = player.get('distance_change', 0.0)
                    seen_player.direction_change = player.get('direction_change', 0.0)
                    seen_player.body_direction = player.get('body_direction', 0.0)
                    seen_player.head_direction = player.get('head_direction', 0.0)
                    ros_msg.players.append(seen_player)
                self.see_pub.publish(ros_msg)
            elif percept['type'] == 'hear':
                ros_msg = HearPercept()
                ros_msg.cycle = percept['cycle']
                ros_msg.sender = percept.get('sender', '')
                ros_msg.direction = percept.get('direction', 0.0)
                ros_msg.message = percept.get('message', '')
                self.hear_pub.publish(ros_msg)
            elif percept['type'] == 'body':
                ros_msg = BodyPercept()
                ros_msg.cycle = percept['cycle']
                ros_msg.stamina = percept.get('stamina', 0.0)
                ros_msg.effort = percept.get('effort', 0.0)
                ros_msg.speed = percept.get('speed', 0.0)
                ros_msg.speed_direction = percept.get('speed_direction', 0.0)
                ros_msg.neck_direction = percept.get('neck_direction', 0.0)
                ros_msg.view_mode = percept.get('view_mode', '')
                self.body_pub.publish(ros_msg)

        # Send the most recent action
        self._flush_queue()

    # ACTION CALLBACKS

    def dash_callback(self, msg: DashCommand):
        cmd = f'(dash {msg.power} {msg.direction})'
        self._enqueue(cmd)

    def turn_callback(self, msg: TurnCommand):
        cmd = f'(turn {msg.moment})'
        self._enqueue(cmd)

    def kick_callback(self, msg: KickCommand):
        cmd = f'(kick {msg.power} {msg.direction})'
        self._enqueue(cmd)

    def say_callback(self, msg: SayCommand):
        cmd = f'(say "{msg.message}")'
        self._enqueue(cmd)

    def catch_callback(self, msg: CatchCommand):
        cmd = f'(catch {msg.direction})'
        self._enqueue(cmd)

    # HELPERS

    def move_player_to_position(self):
        x, y = INITIAL_POSITIONS.get(self.number, (-10, 0))
        self._enqueue(f'(move {x} {y})')
        if self.side == 'l':
            self._enqueue('(turn 0)')
        else:
            self._enqueue('(turn 180)')
        self._positioned = True
        
def main(args=None):

    rclpy.init(args=args)

    node = RCSSClientNode()
    node.init_player()
    
    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()