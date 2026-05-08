from launch import LaunchDescription
from launch.actions import OpaqueFunction, DeclareLaunchArgument, ExecuteProcess
from launch_ros.actions import Node

import os

def launch_setup(context, *args, **kwargs):
    # Adding all the nodes
    nodes = [
        ExecuteProcess(
            cmd=["rcssserver"],
            output="screen"
        ),

        ExecuteProcess(
            cmd=["rcssmonitor"],
            output="screen"
        ),

        Node(
            package="ros2_rcss",
            executable="rcss_client",
            name='player1',
            namespace=f"/A/player1",
            parameters=[
                {'team_name': 'A'}
            ],
            output="screen"
        ),

        Node(
            package="ros2_rcss",
            executable="rcss_client",
            name='player1',
            namespace=f"/B/player1",
            parameters=[
                {'team_name': 'B'}
            ],
            output="screen"
        )
    ]

    return nodes

def generate_launch_description():
    ARGUMENTS = [
    ]

    return LaunchDescription(ARGUMENTS + [OpaqueFunction(function=launch_setup)]) 