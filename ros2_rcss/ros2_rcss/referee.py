"""
Referee helper: the match's trainer ("coach"). It starts the match on request and keeps the ball in play.

rcssserver runs in coach mode (`coach:=true`, with its own referee kept on: `server::coach_w_referee=1`). This
node is the one trainer the server allows (UDP port 6001):

    * service `/referee/kick_off` (std_srvs/Trigger): `(change_mode play_on)`, the unattended version of pressing
      Kick Off. It works whichever side a player got. With `kick_off_on_command_of` the match also starts by
      itself when the first command of one of those teams' players arrives (the clock then starts when the
      agent acts, not when the simulator is up; leave out a team that runs Krislet, whose first command is at once).
    * once the match has started, whenever the referee stops play (ball out, free kick, offside, the kick-off
      after a goal, ...) the ball is put back in the centre and play goes on, RESUME_DELAY_S later.

Parameters: host, port (the server's trainer port), kick_off_on_start (default false: wait for the service),
kick_off_on_command_of (team names, default none) with num_players (players per team), resume_delay_s.
"""

import re
import time

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

from ros2_rcss_msgs.msg import DashCommand, KickCommand, TurnCommand

from .tools.udp_client import UDPClient

DEFAULT_HOST = 'localhost'
TRAINER_PORT = 6001
POLL_PERIOD_S = 0.05          # how often the node reads the server's messages
INIT_RETRY_S = 1.0            # the server may not be up yet: ask again
DEFAULT_RESUME_DELAY_S = 1.0  # lets the referee finish its own moves first
INIT = '(init (version 5))\0'
EAR_ON = '(ear on)\0'         # the trainer hears the referee's calls
PLAY_ON = '(change_mode play_on)\0'
BALL_TO_CENTRE = '(move (ball) 0 0 0 0 0)\0'  # x y angle vx vy: still, in the centre
INIT_OK = '(init ok)'
ALREADY_HAVE_TRAINER = 'already_have_offline_coach'
COMMANDS = {'dash': DashCommand, 'turn': TurnCommand, 'kick': KickCommand}  # what a player is told to do
QUEUE_SIZE = 10
REFEREE_RE = re.compile(r'^\(hear \d+ referee (\w+)\)')
# Calls that do not stop play: running play, the pre-game wait, a goal (players walk back, then comes kick_off_*),
# and the end of a half.
CONTINUES_RE = re.compile(r'^(play_on|before_kick_off|goal_[lr]_\d+|half_time|time_\w+)$')


class RefereeNode(Node):

    def __init__(self):
        super().__init__('referee')
        self.declare_parameter('host', DEFAULT_HOST)
        self.declare_parameter('port', TRAINER_PORT)
        self.declare_parameter('kick_off_on_start', False)
        self.declare_parameter('resume_delay_s', DEFAULT_RESUME_DELAY_S)
        self.declare_parameter('kick_off_on_command_of', [''])
        self.declare_parameter('num_players', 1)
        self.client = UDPClient(self.get_parameter('host').value, self.get_parameter('port').value)
        self.connected = False
        self.playing = False   # the match has been started: only then is the ball put back
        self.resume_at = None  # when to put the ball back and play on
        self.last_call = None  # the referee's latest call, for the log
        self._last_init = 0.0
        self.create_service(Trigger, '~/kick_off', self.on_kick_off)
        self.create_timer(POLL_PERIOD_S, self.poll)
        self.watch_commands()

    def poll(self):
        if not self.connected and time.monotonic() - self._last_init >= INIT_RETRY_S:
            self._last_init = time.monotonic()
            self.client.send(INIT)
        while (message := self.client.recv()) is not None:
            self.on_message(message)
        if self.resume_at is not None and time.monotonic() >= self.resume_at:
            self.resume_at = None
            self.get_logger().info(f'{self.last_call}: ball to the centre, play_on')
            self.client.send(BALL_TO_CENTRE)
            self.client.send(PLAY_ON)

    def on_message(self, message):
        if message.startswith(INIT_OK):
            self.connected = True
            self.client.send(EAR_ON)
            self.get_logger().info('connected to the server as trainer')
            if self.get_parameter('kick_off_on_start').value:
                self.start_match()
        elif ALREADY_HAVE_TRAINER in message:
            self.get_logger().warning('the server already has a trainer', throttle_duration_sec=10)
        elif (call := REFEREE_RE.match(message)):
            self.last_call, self.resume_at = call.group(1), None
            if self.playing and not CONTINUES_RE.match(call.group(1)):
                self.resume_at = time.monotonic() + self.get_parameter('resume_delay_s').value

    def watch_commands(self):
        """Start the match at the first command of a watched team's player."""
        teams = [t for t in self.get_parameter('kick_off_on_command_of').value if t]
        for team in teams:
            for player in range(1, self.get_parameter('num_players').value + 1):
                for command, msg_type in COMMANDS.items():
                    self.create_subscription(msg_type, f'/{team}/player{player}/cmd/{command}',
                                             self.on_player_command, QUEUE_SIZE)

    def on_player_command(self, _msg):
        if not self.playing and self.connected:
            self.get_logger().info('first player command: play_on')
            self.start_match()

    def start_match(self):
        self.playing = True
        self.client.send(PLAY_ON)

    def on_kick_off(self, _request, response):
        response.success = self.connected
        if self.connected:
            self.start_match()
        response.message = 'play_on' if self.connected else 'not connected to the server as trainer (server::coach=1?)'
        return response


def main(args=None):
    rclpy.init(args=args)
    node = RefereeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
