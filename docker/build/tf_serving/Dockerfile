ARG TAG_TENSORFLOW
ARG TAG_GPU
FROM tensorflow/serving:${TAG_TENSORFLOW}${TAG_GPU}

RUN mkdir -p /var/cache/apt/archives/partial

# install python3.7 for simple http server
RUN apt-get update && apt-get install --no-install-recommends -y curl gnupg && . /etc/os-release && \
    curl -s -L "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xba6932366a755776" | apt-key add - && \
    echo "deb http://ppa.launchpad.net/deadsnakes/ppa/ubuntu ${UBUNTU_CODENAME} main" > "/etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-${UBUNTU_CODENAME}.list" && \
    apt-get install --no-install-recommends -y python3.7 && \
    apt-get purge -y curl && \
    rm -rf /etc/apt/sources.list.d/* && rm -rf /var/lib/apt/lists/*

# remove serving entrypoint
ENTRYPOINT []

EXPOSE 8000 8500-8516
