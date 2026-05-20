#!/bin/bash

ROS_VERSION=${2:-humble}

PLATFORM=$(uname -m)
case "$PLATFORM" in
    arm64|aarch64) ARCH="linux/arm64" ;;
    x86_64)        ARCH="linux/amd64" ;;
    *)             ARCH="linux/amd64" ;;
esac

compile() {
    echo "Compiling rcss..."
    docker build \
        --platform $ARCH \
        --build-arg ROS_DISTRO=${ROS_VERSION} \
        --build-arg ARCH=$ARCH \
        -t rcss .
}

run() {
    echo "Running rcss..."
    docker rm rcss 2>/dev/null

    OS="$(uname -s)"

    case "$OS" in
        Darwin)
            echo "[INFO] Detected macOS (XQuartz mode)"

            # allow XQuartz connections
            xhost +local:
            xhost +127.0.0.1

            docker run --name rcss -it \
                --env DISPLAY=host.docker.internal:0 \
                --env QT_X11_NO_MITSHM=1 \
                --env XAUTHORITY=/tmp/.Xauthority \
                --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
                --volume $HOME/.Xauthority:/tmp/.Xauthority:rw \
                --platform $ARCH \
                -p 9090:9090 \
                rcss
            ;;
        Linux)
            echo "[INFO] Detected Linux"

            xhost +local:docker

            docker run --name rcss -it \
                --env DISPLAY=$DISPLAY \
                --env QT_X11_NO_MITSHM=1 \
                --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
                --volume $HOME/.Xauthority:/root/.Xauthority:rw \
                --platform $ARCH \
                -p 9090:9090 \
                rcss
            ;;
        *)
            echo "[WARN] Unsupported OS: $OS. Running without GUI support."
            docker run --name rcss -it -p 9090:9090 rcss
    esac
}

case "$1" in
    --compile)
        compile
        ;;
    --run)
        run
        ;;
    --all)
        compile
        run
        ;;
    *)
        echo "Usage: $0 {--compile|--run|--all} [ros_distro]"
        exit 1
        ;;
esac