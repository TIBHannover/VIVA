#!/bin/bash

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
pushd "${DIR}" >/dev/null || exit
source common.sh

PARAMS="$@"
while [[ $# -gt 0 ]]; do
key="$1"
case ${key} in
  -nc|--no-clean)
    NO_CLEAN=1
    shift
  ;;
  *) # unknown option
    shift
  ;;
esac
done

setup_pipenv_environment

echo "=> Running command in virtual environment ..."
pipenv run python generate_compose.py ${PARAMS}
