#!/bin/bash

VERSION_FILE_PATH="app/base/static/version.info"

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
pushd "${DIR}" >/dev/null || exit
source common.sh
setup_basic_environment

cd "$(git rev-parse --show-toplevel)" || exit

# check parameters
if [[ $# -eq 0 ]]; then
  echo "Not enough parameters! Parameters: <COMMIT_HASH> [<TAG>]"
  echo "Or use the following parameter to delete: -rm"
  exit 1
fi
commit="$1"
if [[ $# -gt 1 ]]; then
  tag="$2"
fi

if [[ ${commit} == "-rm" ]]; then
  rm "${VERSION_FILE_PATH}"
  exit 0
fi

# create version info file
git log -n 1 --format="%h" "${commit}" >"${VERSION_FILE_PATH}"
git log -n 1 --format="%B" "${commit}" | head -n 1 >>"${VERSION_FILE_PATH}"
git log -n 1 --format="%an%n%at" "${commit}" >>"${VERSION_FILE_PATH}"
if [[ ${tag} ]]; then
	echo -e "${tag}">>"${VERSION_FILE_PATH}"
fi
