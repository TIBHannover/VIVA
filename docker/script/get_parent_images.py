import argparse
import os
import re
from typing import List

import dotenv
import yaml

RE_VARIABLE_MATCH = re.compile(r"\${(\w+)}")
RE_DOCKERFILE_PARENT = re.compile(r"\s*FROM\s+(.*)", re.IGNORECASE)


def _get_parent_images(dockerfile_path: str) -> List[str]:
    with open(dockerfile_path, "r") as r:
        dockerfile_content = r.readlines()
    parent_images = []
    for dockerfile_line in dockerfile_content:
        parent_image_match = re.match(RE_DOCKERFILE_PARENT, dockerfile_line.strip())
        if parent_image_match:
            parent_images.append(parent_image_match.groups()[0])
    return parent_images


def _replace_env_variables(values: list, env_values: dict) -> List[str]:
    for value in values:
        for match in re.findall(RE_VARIABLE_MATCH, value):
            value = value.replace("${{{:s}}}".format(match), env_values[match])
        yield value


def get_service_parent_images(docker_compose_dir: str, docker_compose_service: str,
                              compose_yml: dict = None) -> List[str]:
    # load .env in docker-compose folder
    main_env_values = {}
    if os.path.isfile(os.path.join(docker_compose_dir, ".env")):
        main_env_values = dotenv.dotenv_values(dotenv_path=os.path.join(docker_compose_dir, ".env"))

    if not compose_yml:
        with open(os.path.join(docker_compose_dir, "docker-compose.yml"), "r") as f:
            compose_yml = yaml.full_load(f)

    if docker_compose_service in compose_yml['services']:
        s_entries = compose_yml['services'][docker_compose_service]
        if "build" in s_entries:
            s_context = s_entries['build']['context'] if "context" in s_entries['build'] else "."
            s_dockerfile = s_entries['build']['dockerfile'] if "dockerfile" in s_entries['build'] else "Dockerfile"
            s_parent_list = _get_parent_images(os.path.join(docker_compose_dir, s_context, s_dockerfile))
            s_build_envs = {**s_entries['build']['args'], **main_env_values} if "args" in s_entries[
                'build'] else main_env_values
        else:
            s_build_envs = main_env_values
            s_parent_list = [s_entries['image']]
        return list(_replace_env_variables(s_parent_list, s_build_envs))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-dcd', default=os.path.join(".."),
                        help='directory of docker-compose file')
    parser.add_argument('-dcs', required=True, help='docker-compose service name')
    parsed_parameters = parser.parse_args()
    print(get_service_parent_images(parsed_parameters.dcd, parsed_parameters.dcs))
