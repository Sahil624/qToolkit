#!/bin/bash
# Create a timestamped support bundle (logs + Redis dumps) for survey/test users.
# Use this to collect data from test users for traceback and usage analysis.
# Output is written to the log directory; copy out with:
#   docker cp qeducation-toolkit:/home/toolkit/logs/toolkit-support-bundle-YYYYMMDD-HHMMSS.tar.gz ./

LOG_DIR="${LOG_DIR:-/home/toolkit/logs}"
STAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE="${LOG_DIR}/toolkit-support-bundle-${STAMP}.tar.gz"
BUNDLE_DIR="${LOG_DIR}/.bundle-${STAMP}"
REDIS_DUMP_DIR=""

rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}"

if [ ! -d "$LOG_DIR" ]; then
  echo "Log directory not found: $LOG_DIR"
  exit 1
fi

# Copy log files
cp -a "${LOG_DIR}"/*.log "${BUNDLE_DIR}/" 2>/dev/null || true

# Find and copy Redis persistence (dump.rdb and related)
# Redis Stack may use CONFIG dir, or default /var/lib/redis-stack or current dir
if command -v redis-cli >/dev/null 2>&1; then
  REDIS_DIR=$(redis-cli CONFIG GET dir 2>/dev/null | tail -n1)
  if [ -n "$REDIS_DIR" ] && [ -d "$REDIS_DIR" ]; then
    REDIS_DUMP_DIR="$REDIS_DIR"
  fi
fi
if [ -z "$REDIS_DUMP_DIR" ]; then
  for d in /var/lib/redis-stack /var/lib/redis /data /home/toolkit; do
    [ -d "$d" ] || continue
    [ -f "${d}/dump.rdb" ] || [ -f "${d}/appendonly.aof" ] && REDIS_DUMP_DIR="$d" && break
  done
fi
if [ -n "$REDIS_DUMP_DIR" ]; then
  mkdir -p "${BUNDLE_DIR}/redis-data"
  for f in "${REDIS_DUMP_DIR}"/*.rdb "${REDIS_DUMP_DIR}"/*.aof; do
    [ -f "$f" ] && cp -a "$f" "${BUNDLE_DIR}/redis-data/"
  done
fi

# Create tarball
cd "${LOG_DIR}"
tar -czf "$ARCHIVE" -C "${BUNDLE_DIR}" .
cd - > /dev/null
rm -rf "${BUNDLE_DIR}"

echo "Support bundle exported to: ${ARCHIVE}"
echo "  (includes logs and Redis dumps for traceback/usage analysis)"
echo ""
echo "To copy to your computer, run from the host:"
echo "  docker cp qeducation-toolkit:${ARCHIVE} ./"
echo ""
echo "If you mounted a volume (e.g. -v ./logs:/home/toolkit/logs), the file is already in that folder."
