#!/bin/bash

# This file is provided for deploying a desired version of "VIVA-Tool" in a production environment (target OS is Linux)
# Checkout help parameter for detailed information about parameters
# Since this script file could change on runtime (checkout another commit) it will create a copy of the newest local version and execute it
# For development set environment variable DEVELOPMENT=1 to enable copying this script instead of the current git version

TMP_COPY_DIR="/tmp/vivascript"
VERSION_FILE_SCRIPT="script/generate_version_file.sh"
COMMIT_WARNING_TOO_OLD="4648ab7"
DOCKER_DB_DATA_FOLDER="data/postgres/data"
DOCKER_COMPOSE_DB_SERVICE="postgres"
DOCKER_COMPOSE_BUILD_SCRIPT="script/generate_compose.sh"
DOCKER_COMPOSE_BUILD_ARGS="-t gpu"
FILENAME="$(basename "$(test -L "${0}" && readlink "${0}" || echo "${0}")")"

function print_help {
	echo -e "usage:	./$(basename "${0}")\n" \
			"	 [-nf [-ff]] [-b=<branch name>]\n" \
			"	 [-t=<tag name> | -c=<commit hash>]\n" \
			"	 [-s=<sql file>] [-pu] [-cd]\n" \
			"	 [-l]\n" \
			"\n" \
			"-nf 			do not download objects and refs from remote repository (no fetch)\n" \
			"-ff			fast forward current branch\n" \
			"			(to get current state of git repo when not fetching)\n" \
			"-b <branch name>	branch to checkout (default: master)\n" \
			"-t <tag name>		tag to checkout\n" \
			"-c <commit hash>	commit to checkout\n" \
			"-s <file path>		sql file for execution in database\n" \
			"			(relative to docker folder e.g.: postgres/sample_data.sql)\n" \
			"-du			automatically run the sql scripts for demo users\n" \
			"-cd			clean & init the database\n" \
			"-l			automatically print log after start of containers (CTRL+C to stop)\n" \
			"\n" \
			"This script is intended to run on a production server in production environment only.\n" \
			"This script includes automatically storing and applying a modified env file in the checked out state."
}

function print_message {
	echo -e " => \033[1;33m${1}\033[0m"
}
function print_error {
	echo -e " => \033[0;31m${1}\033[0m"
}

function git_stash_pop {
	if [[ ${GIT_STASH_APPLY} ]]; then
		print_message "Git apply stashed changes"
		if ! git stash pop; then
			read -r -p "Solve the conflict using the following editor to edit the file: " answer
			echo ""
			${answer:-vi} .env
			git add .env
		fi
	fi
}

# make sure that this script runs as a copied script file
EXECUTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
if [[ ${EXECUTION_DIR} != "${TMP_COPY_DIR}" ]]; then
	mkdir -p "${TMP_COPY_DIR}"
	if [[ ${DEVELOPMENT} ]]; then
		cat "${EXECUTION_DIR}/${FILENAME}">"${TMP_COPY_DIR}/${FILENAME}"
	else
		git show origin/master:"docker/script/${FILENAME}">"${TMP_COPY_DIR}/${FILENAME}"
	fi
	chmod u+x "${TMP_COPY_DIR}/${FILENAME}"
	{  # this block protects from modification on runtime
	exec "${TMP_COPY_DIR}/${FILENAME}" -gf "${EXECUTION_DIR}/.." "$@"
	exit $?
	}
else
	rm "$0"
fi

# read parameters
POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case ${key} in
	-gf|--git-folder)
		GIT_FOLDER="$2"
		shift
		shift
	;;
	-nf|--no-fetch)
		NO_FETCH=1
		shift
	;;
	-b|--branch)
		BRANCH="$2"
		shift
		shift
	;;
	-t|--tag)
		TAG="$2"
		shift
		shift
	;;
	-c|--commit)
		COMMIT="$2"
		shift
		shift
	;;
	-ff|--fast-forward)
		FAST_FORWARD=1
		shift
	;;
	-s|--sql-file)
		SQL_FILE="$2"
		shift
		shift
	;;
	-du|--demo-users)
		DEMO_USERS=1
		shift
	;;
	-cd|--clean-database)
		CLEAN_DATABASE=1
		shift
	;;
	-l|--log)
		PRINT_LOG=1
		shift
	;;
	-h|--help)
		print_help
		exit 0
	;;
	*) # unknown option
		POSITIONAL+=("$1")
		shift
	;;
esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

# check parameters
if [[ ! ${GIT_FOLDER} ]] || [[ ! -d ${GIT_FOLDER} ]]; then
	print_error "Fatal: Missing or wrong parameter of automated script routine - did you call it by yourself?"
	print_error "GIT_FOLDER is '${GIT_FOLDER}'"
	print_message "As standalone script you have to provide the path to the docker folder of the cloned repository by using the parameter 'gf' (e.g.: -gf /mnt/hhd1/docker/VIVA-Tool/docker)."
	exit 1
fi
if [[ ! ${BRANCH} ]]; then
	BRANCH="master"
fi
if [[ ${TAG} ]] && [[ ${COMMIT} ]]; then
	print_error "Fatal: You can only checkout either a tag or a commit at the same time (or none of both)."
	exit 1
fi
if [[ ${SQL_FILE} ]] && [[ ! -f ${SQL_FILE} ]]; then
	print_error "Fatal: SQL file not found - exiting"
	exit 1
fi

# change wd to git docker folder
pushd "${GIT_FOLDER}" >/dev/null || exit

# generate docker compose file
print_message "Generate Docker compose file for production environment"
bash "${DOCKER_COMPOSE_BUILD_SCRIPT}" "${DOCKER_COMPOSE_BUILD_ARGS}"

# stop all production environment containers
print_message "Stopping docker containers in production environment"
docker-compose stop

# fetch from and integrate with remote repository
if [[ ! ${NO_FETCH} ]]; then
	print_message "Git fetch"
	git fetch --all --tags
fi

# check for local git changes
if [[ -f "${VERSION_FILE_PATH}" ]]; then
	rm "${VERSION_FILE_PATH}"
fi
git update-index --no-assume-unchanged .env
count_git_changes=$(($(git status --porcelain | wc -l)))
if [[ ${count_git_changes} != 0 ]]; then
	print_message "Git changes found"
	# check if only env file is modified
	if [[ ${count_git_changes} == 1 ]] && [[ $(git status -s | grep -E "M\s+.env") ]]; then
		print_message "Stashing changes of docker/.env file"
		git stash
		GIT_STASH_APPLY=1
	else
		git update-index --assume-unchanged .env
		print_message "Git changes:"
		git status
		git update-index --no-assume-unchanged .env
		print_message "Warning: There were local changes in the git repository."
		read -n 1 -p "Do you want to revert all local changes? [y/n] " answer
		echo ""
		case ${answer:0:1} in
			y|Y)
				read -n 1 -p "All local changes will be lost! Continue? [y/n] " answer
				echo ""
				case ${answer:0:1} in
					y|Y)
						git reset HEAD -- ..
						if [[ $(git status -s | grep "M .env") ]]; then
							git add .env
						fi
						git clean -fd
						git checkout ..
						count_git_changes=$(($(git status --porcelain | wc -l)))
						if [[ ${count_git_changes} == 1 ]] && [[ $(git status -s | grep -E "M  .env") ]]; then
							print_message "Stashing changes of docker/.env file"
							git stash
							GIT_STASH_APPLY=1
						elif [[ ${count_git_changes} != 0 ]]; then
							print_error "Fatal: Unable to reset repository."
							exit 1
						fi
						
					;;
					*)
						print_error "Fatal: Git repository cannot be changed in this state."
						exit 1
					;;
				esac
			;;
			*)
				print_error "Fatal: Git repository cannot be changed in this state."
				exit 1
			;;
		esac
	fi
fi

# check for git difference in commits
if [[ ! ${NO_FETCH} ]]; then
	upstream=${BRANCH:-'@{u}'}
	local=$(git rev-parse @)
	remote=$(git rev-parse "$upstream")
	base=$(git merge-base @ "$upstream")

	if [[ ${local} == "${remote}" ]]; then
		print_message "Git: Up-to-date"
	elif [[ ${local} == "${base}" ]]; then
		print_message "Git: Need to pull"
	elif [[ ${remote} == "${base}" ]]; then
		print_message "Git: Need to push"
		print_message "Push your changes and try again"
		print_error "Fatal: Git repository cannot be updated in this state."
		exit 1
	else
		print_message "Git: Diverged"
		print_error "Fatal: Git repository cannot be updated in this state."
		exit 1
	fi
fi


# checkout
print_message "Git checkout"
# check if specified branch exists
if [[ ! $(git branch --list ${BRANCH}) ]]; then
	git_stash_pop
	print_error "Fatal: The specified branch could not be found."
	exit 1
fi
# check if specified commit/tag exists
# shellcheck disable=SC2086
git_commit_hash=$(git log -n 1 --format="%h" ${COMMIT}${TAG})
if [[ $? != 0 ]]; then
	git_stash_pop
	print_error "Fatal: The specified commit/tag could not be found."
	exit 1
fi
if [[ ${TAG} ]]; then
	COMMIT=${git_commit_hash}
fi
# check if checkout commit is before shell script existed in repository
if [[ ${COMMIT} ]]; then
	commits_ahead=$(($(git rev-list --boundary "${COMMIT}" --not ${COMMIT_WARNING_TOO_OLD} | wc -l)))
	if [[ ${commits_ahead} == 0 ]]; then
		print_error "Warning: The state of the repository of the checkout commit/tag does not contain this shell script anymore."
		print_error "Special integrated features like version printing (start page) and port specification in env file might not be available!"
		print_error "Watch out for container version incompatibility (mostly postgres)!"
		print_message "Use this command to get the latest local version: 'git show origin/master:\"docker/script/${FILENAME}\"'."
		read -n 1 -p "Continue script now - answer question (eventually applies stash). Continue? [y/n] " answer
		echo ""
		case ${answer:0:1} in
			y|Y)
			;;
			*)
				git_stash_pop
				print_error "Fatal: User abort git checkout."
				exit 1
			;;
		esac
	fi
fi
# do the actual checkout
git checkout ${BRANCH}
if [[ ! ${NO_FETCH} ]] || [[ ${FAST_FORWARD} ]]; then
	git merge --ff-only
	if [[ $? != 0 ]]; then
		git_stash_pop
		print_error "Fatal: Git repository cannot be merged (fast-forward) in this state."
		exit 1
	fi
fi
if [[ ${COMMIT} ]]; then
	git checkout ${COMMIT}
fi

# apply stashed changes
git_stash_pop

# clean / init database
if [[ ${CLEAN_DATABASE} ]]; then
	print_message "Cleaning database ..."
	print_message "Delete database folder (requires root)"
	sudo rm -rf "${DOCKER_DB_DATA_FOLDER}"
	print_message "Reinit database"
	docker-compose -f compose/init.yml up --abort-on-container-exit
	bash script/run_sql_script.sh "sql/base_init.sql"
fi

# execute sql script
if [[ ${SQL_FILE} ]]; then
	print_message "Execute SQL file in database container"
	docker-compose up -d ${DOCKER_COMPOSE_DB_SERVICE}
	sleep 5  # short break - container service startup ...
	docker cp "${SQL_FILE}" "$(docker-compose ps -q ${DOCKER_COMPOSE_DB_SERVICE})":/tmp/tmp.sql
	docker exec -it "$(docker-compose ps -q ${DOCKER_COMPOSE_DB_SERVICE})" bash -c "psql dradb dra -f /tmp/tmp.sql"
	docker-compose stop ${DOCKER_COMPOSE_DB_SERVICE}
fi

# create version info file
print_message "Generate version info file"
# shellcheck disable=SC2086
bash "${VERSION_FILE_SCRIPT}" ${git_commit_hash} ${TAG}

# start all production environment containers
print_message "Starting docker containers in production environment"
if [[ ${PRINT_LOG} ]]; then
	print_message "Showing continuous log output after startup"
	print_message "HINT: To exit the script press CTRL+C once" 
fi
docker-compose up -d

# run production users sql file
if [[ ${DEMO_USERS} ]]; then
	print_message "Execute SQL files for demo users"
	sleep 3
	bash script/run_sql_script.sh "sql/users_development.sql"
	bash script/run_sql_script.sh "sql/users_additional_demo.sql"
fi

# print log output
if [[ ${PRINT_LOG} ]]; then
	docker-compose logs -f
fi

# return to original wd
popd >/dev/null || exit
