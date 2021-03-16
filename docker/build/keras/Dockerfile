ARG TAG_TENSORFLOW
ARG TAG_GPU
FROM tensorflow/tensorflow:${TAG_TENSORFLOW}${TAG_GPU}

# TAG_TENSORFLOW is specified again because the FROM directive resets ARGs
ARG TAG_TENSORFLOW

# install postgres config for psycopg2
RUN apt-get update && apt-get install --no-install-recommends -y libpq-dev

# install pipenv
RUN pip3 install pipenv==2018.11.26

# install missing packages for - do not install TensorFlow again
COPY Pipfile .
COPY Pipfile.lock .
# write out existing Python packages
RUN pip freeze | sed 's/^\([^=]*==\).*/\1/g' > /tmp/python-packages.txt
# write out the diff of Python packages required by pipfile excluding already installed packages (file generated step before)
RUN pipenv lock --requirements | grep -o -E "^\S*==\S*" | grep -v "^tensorflow==" | grep -viFf /tmp/python-packages.txt > /tmp/requirements.txt
# add exact tensorflow Python package version (of parent image) since otherwise a different version of TF will be installed by a dependency
RUN echo "tensorflow==${TAG_TENSORFLOW}" >> /tmp/requirements.txt
# install packages
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# remove pipenv
RUN pipenv --rm
RUN rm Pipfile Pipfile.lock

# uninstall pipenv
RUN pip3 uninstall -y pipenv

# remove caches
RUN rm -rf /var/lib/apt/lists/* \
 && rm -rf ~/.cache ~/.local

EXPOSE 8080
