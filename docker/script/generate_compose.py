import argparse
import os
import sys
from typing import List

import yaml

SERVICES_PRODUCTION = ['django', 'django-rq', 'elastic-search', 'keras', 'nginx', 'postgres', 'postgres-backup',
                       'redis', 'tf-serving', 'face-processing']
SERVICES_DEVELOPMENT = ['django', 'django-rq', 'elastic-search', 'keras', 'postgres', 'redis', 'tf-serving', 'face-processing']
SERVICES_INITIALIZATION = ['django', 'postgres']

DIR_SERVICES = os.path.join("..", "compose", "general")
DIR_SERVICES_WINDOWS = "windows"
ENV_SUBDIR = {
    'production': ["prod"],
    'development_django': ["dev", "dev/django"],
    'development_keras': ["dev", "dev/keras"],
    'development_face': ["dev", "dev/face-processing"],
    'initialization': ["init"],
    'gpu': ["gpu"]
}


def represent_none(self, _):
    return self.represent_scalar('tag:yaml.org,2002:null', '')


yaml.add_representer(type(None), represent_none)


def validate_arguments(parameters: argparse.Namespace):
    if parameters.host != 'linux' and parameters.training == 'gpu':
        print("GPU support is only available for Linux hosts.")
    if parameters.host != 'linux':
        print("Warning: Windows compose files were not tested yet! They might not work!", file=sys.stderr)
    if parameters.init and (parameters.dev or parameters.training == 'gpu'):
        print("Compose for initialization of database ignoring all other arguments except host.")


def string_of_arguments(parameters: argparse.Namespace) -> str:
    result = "Docker host: "
    if parameters.host == 'linux':
        result += "Linux"
    elif parameters.host == 'win-tb':
        result += "Windows - Docker Toolbox"
    elif parameters.host == 'win':
        result += "Windows 10 - Docker App"

    result += "\nEnvironment: "
    if parameters.init:
        result += "initialization of database"
        return result
    if parameters.dev:
        result += "development"
        if parameters.dev == "django":
            result += " (Django)"
        elif parameters.dev == "keras":
            result += " (Keras)"
        else:
            result += " (Face-Processing)"
    else:
        result += "production"

    result += "\nHardware for training: "
    if parameters.host == 'linux' and parameters.training == 'gpu':
        result += "GPU"
    else:
        result += "CPU"
    return result


def generate_general_environment(services: List[str]) -> dict:
    compose = {"version": "2.3", "services": {}}
    for service in services:
        with open(os.path.join(DIR_SERVICES, service + ".yml"), 'r') as r:
            service_yml = yaml.full_load(r)
        compose['services'][service] = service_yml

    return compose


def update_environment_dict(original: dict, update: dict) -> dict:
    for key, value in original.items():
        if key not in update:
            continue
        if isinstance(value, dict):
            original[key] = update_environment_dict(original[key], update[key])
        elif key == "environment" and isinstance(value, list):
            original[key] = combine_environment_lists(original[key], update[key])
        else:
            original[key] = update[key]
    for key, value in update.items():
        if key in original:
            continue
        original[key] = value
    return original


def combine_environment_lists(original: List[str], update: List[str]) -> List[str]:
    result = {}
    for key, value in map(lambda x: x.split('=', 1), original + update):
        result[key] = value
    env_list = []
    for key, value in result.items():
        env_list.append("{:s}={:s}".format(key, value))
    return env_list


def update_environment(compose: dict, service_name: str, service_file: str) -> None:
    if os.path.isfile(service_file):
        with open(service_file, 'r') as r:
            service_yml = yaml.full_load(r)
        compose['services'][service_name] = update_environment_dict(compose['services'][service_name], service_yml)


def convert_ports_for_toolbox(compose: dict) -> None:
    for _, service_entries in compose['services'].items():
        if "ports" in service_entries:
            for i, port_entry in enumerate(service_entries['ports']):
                host_part, remain_part = port_entry.split(":", 1)
                if host_part == "127.0.0.1":
                    service_entries['ports'][i] = remain_part


def add_additional_environment(parameters: argparse.Namespace, compose: dict, services: List[str]) -> None:
    env_dirs = ENV_SUBDIR["initialization"]
    if not parameters.init:
        if parameters.dev:
            if parameters.dev == "django":
                env_dirs = ENV_SUBDIR["development_django"]
            elif parameters.dev == "keras":
                env_dirs = ENV_SUBDIR["development_keras"]
            else:
                env_dirs = ENV_SUBDIR["development_face"]
        else:
            env_dirs = ENV_SUBDIR["production"]
        if parameters.host == 'linux' and parameters.training == 'gpu':
            env_dirs += ENV_SUBDIR["gpu"]

    for service_name in services:
        for env_dir in env_dirs:
            training_hw_service_file = os.path.join(DIR_SERVICES, env_dir, service_name + ".yml")
            update_environment(compose, service_name, training_hw_service_file)
            if parameters.host != 'linux' and env_dir not in ENV_SUBDIR["gpu"]:
                host_service_file = os.path.join(DIR_SERVICES_WINDOWS, service_name + ".yml")
                host_env_service_file = os.path.join(DIR_SERVICES_WINDOWS, env_dir, service_name + ".yml")
                update_environment(compose, service_name, host_service_file)
                update_environment(compose, service_name, host_env_service_file)
                if parameters.host == 'win-tb':
                    convert_ports_for_toolbox(compose)


def add_named_volumes(compose: dict) -> None:
    volumes = set()
    for _, service_entries in compose['services'].items():
        if "volumes" in service_entries:
            for volume_entry in service_entries['volumes']:
                if ":/" in volume_entry:
                    host_part, _ = volume_entry.split(":/", 1)
                    if "/" not in host_part:
                        volumes.add(host_part)

    if len(volumes) != 0:
        compose['volumes'] = {}
        for volume in volumes:
            compose['volumes'][volume] = None


def write_environment(parameters: argparse.Namespace, compose: dict) -> None:
    with open(parameters.output, 'w') as w:
        # header comments
        w.write("# generated compose file - do not edit - changes might get overwritten without notice\n")
        for line in string_of_arguments(parameters).split("\n"):
            w.write("# " + line + " \n")
        # the content
        w.write(yaml.dump(compose))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='generate_compose.sh',
                                     description='Use this script to generate a docker compose file for different '
                                                 'environments and docker hosts.')

    parser.add_argument('-hs', '--host', choices=['linux', 'win-tb', 'win'], default='linux',
                        help='operating system / docker host app: All Linux distributions are handled the same whereas '
                             'on Windows hosts it differs between using the "Docker Toolbox" (win-tb) or the '
                             '"Docker App" (win).')
    parser.add_argument('-d', '--dev', choices=['django', 'keras', 'face'], help='set development environment')
    parser.add_argument('-t', '--training', choices=['cpu', 'gpu'], default='cpu',
                        help='hardware on which the neural net should be trained')
    parser.add_argument('-i', '--init', action='store_true', help='initialization of the database')
    parser.add_argument('-o', '--output', default=os.path.join("..", "docker-compose.yml"),
                        help='file to write compose content'),
    parser.add_argument('-nc', '--no-clean', action='store_true',
                        help='do not cleanup the virtual environment after execution')

    parsed_parameters = parser.parse_args()
    validate_arguments(parsed_parameters)
    print(string_of_arguments(parsed_parameters))

    selected_services = SERVICES_INITIALIZATION if parsed_parameters.init else \
        SERVICES_PRODUCTION if not parsed_parameters.dev else \
        SERVICES_DEVELOPMENT

    compose_content = generate_general_environment(selected_services)
    add_additional_environment(parsed_parameters, compose_content, selected_services)
    add_named_volumes(compose_content)
    write_environment(parsed_parameters, compose_content)
