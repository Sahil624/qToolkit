#!/bin/bash
# Show recent lines from each log file for debugging.
# Run from host: docker exec qeducation-toolkit /home/toolkit/view-logs.sh
# Or from inside container: /home/toolkit/view-logs.sh

LOG_DIR="${LOG_DIR:-/home/toolkit/logs}"
LINES="${1:-50}"

if [ ! -d "$LOG_DIR" ]; then
  echo "Log directory not found: $LOG_DIR"
  exit 1
fi

echo "=== Last ${LINES} lines of each log (from ${LOG_DIR}) ==="
echo ""

for f in redis simulator caddy jupyter; do
  path="${LOG_DIR}/${f}.log"
  if [ -f "$path" ]; then
    echo "--- ${f}.log ---"
    tail -n "$LINES" "$path"
    echo ""
  else
    echo "--- ${f}.log (not found) ---"
    echo ""
  fi
done
