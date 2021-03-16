ARG TAG_PYTHON
FROM python:${TAG_PYTHON}

# Install pipenv
RUN pip3 install pipenv

# Copy pipfile to install missing packages directly on system (pipenv is ONLY used to extract installed packages)
COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv lock --requirements | grep -o -E "^\S*==\S*" | xargs pip3 install
RUN pipenv --rm
RUN rm Pipfile Pipfile.lock

# uninstall pipenv
RUN pip3 uninstall -y pipenv

# install gunicorn (for production)
RUN pip3 install gunicorn

# Remove cached and unnecessary files created
RUN rm -rf ~/.cache ~/.local

# Copy script files
RUN mkdir /scripts
COPY *.sh /scripts/

# Expose http port
EXPOSE 8000
