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
# Stage 1b: q-sim UI Builder (requires q-sim submodule in build context)
# =================================================================
FROM node:18-slim AS q-sim-ui
WORKDIR /app
COPY q-sim/ui/package*.json ./
RUN npm ci
COPY q-sim/ui/ .
RUN npm run build


# =================================================================
# Stage 2a: Redis Stack (for redis_om / RedisJSON in q-sim)
# =================================================================
FROM redis/redis-stack-server:latest AS redis-stack


# =================================================================
# Stage 3: Plugin Builder
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
# Use Python 3.11 to match q-sim and redis-om/pydantic compatibility.
# =================================================================
FROM python:3.11-slim

# Install OS dependencies (Caddy for combined run).
# Redis Stack is copied from the official image (no redis-stack-server package on Debian trixie).
RUN apt-get -y update && \
    apt-get install -y build-essential git cmake libssl-dev curl gpg && \
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https && \
    (curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg) && \
    (curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list) && \
    chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg /etc/apt/sources.list.d/caddy-stable.list && \
    apt-get update && apt-get install -y caddy && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Redis Stack from official image (includes RedisJSON required by q-sim redis_om)
COPY --from=redis-stack /opt/redis-stack /opt/redis-stack
ENV PATH="/opt/redis-stack/bin:${PATH}" \
    LD_LIBRARY_PATH="/opt/redis-stack/lib:${LD_LIBRARY_PATH}"

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

# 2b. q-sim submodule and built UI (for combined container)
COPY q-sim ./q-sim
COPY --from=q-sim-ui /app/dist ./q-sim/ui/dist
RUN pip install --no-cache-dir -r q-sim/requirements.txt

# 2c. Combined container entrypoint, Caddy config, and log helpers
COPY docker/entrypoint.sh /home/toolkit/docker/entrypoint.sh
COPY docker/Caddyfile.combined /home/toolkit/docker/Caddyfile.combined
COPY docker/view-logs.sh /home/toolkit/view-logs.sh
COPY docker/export-support-bundle.sh /home/toolkit/export-support-bundle.sh
RUN chmod +x /home/toolkit/docker/entrypoint.sh /home/toolkit/view-logs.sh /home/toolkit/export-support-bundle.sh

# Keep un-necessary files hidden
COPY requirements.txt .requirements.txt
COPY run_notebook.sh .run_notebook.sh
RUN chmod +x .run_notebook.sh

# 3. Copy and install chat plugin.
COPY --from=plugin-builder /plugin/edu_agent_plugin ./.plugins/edu_agent_plugin
RUN pip install -r .requirements.txt

RUN pip install ./.plugins/edu_agent_plugin

EXPOSE 8888 80
VOLUME ["/home/toolkit/content", "/home/toolkit/logs"]
ENTRYPOINT ["/home/toolkit/docker/entrypoint.sh"]