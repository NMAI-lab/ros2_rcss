#!/bin/bash

CONTAINER="rcss"

usage() {
    cat <<USAGE
Usage: $0 {--compile|--run|--all} [ros_distro] [options]

Options:
  --krislet {none|team1|team2|both}   Team(s) controlled by the Krislet agent (default: none)
  --krislet-period <seconds>          Seconds between Krislet decisions; larger = slower (default: 0.2)
  --no-launch                         Only open a shell in the container; start the match yourself
                                      (by default the match starts automatically)
  name:=value                         Extra launch args forwarded to rcss.launch.py (e.g. num_players:=3)

By default, 'ros2 launch' runs in this terminal as the container's main process.
USAGE
    exit 1
}

MODE=""
ROS_VERSION="humble"
KRISLET="none"
KRISLET_PERIOD="0.2"
LAUNCH=1
LAUNCH_ARGS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --compile|--run|--all) MODE="$1" ;;
        --krislet)             KRISLET="$2"; shift ;;
        --krislet=*)           KRISLET="${1#*=}" ;;
        --krislet-period)      KRISLET_PERIOD="$2"; shift ;;
        --krislet-period=*)    KRISLET_PERIOD="${1#*=}" ;;
        --launch)              LAUNCH=1 ;;
        --no-launch)           LAUNCH=0 ;;
        *:=*)                  LAUNCH_ARGS+=("$1") ;;
        -h|--help)             usage ;;
        -*)                    echo "Unknown option: $1"; usage ;;
        *)                     ROS_VERSION="$1" ;;
    esac
    shift
done

case "$KRISLET" in
    none|team1|team2|both) ;;
    *) echo "Invalid --krislet value: '$KRISLET' (expected none|team1|team2|both)"; exit 1 ;;
esac

if ! [[ "$KRISLET_PERIOD" =~ ^[0-9]*\.?[0-9]+$ ]] || awk "BEGIN{exit !($KRISLET_PERIOD <= 0)}"; then
    echo "Invalid --krislet-period value: '$KRISLET_PERIOD' (expected a positive number of seconds)"
    exit 1
fi

PLATFORM=$(uname -m)
case "$PLATFORM" in
    arm64|aarch64) ARCH="linux/arm64" ;;
    x86_64)        ARCH="linux/amd64" ;;
    *)             ARCH="linux/amd64" ;;
esac

cleanup() {
    echo "Stopping containers..."
    docker stop $CONTAINER >/dev/null 2>&1
    docker rm $CONTAINER >/dev/null 2>&1
}

compile() {
    echo "Compiling rcss..."
    docker build \
        --platform $ARCH \
        --build-arg ROS_DISTRO=${ROS_VERSION} \
        --build-arg ARCH=$ARCH \
        -t rcss .
}

run() {
    echo "Running rcss... (krislet=$KRISLET, krislet_period=${KRISLET_PERIOD}s, auto_launch=$LAUNCH)"
    docker rm -f $CONTAINER >/dev/null 2>&1
    trap cleanup SIGINT SIGTERM EXIT

    OS="$(uname -s)"
    DOCKER_ARGS=(
        --name $CONTAINER
        --platform $ARCH
        -p 9090:9090
        --env "KRISLET=$KRISLET"
        --env "KRISLET_PERIOD=$KRISLET_PERIOD"
    )

    case "$OS" in
        Darwin)
            echo "[INFO] Detected macOS (XQuartz mode)"

            # allow XQuartz connections
            xhost +local:
            xhost +127.0.0.1

            DOCKER_ARGS+=(
                --env DISPLAY=host.docker.internal:0
                --env QT_X11_NO_MITSHM=1
                --env XAUTHORITY=/tmp/.Xauthority
                --volume /tmp/.X11-unix:/tmp/.X11-unix:rw
                --volume $HOME/.Xauthority:/tmp/.Xauthority:rw
            )
            ;;
        Linux)
            echo "[INFO] Detected Linux"

            xhost +local:docker

            DOCKER_ARGS+=(
                --env DISPLAY=$DISPLAY
                --env QT_X11_NO_MITSHM=1
                --volume /tmp/.X11-unix:/tmp/.X11-unix:rw
                --volume $HOME/.Xauthority:/root/.Xauthority:rw
            )
            ;;
        *)
            echo "[WARN] Unsupported OS: $OS. Running without GUI support."
            ;;
    esac

    if [ "$LAUNCH" = "1" ]; then
        # The entrypoint sources ROS and then execs this command as the main process
        local CMD=(ros2 launch ros2_rcss rcss.launch.py "krislet:=$KRISLET" "krislet_period:=$KRISLET_PERIOD" "${LAUNCH_ARGS[@]}")
        echo "[INFO] ${CMD[*]}"
        echo "[INFO] Ctrl-C to stop. Another shell: docker exec -it $CONTAINER bash"
        docker run -it "${DOCKER_ARGS[@]}" rcss "${CMD[@]}"
    else
        docker run -it "${DOCKER_ARGS[@]}" rcss
    fi
}

case "$MODE" in
    --compile)
        compile
        ;;
    --run)
        run
        ;;
    --all)
        compile && run
        ;;
    *)
        usage
        ;;
esac
