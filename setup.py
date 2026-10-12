from setuptools import setup
from glob import glob
import os

package_name = 'ri_a1'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'resource'), glob('resource/*')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.wbt')),
        (os.path.join('share', package_name, 'worlds', 'protos'), glob('worlds/protos/*.proto')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='User',
    maintainer_email='user@example.com',
    description='Multi-robot Webots simulation with ROS 2',
    license='MIT',
    entry_points={
        'console_scripts': [
            'controller = ri_a1.controller:main',
        ],
    },
)