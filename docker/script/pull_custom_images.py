#!/bin/python3
import argparse
import os
import subprocess

import yaml

from get_parent_images import get_service_parent_images

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='pull_custom_images.sh',
                                     description='Use this script to pull images that are used as parent images defined'
                                                 ' in a docker-compose file (considers custom builds).')
    parser.add_argument('-dcp', default=os.path.join(".."), help='directory of docker-compose file')
    parser.add_argument('-nc', '--no-clean', action='store_true',
                        help='do not cleanup the virtual environment after execution')
    parsed_parameters = parser.parse_args()

    with open(os.path.join(parsed_parameters.dcp, "docker-compose.yml"), "r") as f:
        compose_yml = yaml.full_load(f)

    pulled_service_images = set()
    for s_name, s_entries in compose_yml['services'].items():
        if "build" in s_entries:
            s_parent_images = get_service_parent_images(parsed_parameters.dcp, s_name, compose_yml)
            print(" -", s_name, ":", s_parent_images)
            for s_parent_image in s_parent_images:
                if s_parent_image in pulled_service_images:
                    continue
                else:
                    pulled_service_images.add(s_parent_image)
                subprocess.run(["docker", "pull", s_parent_image])
