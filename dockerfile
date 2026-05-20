ARG ROS_DISTRO=humble 
ARG ARCH=linux/amd64

FROM --platform=${ARCH} ros:${ROS_DISTRO}-ros-base

ARG ROS_DISTRO=humble

ENV ROS_DISTRO=${ROS_DISTRO}
ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-c"]

# Install additional packages
RUN apt update && apt install -y \
    python3-rosdep \
    bison \
    flex \
    netcat \
    libboost-all-dev \
    qtbase5-dev \
    qt5-qmake \
    libqt5widgets5 \
    libqt5opengl5-dev \
    ros-$ROS_DISTRO-rosbridge-server \
    && rm -rf /var/lib/apt/lists/*

# Start rosdep and update
RUN rosdep init || true
RUN rosdep update

# Expose ROS bridge port (default 9090)
EXPOSE 9090

# Create workspace
RUN mkdir -p /root/rcss_ws/src/rcss
WORKDIR /root/rcss_ws/src

# Clone RCSS dependencies
COPY dependencies.repos /root/rcss_ws/src/rcss/dependencies.repos
RUN vcs import /root/rcss_ws/src/ < /root/rcss_ws/src/rcss/dependencies.repos

# Install ROS 2 dependencies
WORKDIR /root/rcss_ws
RUN source /opt/ros/$ROS_DISTRO/setup.bash && \
    rosdep install --from-paths src -yi

WORKDIR /root/rcss_ws

# Build the RCSS core packages
RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build --symlink-install

# Copy the package
COPY ros2_rcss/ /root/rcss_ws/src/rcss/ros2_rcss
COPY ros2_rcss_msgs/ /root/rcss_ws/src/rcss/ros2_rcss_msgs

# Build RCSS ROS wrapper pakages
RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build --symlink-install --packages-select ros2_rcss ros2_rcss_msgs

# Environment setup
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc
RUN echo "source /root/rcss_ws/install/local_setup.bash" >> /root/.bashrc

# Start the container
COPY load_container.sh /root/load_container.sh
RUN chmod +x /root/load_container.sh
ENTRYPOINT ["/bin/bash", "/root/load_container.sh"]

# Default shell
CMD ["bash"]