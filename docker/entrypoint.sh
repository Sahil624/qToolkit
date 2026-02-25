#!/bin/bash
set -e

TOOLKIT_ROOT="${TOOLKIT_ROOT:-/home/toolkit}"
Q_SIM_ROOT="${TOOLKIT_ROOT}/q-sim"
SIMULATOR_UI_DIR="${Q_SIM_ROOT}/ui/dist"
LOG_DIR="${TOOLKIT_ROOT}/logs"

mkdir -p "${LOG_DIR}"

# -----------------------------------------------------------------------------
# 1. Start Redis Stack (includes RedisJSON required by q-sim redis_om)
# -----------------------------------------------------------------------------
redis-stack-server >> "${LOG_DIR}/redis.log" 2>&1 &

for i in $(seq 1 30); do
  if redis-cli ping 2>/dev/null | grep -q PONG; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Redis did not become ready. Check ${LOG_DIR}/redis.log"
    exit 1
  fi
  sleep 0.5
done

# -----------------------------------------------------------------------------
# 2. q-sim .env (required by start.py)
# -----------------------------------------------------------------------------
cat > "${Q_SIM_ROOT}/.env" << EOF
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=
PORT=8000
HOST=0.0.0.0
DEBUG=False
EOF

# -----------------------------------------------------------------------------
# 3. Start q-sim Python server (FastAPI)
# -----------------------------------------------------------------------------
cd "${Q_SIM_ROOT}"
python start.py >> "${LOG_DIR}/simulator.log" 2>&1 &
cd - > /dev/null

for i in $(seq 1 60); do
  if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/health" 2>/dev/null | grep -q 200; then
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "WARNING: q-sim API may not be ready yet. Check ${LOG_DIR}/simulator.log"
  fi
  sleep 0.5
done

# -----------------------------------------------------------------------------
# 4. Start Caddy (simulator UI + proxy to Python)
# -----------------------------------------------------------------------------
if [ ! -d "${SIMULATOR_UI_DIR}" ] || [ -z "$(ls -A "${SIMULATOR_UI_DIR}" 2>/dev/null)" ]; then
  echo "WARNING: q-sim UI not built at ${SIMULATOR_UI_DIR}" >> "${LOG_DIR}/caddy.log"
fi
caddy run --config "${TOOLKIT_ROOT}/docker/Caddyfile.combined" --adapter caddyfile >> "${LOG_DIR}/caddy.log" 2>&1 &

# -----------------------------------------------------------------------------
# 5. Jupyter (background; output to log file)
# -----------------------------------------------------------------------------
cd "${TOOLKIT_ROOT}"
"${TOOLKIT_ROOT}/.run_notebook.sh" >> "${LOG_DIR}/jupyter.log" 2>&1 &
JUPYTER_PID=$!

# Wait for Jupyter to be up
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8888/" 2>/dev/null | grep -qE '200|302|403'; then
    break
  fi
  sleep 1
done

# -----------------------------------------------------------------------------
# 6. Clean banner and instructions
# -----------------------------------------------------------------------------
echo ""
echo "========================================================================"
echo "  Quantum Education Toolkit is running"
echo "========================================================================"
echo "  Learning Lab:    http://127.0.0.1:8888/voila/render/index.ipynb"
echo "  Simulator:      http://localhost:8001"
echo "------------------------------------------------------------------------"
echo "  Logs are saved in: ${LOG_DIR}/"
echo "  View recent logs:  ${TOOLKIT_ROOT}/view-logs.sh"
echo "  Export support bundle (logs + Redis): ${TOOLKIT_ROOT}/export-support-bundle.sh"
echo "  (From host:        docker exec qeducation-toolkit /home/toolkit/view-logs.sh)"
echo "========================================================================"
echo ""

wait $JUPYTER_PID
