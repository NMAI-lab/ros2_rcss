from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import OpaqueFunction, DeclareLaunchArgument, ExecuteProcess
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration, EnvironmentVariable

import os

KRISLET_OPTIONS = {'none', 'team1', 'team2', 'both'}

# rcssserver drops the ball (and teleports the players away from it) when nobody has kicked it for this
# many cycles. Its default of 100 cycles (10 s) is too short for agents that take a few seconds per
# decision: they never reach the ball. 500 cycles = 50 s. Also used for kick_off_wait.
DEFAULT_DROP_BALL_TIME = 500

def launch_setup(context, *args, **kwargs):
    # Environment config files.
    pkg_ros2_rcss = get_package_share_directory('ros2_rcss')
    rcss_client_params_yaml_file = os.path.join(
        pkg_ros2_rcss,
        'config',
        'rcss_client_params.yaml'
    )

    num_players = int(LaunchConfiguration('num_players').perform(context))
    team1_name = LaunchConfiguration('team1').perform(context)
    team2_name = LaunchConfiguration('team2').perform(context)
    make_goalie = LaunchConfiguration('make_goalie').perform(context)
    krislet = LaunchConfiguration('krislet').perform(context).strip().lower()
    krislet_period = float(LaunchConfiguration('krislet_period').perform(context))
    drop_ball_time = int(LaunchConfiguration('drop_ball_time').perform(context))

    if krislet not in KRISLET_OPTIONS:
        raise ValueError(
            f"Invalid krislet:='{krislet}'. Expected one of {sorted(KRISLET_OPTIONS)}."
        )
    if krislet_period <= 0.0:
        raise ValueError('krislet_period must be > 0')

    krislet_teams = []
    if krislet in ('team1', 'both'):
        krislet_teams.append(team1_name)
    if krislet in ('team2', 'both'):
        krislet_teams.append(team2_name)

    nodes = [
        ExecuteProcess(
            cmd=['rcssserver',
                 f'server::drop_ball_time={drop_ball_time}',
                 f'server::kick_off_wait={drop_ball_time}'],
            output='screen'
        ),

        ExecuteProcess(
            cmd=['rcssmonitor'],
            output='screen'
        )
    ]

    for i in range(num_players):
        is_goalie = False
        if make_goalie.lower() == 'true' and i == 0:
            is_goalie = True

        nodes.append(
            Node(
                package='ros2_rcss',
                executable='rcss_client',
                name=f'player{i+1}',
                namespace=f'/{team1_name}/player{i+1}',
                parameters=[
                    {'team_name': f'{team1_name}'},
                    {'rcss_client_params': rcss_client_params_yaml_file},
                    {'is_goalie': is_goalie}
                ],
                output='screen'
            )
        )

        nodes.append(
            Node(
                package='ros2_rcss',
                executable='rcss_client',
                name=f'player{i+1}',
                namespace=f'/{team2_name}/player{i+1}',
                parameters=[
                    {'team_name': f'{team2_name}'},
                    {'rcss_client_params': rcss_client_params_yaml_file},
                    {'is_goalie': is_goalie}
                ],
                output='screen'
            )
        )

        # Krislet agents drive the players of the selected team(s)
        for team_name in krislet_teams:
            nodes.append(
                Node(
                    package='ros2_rcss',
                    executable='krislet',
                    name='krislet',
                    namespace=f'/{team_name}/player{i+1}',
                    parameters=[{'decision_period': krislet_period}],
                    output='screen'
                )
            )

    return nodes

def generate_launch_description():
    ARGUMENTS = [
        DeclareLaunchArgument('num_players', default_value='1',
                              description='The number of players per team.'),
        DeclareLaunchArgument('team1', default_value='A',
                              description='The first team name.'),
        DeclareLaunchArgument('team2', default_value='B',
                              description='The second team name.'),
        DeclareLaunchArgument('make_goalie', default_value='false',
                              description='Make Player 1 Goalie.'),
        DeclareLaunchArgument('krislet',
                              default_value=EnvironmentVariable('KRISLET', default_value='none'),
                              description='Which team(s) Krislet controls: none, team1, team2 or both.'),
        DeclareLaunchArgument('drop_ball_time', default_value=str(DEFAULT_DROP_BALL_TIME),
                              description='Cycles before the referee drops an unkicked ball (also sets '
                                          'kick_off_wait); rcssserver\'s default is 100.'),
        DeclareLaunchArgument('krislet_period',
                              default_value=EnvironmentVariable('KRISLET_PERIOD', default_value='0.2'),
                              description='Seconds between Krislet decisions (larger = slower).'),
    ]

    return LaunchDescription(ARGUMENTS + [OpaqueFunction(function=launch_setup)]) 