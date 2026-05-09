# ROS2 RCSS

<p align="center">
    <img src="images/demo.png" alt="ros2_rcss" width="500">
    <br>
    <em>A demo of ROS2 RCSS</em>
</p>

This is a ROS2 client for the [RoboCup Soccer Simulation 2D](https://ssim.robocup.org/).

## Installation

Compile the Docker container as follows:
```sh
$ docker build --build-arg ROS_DISTRO=${ROS_VERSION} -t rcss .
```

## Running the simulator

1. Start the Docker container
```sh
$ xhost +local:docker

$ docker run --name rcss -it \
--env DISPLAY=$DISPLAY \
--env QT_X11_NO_MITSHM=1 \
--volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
--volume $HOME/.Xauthority:/root/.Xauthority:rw \
rcss
```

2. Launch the simulator inside the container
```sh
ros2 launch ros2_rcss rcss.launch.py [num_players:=] [team1:=] [team2:=]
```

3. Verify that everything is working by doing
```sh
$ ros2 topic list
/A/player1/body
/A/player1/cmd/catch
/A/player1/cmd/dash
/A/player1/cmd/kick
/A/player1/cmd/say
/A/player1/cmd/turn
/A/player1/hear
/A/player1/see
/B/player1/body
/B/player1/cmd/catch
/B/player1/cmd/dash
/B/player1/cmd/kick
/B/player1/cmd/say
/B/player1/cmd/turn
/B/player1/hear
/B/player1/see
```

## Usage

- You can echo the perception topics as follows:
```sh
$ ros2 topic echo /[team]/player[number]/body
$ ros2 topic echo /[team]/player[number]/see
$ ros2 topic echo /[team]/player[number]/hear
```

- You can publish to the action topics as follows:
```sh
$ ros2 topic pub /[team]/player[number]/cmd/dash "{power: [value], direction: [value]}"
$ ros2 topic pub /[team]/player[number]/cmd/turn "{moment: [value]}"
$ ros2 topic pub /[team]/player[number]/cmd/say "{message: [value]}"
$ ros2 topic pub /[team]/player[number]/cmd/kick "{power: [value], direction: [value]}"
$ ros2 topic pub /[team]/player[number]/cmd/catch "{direction: [value]}"
```


## Acknowledgements
- [rcssserver](https://github.com/rcsoccersim/rcssserver)
- [rcssmonitor](https://github.com/rcsoccersim/rcssmonitor)