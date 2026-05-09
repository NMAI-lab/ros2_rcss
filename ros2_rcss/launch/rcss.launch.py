from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import OpaqueFunction, DeclareLaunchArgument, ExecuteProcess
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

import os

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

    nodes = [
        ExecuteProcess(
            cmd=['rcssserver'],
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
    ]

    return LaunchDescription(ARGUMENTS + [OpaqueFunction(function=launch_setup)]) 