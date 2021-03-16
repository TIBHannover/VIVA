#!/bin/bash

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
pushd "${DIR}" >/dev/null || exit
source common.sh
setup_basic_environment

chown -R 1000 ../data/elasticsearch
