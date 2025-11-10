# =================================================================
# Stage 1: JavaScript & Game Asset Builder
# This stage builds all necessary JS projects.
# =================================================================
FROM node:20-slim as builder

WORKDIR /app

# Copy all game-related source files into the builder
COPY ./games/ ./games/

# --- Build 'ozma' ---
WORKDIR /app/games/ozma
RUN npm install && npm run build

# --- Build 'snake_n_ladders' ---
WORKDIR /app/games/snake_n_ladders
RUN npm install && node build.js
# The 'dist' folders for both games are now built within this stage.
# The static HTML file is also present.


# =================================================================
# Stage 2: Plugin Builder
# =================================================================
FROM nikolaik/python-nodejs as plugin-builder

WORKDIR /plugin


RUN npm install -g jupyterlab
RUN pip install jupyterlab
COPY ./.plugins/edu_agent_plugin ./edu_agent_plugin

WORKDIR /plugin/edu_agent_plugin

# Install and build the plugin
RUN npm install
RUN npm run build:lib
RUN npm run build:labextension


# =================================================================
# Stage 3: Final Python Application
# This is final image, which will receive the built assets.
# =================================================================
FROM python:latest

# Install OS dependencies
RUN apt-get -y update && \
    apt-get install -y build-essential git cmake libssl-dev

# Get and install liboqs
RUN git clone --depth 1 --branch main https://github.com/open-quantum-safe/liboqs && \
    cmake -S liboqs -B liboqs/build -DBUILD_SHARED_LIBS=ON && \
    cmake --build liboqs/build --parallel 4 && \
    cmake --build liboqs/build --target install

WORKDIR /home/oqs_source
ENV LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"

# Get and install liboqs-python
RUN git clone --depth 1 --branch main https://github.com/open-quantum-safe/liboqs-python.git /home/oqs_source/liboqs-python
WORKDIR /home/oqs_source/liboqs-python
RUN pip install .

WORKDIR /home/toolkit

# 1. Copy the built game assets from the 'builder' stage.
# This includes the 'dist' folders and the static HTML file.
COPY --from=builder /app/games/ ./games/
COPY --from=builder /app/games/ ./course/games/

# 2. Copy the rest of application code from local machine.
COPY content ./content
COPY master.ipynb master.ipynb
COPY init.py init.py
COPY data data
COPY course/index.ipynb course/index.ipynb
COPY course/generate_course.ipynb course/generate_course.ipynb
COPY course/pyfiles course/pyfiles
COPY .project_root course/.project_root

# Keep un-necessary files hidden
COPY requirements.txt .requirements.txt
COPY run_notebook.sh .run_notebook.sh
RUN chmod +x .run_notebook.sh

# 3. Copy and install chat plugin.
COPY --from=plugin-builder /plugin/edu_agent_plugin ./.plugins/edu_agent_plugin
RUN pip install -r .requirements.txt

RUN pip install ./.plugins/edu_agent_plugin

EXPOSE 8888
VOLUME ["/home/toolkit/content"]
CMD ["/home/toolkit/.run_notebook.sh"]