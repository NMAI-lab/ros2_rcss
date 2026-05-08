cmake_minimum_required(VERSION 3.8)
project(ros2_rcss_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}

  #
  # Percepts
  #

  "msg/SeenObject.msg"
  "msg/SeenPlayer.msg"
  "msg/SeePercept.msg"
  "msg/HearPercept.msg"
  "msg/BodyPercept.msg"

  #
  # Commands
  #

  "msg/DashCommand.msg"
  "msg/TurnCommand.msg"
  "msg/KickCommand.msg"
  "msg/SayCommand.msg"
  "msg/CatchCommand.msg"

  DEPENDENCIES builtin_interfaces
)

ament_package()