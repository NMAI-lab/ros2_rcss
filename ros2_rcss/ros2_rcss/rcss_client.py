import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy

from collections import deque
from threading import Lock

from std_msgs.msg import String
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

# Team-relative positions: the server mirrors them for the right side, so
# negative x is always our own half.
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
INIT_RETRY_PERIOD = 1.0   # seconds between (init ...) attempts
INIT_POLL_PERIOD = 0.01   # seconds between socket reads while waiting for (init ...)
DEFAULT_POSITION = (-10, 0)


def move_allowed(play_mode: str) -> bool:
    """Play modes in which the server accepts the (move x y) command."""
    return play_mode == 'before_kick_off' or play_mode.startswith('goal_')


class RCSSClientNode(Node):

    def __init__(self):

        super().__init__('rcss_client')

        self.client = UDPClient()
        self.parser = Parser()

        self._action_queue = deque()
        self._queue_lock = Lock()
        self._pending_move = None  # sent before any queued action
        # The server executes at most one action per cycle. 
        # A new cycle starts with every sense_body, so one command may be sent per sense_body.
        self._can_send = True

        self.side = None
        self.number = None
        self.play_mode = None

        # Declare the parameters
        self.declare_parameter('team_name', 'A')
        self.declare_parameter('rcss_client_params', '')
        self.declare_parameter('is_goalie', False)

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

        # Latched so late subscribers (e.g. agents) still get the side ('l' or 'r')
        self.side_pub = self.create_publisher(
            String,
            'side',
            QoSProfile(
                depth=1,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            )
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
        self._send_next()

    def _send_next(self):
        """Send the next command right away if this cycle's slot is still free."""
        with self._queue_lock:
            if not self._can_send:
                return
            if self._pending_move is not None:
                cmd, self._pending_move = self._pending_move, None
            elif self._action_queue:
                cmd = self._action_queue.popleft()
            else:
                return
            self._can_send = False
        self.get_logger().debug(f"Sending: {cmd}")
        self.client.send(cmd)

    def init_player(self):
        player_desc = f"(init {self.team_name}"
        if self.is_goalie:
            player_desc += " goalie"
        player_desc += " (version 15))"

        # The server may not be listening yet, so retry until it answers
        last_sent = 0.0
        while rclpy.ok():
            if time.monotonic() - last_sent >= INIT_RETRY_PERIOD:
                self.client.send(player_desc)
                last_sent = time.monotonic()

            msg = self.client.recv()
            if msg is None:
                time.sleep(INIT_POLL_PERIOD)
                continue

            self.get_logger().info(f"[init] received: {msg}")
            if msg.startswith("(init "):
                parts = msg.strip("()").split()
                self.side = parts[1]          # 'l' or 'r'
                self.number = parts[2]        # uniform number
                play_mode = parts[3] if len(parts) > 3 else ''
                break
            if msg.startswith("(error"):
                raise RuntimeError(f"Server rejected {player_desc}: {msg}")

        self.side_pub.publish(String(data=self.side))
        self.on_play_mode(play_mode)

    # PERCEPTIONS

    def poll_server(self):

        while True:
            raw_msg = self.client.recv()

            # No more messages to process
            if raw_msg is None:
                break

            percept = self.parser.parse_message(raw_msg)

            # server_param, player_type, ok, error, ...
            if percept is None:
                if raw_msg.startswith("(error"):
                    self.get_logger().warn(f"Server error: {raw_msg}")
                continue

            if percept['type'] == 'see':
                ros_msg = SeePercept()
                ros_msg.cycle = percept['cycle']
                for obj in percept['objects']:
                    seen_obj = SeenObject()
                    seen_obj.object_type = obj['object_type']
                    seen_obj.name = obj.get('name', obj['object_type'])
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
                if percept['sender'] == 'referee':
                    self.on_play_mode(percept['message'])
                ros_msg = HearPercept()
                ros_msg.cycle = percept['cycle']
                ros_msg.sender = percept.get('sender', '')
                ros_msg.direction = percept.get('direction', 0.0)
                ros_msg.message = percept.get('message', '')
                self.hear_pub.publish(ros_msg)
            elif percept['type'] == 'body':
                with self._queue_lock:
                    self._can_send = True
                ros_msg = BodyPercept()
                ros_msg.cycle = percept['cycle']
                ros_msg.stamina = percept.get('stamina', 0.0)
                ros_msg.effort = percept.get('effort', 0.0)
                ros_msg.speed = percept.get('speed', 0.0)
                ros_msg.speed_direction = percept.get('speed_direction', 0.0)
                ros_msg.neck_direction = percept.get('neck_direction', 0.0)
                ros_msg.view_mode = percept.get('view_mode', '')
                self.body_pub.publish(ros_msg)

        # A new cycle may have started: send the next queued action
        self._send_next()

    def on_play_mode(self, play_mode: str):
        """Track the referee's play mode and go to the formation position whenever moving is allowed."""
        if play_mode == self.play_mode:
            return
        self.play_mode = play_mode
        if move_allowed(play_mode):
            self.move_player_to_position()

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
        # The server already spawns both sides facing the opponent goal, so no turn is needed
        x, y = INITIAL_POSITIONS.get(self.number, DEFAULT_POSITION)
        with self._queue_lock:
            self._pending_move = f'(move {x} {y})'
        self._send_next()

    def disconnect(self):
        try:
            self.client.send('(bye)')
        except OSError:
            pass


def main(args=None):

    rclpy.init(args=args)

    node = RCSSClientNode()
    try:
        node.init_player()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.disconnect()
        node.destroy_node()
        rclpy.try_shutdown()
