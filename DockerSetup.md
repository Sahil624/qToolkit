# Docker Setup: Toolkit and Simulator

## Combined single-container run (toolkit + q-sim)

The project can run the **Quantum Education Toolkit** (Jupyter Lab) and the **q-sim simulator** in one container. Use this for a single deployment or for exercises that embed or link to the simulator.

### Build (with q-sim submodule)

```bash
git submodule update --init q-sim
docker compose build
```

### Run

```bash
docker compose up
```

- **Jupyter Lab**: http://localhost:8888  
- **Simulator UI**: http://localhost:8001  

The startup script in the container starts Redis, the q-sim Python API, Caddy (simulator UI + API proxy), and finally Jupyter. The terminal stays clean; all service output is written to log files.

### Logs (viewing and exporting)

Service logs are written to **`/home/toolkit/logs/`** inside the container (`redis.log`, `simulator.log`, `caddy.log`, `jupyter.log`). The terminal only shows a short banner with URLs and log instructions.

**If something goes wrong (e.g. for a student or support):**

- **View recent log lines** (last 50 lines of each file):
  ```bash
  docker exec qeducation-toolkit /home/toolkit/view-logs.sh
  ```
  To see more lines: `docker exec qeducation-toolkit /home/toolkit/view-logs.sh 200`

- **Export a support bundle** (logs + Redis dumps) for traceback or usage analysis (e.g. from survey/test users):
  ```bash
  docker exec qeducation-toolkit /home/toolkit/export-support-bundle.sh
  ```
  This creates a timestamped `.tar.gz` in `/home/toolkit/logs/` containing logs and Redis persistence data. Copy it to the host:
  ```bash
  docker cp qeducation-toolkit:/home/toolkit/logs/toolkit-support-bundle-YYYYMMDD-HHMMSS.tar.gz ./
  ```

**Optional:** To have logs on the host automatically, add a bind mount in `docker-compose.yaml` under `volumes`: `- ./logs:/home/toolkit/logs`. Then `./logs` on the host will contain the log files and any exported tarballs.

### Environment: `SIMULATOR_HOST`

Notebooks and course code that embed or link to the simulator should use the **`SIMULATOR_HOST`** environment variable so the URL is configurable.

- **Meaning**: Base URL of the simulator UI (e.g. `http://localhost:8001`). No trailing slash.
- **Default** (when unset): `http://localhost:8001` — suitable for local dev when the simulator runs on port 8001.
- **In the combined Docker setup**: Set to `http://localhost:8001` so the browser can load the simulator on the same host.

**In Python (e.g. in a notebook):**

```python
from pyfiles.simulator_url import get_simulator_url

# Base URL (e.g. http://localhost:8001)
url = get_simulator_url()

# With a path (e.g. http://localhost:8001/labs/bb84)
url = get_simulator_url("labs/bb84")

# Embed in an iframe
from IPython.display import IFrame
IFrame(src=get_simulator_url(), width="100%", height=800)
```

**Override when needed**

- If you access the stack from another machine, set `SIMULATOR_HOST` to the URL the browser should use (e.g. `http://<host-ip>:8001`).
- In `docker-compose.yaml` you can set `SIMULATOR_HOST` in the service `environment` section.

## Toolkit-only run (existing image behavior)

To run only the toolkit (no simulator) from the same image, you can override the entrypoint and run the original Jupyter script:

```bash
docker run --rm -p 8888:8888 -v $(pwd)/content:/home/toolkit/content \
  --entrypoint /home/toolkit/.run_notebook.sh \
  <image-name>
```

## Development: toolkit and simulator separately

- Run the **toolkit** (Jupyter) on your machine as usual (e.g. from the repo root or `course/`).
- Run the **simulator** (q-sim) via its own `docker compose` in `q-sim/`, or run the q-sim server and UI locally.
- Leave `SIMULATOR_HOST` unset; the default `http://localhost:8001` is used so notebooks can open the simulator at that URL.
