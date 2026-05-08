#!/bin/bash

while getopts "f" opt; do
    case $opt in
        f) FORCE_COMPILE=true ;;
        *) echo "Usage: $0 [-f] [ROS_VERSION]"; exit 1 ;;
    esac
done
shift $((OPTIND - 1))
ROS_VERSION=${1:-humble}

if [ "$FORCE_COMPILE" = true ]; then
    echo "Compiling..."
    docker build --build-arg ROS_DISTRO=${ROS_VERSION} -t rcss .
fi

echo "Running rcss..."
docker rm rcss 2>/dev/null
xhost +local:docker
docker run --name rcss -it \
    --env DISPLAY=$DISPLAY \
    --env QT_X11_NO_MITSHM=1 \
    --volume /tmp/.X11-unix:/tmp/.X11-unix:rw \
    rcss