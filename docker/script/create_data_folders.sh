#!/bin/bash

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
pushd "${DIR}" >/dev/null || exit
source common.sh
setup_basic_environment

mkdir -p ../data
cd ../data || exit
mkdir -p  concept-classification/logs concept-classification/models django elasticsearch export face-processing/index face-processing/models face-processing/models/embeddings face-processing/models/training face-processing/models/classifier nginx postgres/backup postgres/data postgres/transfer redis
