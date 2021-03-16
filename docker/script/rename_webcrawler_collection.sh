#!/bin/bash

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
pushd "${DIR}" >/dev/null || exit
source common.sh
setup_basic_environment

if [[ ! ${1} ]] || [[ ! ${2} ]]; then
	echo "Missing parameter for webcrawler old and/or new collection basepath."
	echo "${0} OLD_BASEPATH NEW_BASEPATH"
	exit 1
fi

RANDOM_FILENAME="${RANDOM}.sql"

cat >"/tmp/${RANDOM_FILENAME}.sql" <<EOL
UPDATE image
SET path = REGEXP_REPLACE(path, '^${1}/', '${2}/')
WHERE collectionid IN (
  SELECT id
  FROM collection
  WHERE basepath = '${1}'
);
UPDATE collection
SET basepath = '${2}'
WHERE basepath = '${1}';
EOL

bash run_sql_script.sh "/tmp/${RANDOM_FILENAME}.sql"

rm "/tmp/${RANDOM_FILENAME}.sql"

echo "Remember to rename the webcrawler media folder too!"
