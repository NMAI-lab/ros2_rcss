import os
from glob import glob
from setuptools import setup

package_name = 'ros2_rcss'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['config/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Include the config files.
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
        # Include the launch files.
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Bardia Parmoun',
    maintainer_email='bardiaparmoun@sce.carleton.ca',
    description='A ROS2 client for the RoboCup Soccer 2D Simulation',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'rcss_client = ros2_rcss.rcss_client:main',
        ],
    },
)
