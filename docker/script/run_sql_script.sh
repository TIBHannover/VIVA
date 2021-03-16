#!/bin/bash

# Execute a provided SQL file
# Works on Windows when using "git bash" - ignore error message "The system can not find the specified path."

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
pushd "${DIR}" >/dev/null || exit
source common.sh
setup_database_environment

cd ..

if [[ ! ${1} ]] || [[ ! -f "${1}" ]]; then
	echo "Missing parameter for script path or provided parameter is not a file path"
	exit 1
fi

docker cp "${1}" "$(docker-compose ps -q "${SERVICE_DATABASE_POSTGRES}")":/tmp/tmp.sql
docker exec -it "$(docker-compose ps -q "${SERVICE_DATABASE_POSTGRES}")" bash -c "psql dradb dra -f /tmp/tmp.sql; rm /tmp/tmp.sql"
