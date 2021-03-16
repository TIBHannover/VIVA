#!/bin/bash

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
pushd "${DIR}" >/dev/null || exit
source common.sh
setup_basic_environment

cd ..

git ls-files -v | grep -E "^h .env$" >/dev/null
if [[ $? != 0 ]]; then
	git update-index --assume-unchanged .env
else
	git update-index --no-assume-unchanged .env
fi
