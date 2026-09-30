"""Start llama-server as a ROS 2 launch process"""

import shlex

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import ExecutableInPackage


FLAGS = {
    'model':        '--model',
    'hf_repo':      '--hf-repo',
    'host':         '--host',
    'port':         '--port',
    'n_gpu_layers': '--n-gpu-layers',
    'ctx_size':     '--ctx-size',
}


def _start_server(context):
    command = [ExecutableInPackage('llama-server', 'llama_server_vendor')]

    for argument_name, flag in FLAGS.items():
        value = LaunchConfiguration(argument_name).perform(context)

        if value:
            command += [flag, value]

    extra_args = LaunchConfiguration('extra_args').perform(context)
    command += shlex.split(extra_args)

    return [
        ExecuteProcess(
            cmd=command,
            name='llama_server',
            output='screen'
        )
    ]


def generate_launch_description():
    arguments = [
        DeclareLaunchArgument(argument_name, default_value='')
        for argument_name
        in FLAGS
    ]

    arguments.append(
        DeclareLaunchArgument(
            'extra_args',
            default_value='',
            description='More llama-server args'
        )
    )

    return LaunchDescription(arguments + [OpaqueFunction(function=_start_server)])
