#!/bin/bash


function setup_pipenv_environment {
  function pipenv_environment_script_exit {
    if [[ ! ${NO_CLEAN} ]]; then
      echo "=> Cleanup virtual environment files"
      pipenv --rm >/dev/null 2>&1
    fi

    popd >/dev/null || exit
  }
  trap pipenv_environment_script_exit EXIT

  echo "=> Updating virtual environment (might initialize) please wait"
  pipenv update >/dev/null 2>&1
}

function setup_database_environment {
  function database_environment_script_exit {
    pushd "${DIR}/.." >/dev/null || exit
    if [[ ${DOCKER_STOP} ]]; then
      docker-compose stop "${SERVICE_DATABASE_POSTGRES}"
    fi
    popd >/dev/null || exit
    popd >/dev/null || exit
  }
  trap database_environment_script_exit EXIT

  pushd "${DIR}/.." >/dev/null || exit
  export "$(grep "^SERVICE_DATABASE_POSTGRES=" .env)"
  if [[ $(docker-compose ps "${SERVICE_DATABASE_POSTGRES}" | grep -E "^.*_${SERVICE_DATABASE_POSTGRES}_.* Exit [0-9]+") ]]; then
    docker-compose up -d "${SERVICE_DATABASE_POSTGRES}"
    DOCKER_STOP=1
    echo "=> Waiting for database to get ready"
    while ! </dev/tcp/localhost/5432; do sleep 1; done
  fi
  popd >/dev/null || exit
}

function setup_basic_environment {
  function basic_environment_script_exit {
    popd >/dev/null || exit
  }
  trap basic_environment_script_exit EXIT
}
