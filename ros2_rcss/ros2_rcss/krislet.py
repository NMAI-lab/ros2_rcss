"""
Krislet: a purely rule-basec baseline agent for ros2_rcss.

This is a ROS2 port of the classic Krislet strategy (Krzysztof Langner).
It talks to an `rcss_client` node in the same namespace through the usual percept / command topics,
so it is a drop-in stand-in for any other agent (e.g. an LLM agent) controlling that player.

Strategy, evaluated once per decision tick on the latest see percept. The
percept is cleared after every action, so Krislet never acts twice on the
same view:
    1. If the ball is not visible -> turn SEARCH_TURN and wait for new visual info.
    2. If the ball is farther than KICKABLE_DISTANCE:
         2.1 if we are facing it (direction == 0) -> dash towards it
         2.2 otherwise -> turn towards it
    3. If the ball is kickable but the opponent goal is not visible
       -> turn SEARCH_TURN and wait for new visual info.
    4. Otherwise -> kick at full power towards the opponent goal.

Parameters:
    decision_period (float, seconds, default 0.2):
        Time between decisions. 
        The original Krislet sleeps 2 simulator steps (2 * 100ms).
        Increase it to artificially slow the agent down. It can be changed at runtime:
            ros2 param set /A/player1/krislet decision_period 1.0
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from rcl_interfaces.msg import SetParametersResult

from std_msgs.msg import String
from ros2_rcss_msgs.msg import (
    SeePercept,
    HearPercept,
    DashCommand,
    TurnCommand,
    KickCommand,
)

DEFAULT_DECISION_PERIOD = 0.2  # 2 * simulator_step
QUEUE_SIZE = 10

# Strategy constants
SEARCH_TURN = 40.0        # turn moment while looking for the ball / goal
KICKABLE_DISTANCE = 1.0   # ball closer than this can be kicked
DASH_GAIN = 10.0          # dash power = DASH_GAIN * ball distance
KICK_POWER = 100.0


class KrisletNode(Node):

    def __init__(self):
        super().__init__('krislet')

        self.declare_parameter('decision_period', DEFAULT_DECISION_PERIOD)
        self.decision_period = self._validated_period(
            self.get_parameter('decision_period').value
        )

        self.side = None              # 'l' or 'r', from the rcss_client
        # Krislet's Memory: the latest see percept, cleared after every action
        # so each decision is based on what was seen after the previous one
        self.latest_see = None
        self.time_over = False

        # Perceptions
        self.create_subscription(SeePercept, 'see', self.see_callback, QUEUE_SIZE)
        self.create_subscription(HearPercept, 'hear', self.hear_callback, QUEUE_SIZE)
        side_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self.create_subscription(String, 'side', self.side_callback, side_qos)

        # Actions
        self.dash_pub = self.create_publisher(DashCommand, 'cmd/dash', QUEUE_SIZE)
        self.turn_pub = self.create_publisher(TurnCommand, 'cmd/turn', QUEUE_SIZE)
        self.kick_pub = self.create_publisher(KickCommand, 'cmd/kick', QUEUE_SIZE)

        self.timer = self.create_timer(self.decision_period, self.decide)
        self.add_on_set_parameters_callback(self.on_parameters_set)

        self.get_logger().info(
            f'Krislet started with decision_period={self.decision_period:.3f}s'
        )

    # PARAMETERS

    def _validated_period(self, value):
        period = float(value)
        if period <= 0.0:
            raise ValueError('decision_period must be > 0')
        return period

    def on_parameters_set(self, params):
        for param in params:
            if param.name != 'decision_period':
                continue
            try:
                period = self._validated_period(param.value)
            except (TypeError, ValueError) as e:
                return SetParametersResult(successful=False, reason=str(e))

            self.decision_period = period
            self.timer.cancel()
            self.destroy_timer(self.timer)
            self.timer = self.create_timer(self.decision_period, self.decide)
            self.get_logger().info(f'decision_period set to {period:.3f}s')
        return SetParametersResult(successful=True)

    # PERCEPTIONS

    def see_callback(self, msg: SeePercept):
        self.latest_see = msg

    def hear_callback(self, msg: HearPercept):
        if msg.sender == 'referee' and msg.message.strip() == 'time_over':
            self.get_logger().info('time_over received, Krislet stopping')
            self.time_over = True

    def side_callback(self, msg: String):
        self.side = msg.data
        self.get_logger().info(f'Playing on side: {self.side}')

    def get_object(self, name):
        for obj in self.latest_see.objects:
            if obj.name == name:
                return obj
        return None

    # DECISION LOOP 

    def decide(self):
        if self.time_over or self.side is None:
            return
        if self.latest_see is None:
            return  # Memory.waitForNewInfo()

        ball = self.get_object('ball')
        if ball is None:
            # 1. Don't know where the ball is -> look for it
            self.turn(SEARCH_TURN)
        elif ball.distance > KICKABLE_DISTANCE:
            # 2. Ball too far -> face it, then run to it
            if ball.direction != 0:
                self.turn(ball.direction)
            else:
                self.dash(DASH_GAIN * ball.distance)
        else:
            # 3/4. Ball kickable -> shoot at the opponent goal
            goal = self.get_object('goal r' if self.side == 'l' else 'goal l')
            if goal is None:
                self.turn(SEARCH_TURN)
            else:
                self.kick(KICK_POWER, goal.direction)

    # ACTIONS

    def turn(self, moment):
        msg = TurnCommand()
        msg.moment = float(moment)
        self.turn_pub.publish(msg)
        self.get_logger().debug(f'turn {moment}')
        self.latest_see = None

    def dash(self, power):
        msg = DashCommand()
        msg.power = float(power)
        msg.direction = 0.0
        self.dash_pub.publish(msg)
        self.get_logger().debug(f'dash {power}')
        self.latest_see = None

    def kick(self, power, direction):
        msg = KickCommand()
        msg.power = float(power)
        msg.direction = float(direction)
        self.kick_pub.publish(msg)
        self.get_logger().debug(f'kick {power} {direction}')
        self.latest_see = None


def main(args=None):
    rclpy.init(args=args)
    node = KrisletNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
