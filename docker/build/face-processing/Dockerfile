ARG PARENT_IMAGE
FROM ${PARENT_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Install dependencies for dlib
RUN apt update && apt install -y gcc g++ cmake python3-dev libgl1-mesa-glx libglib2.0-0

#Update conda
RUN conda update conda
COPY environment.yml /tmp/environment.yml
RUN mkdir /conda_env

#Setup Conda
RUN conda env create --prefix /conda_env -f /tmp/environment.yml
ENV PATH /conda_env/bin:$PATH
RUN conda run -p /conda_env pip install face-detection
RUN conda run -p /conda_env pip install opencv-python-headless

# Setup directories
RUN mkdir -p /code/scripts
COPY start_face-processing.sh /code/scripts/start_face-processing.sh

WORKDIR /code

#Make RUN commands use the new environment:
#SHELL ["conda", "run", "-n", "face-processing_env", "/bin/bash", "-c"]

EXPOSE 8001
