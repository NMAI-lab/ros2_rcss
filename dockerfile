FROM ubuntu:22.04

ARG ROS_DISTRO=humble

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=${ROS_DISTRO}

SHELL ["/bin/bash", "-c"]

# Basic dependencies
RUN apt update && apt install -y \
    locales \
    curl \
    gnupg2 \
    lsb-release \
    software-properties-common \
    git \
    wget \
    build-essential \
    cmake \
    python3-pip \
    x11-apps \
    libgl1-mesa-glx \
    libglu1-mesa \
    freeglut3-dev \
    bison \
    flex \
    && rm -rf /var/lib/apt/lists/*

# Locale
RUN locale-gen en_US en_US.UTF-8

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Add ROS 2 GPG key and repo
RUN curl -sSL http://repo.ros2.org/repos.key | apt-key add - && \
    add-apt-repository universe && \
    echo "deb http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/ros2-latest.list

# Install ROS 2 + tools
RUN apt update && apt install -y \
    ros-$ROS_DISTRO-desktop \
    python3-colcon-common-extensions \
    python3-vcstool \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# rosdep
RUN rosdep init || true
RUN rosdep update

# Create workspace
RUN mkdir -p /root/rcss_ws/src/rcss
WORKDIR /root/rcss_ws/src

# Clone RCSS dependencies
COPY dependencies.repos /root/rcss_ws/src/rcss/dependencies.repos

RUN vcs import /root/rcss_ws/src/ < /root/rcss_ws/src/rcss/dependencies.repos

# Build rcssserver
WORKDIR /root/rcss_ws/src/rcsoccersim/rcssserver

RUN mkdir build && cd build && \
    cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local && \
    make -j$(nproc) && \
    make install

# Build rcssmonitor
WORKDIR /root/rcss_ws/src/rcsoccersim/rcssmonitor

RUN mkdir build && cd build && \
    cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local && \
    make -j$(nproc) && \
    make install

# Ensure binaries exist
RUN which rcssserver && which rcssmonitor

# Copy the package
COPY ros2_rcss/ /root/rcss_ws/src/rcss/ros2_rcss
COPY ros2_rcss_msgs/ /root/rcss_ws/src/rcss/ros2_rcss_msgs

# Build ROS workspace
WORKDIR /root/rcss_ws

RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build --symlink-install

# Environment setup
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc
RUN echo "source /root/rcss_ws/install/local_setup.bash" >> /root/.bashrc


# Default shell
CMD ["bash"]