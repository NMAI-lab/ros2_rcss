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
ros2 launch ros2_rcss rcss.launch.py [num_players:=] [team1:=] [team2:=] [make_goalie:=] [krislet:=] [krislet_period:=]
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
$ ros2 topic pub -t 1 /[team]/player[number]/cmd/dash ros2_rcss_msgs/msg/DashCommand "{power: [value], direction: [value]}"
$ ros2 topic pub -t 1 /[team]/player[number]/cmd/turn ros2_rcss_msgs/msg/TurnCommand "{moment: [value]}"
$ ros2 topic pub -t 1 /[team]/player[number]/cmd/say ros2_rcss_msgs/msg/SayCommand "{message: [value]}"
$ ros2 topic pub -t 1 /[team]/player[number]/cmd/kick ros2_rcss_msgs/msg/KickCommand "{power: [value], direction: [value]}"
$ ros2 topic pub -t 1 /[team]/player[number]/cmd/catch ros2_rcss_msgs/msg/CatchCommand "{direction: [value]}"
```

- Each `see` object has an `object_type` (`ball`, `goal`, `flag`) and a full `name` (e.g. `ball`, `goal r`, `flag c t`).
- Each player publishes its field side (`l` or `r`) on the latched topic `/[team]/player[number]/side`.

## Krislet baseline agent

A ROS2 port of the classic rule-based Krislet (Krzysztof Langner) strategy is included as a non-LLM baseline. It uses the same `see`/`hear`/`side` topics and `cmd/*` topics as any other agent:

1. Ball not visible → turn 40° and wait for new visual info.
2. Ball farther than 1.0 → turn to it, or dash at it if already facing it.
3. Ball kickable but opponent goal not visible → turn 40° and wait.
4. Otherwise → kick at full power towards the opponent goal.

Choose which team(s) Krislet controls and how often it decides (seconds between decisions; larger = slower):
```sh
# From the docker script: starts the match in this terminal (Ctrl-C stops it and the container)
$ ./rcss.sh --run --krislet both --krislet-period 0.5     # none | team1 | team2 | both
$ ./rcss.sh --run --krislet team1 num_players:=3          # extra name:=value args go to the launch file
$ ./rcss.sh --run                                         # starts the match without Krislet
$ ./rcss.sh --run --krislet both --no-launch              # only open a shell; launch manually

# Or directly at launch time (overrides the docker script values)
$ ros2 launch ros2_rcss rcss.launch.py num_players:=3 krislet:=team1 krislet_period:=1.0

# Or change the speed of a running Krislet on the fly
$ ros2 param set /A/player1/krislet decision_period 2.0
```

The default period is `0.2s`, matching the original Krislet (two simulator steps). Krislet clears its view after
every action and only acts again on a newer `see` percept. `rcss_client` sends at most one command per server
cycle (0.1s), so periods below that only fill the queue.

## Acknowledgements
- [rcssserver](https://github.com/rcsoccersim/rcssserver)
- [rcssmonitor](https://github.com/rcsoccersim/rcssmonitor)