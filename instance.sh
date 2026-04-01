#!/bin/bash

# --- Configuration ---
BASE_MACHINE_ID=100
BASE_JUPYTER_PORT=9200
BASE_SIM_PORT=12000
COMPOSE_FILE="docker-componse-template.yaml"
REGISTRY_FILE="machine_registry.txt"

# Initialize Registry
if [ ! -f "$REGISTRY_FILE" ]; then
    echo "ID | Machine_Num | Jupyter_Port | Sim_Port | Status | Started_At" > "$REGISTRY_FILE"
    echo "----------------------------------------------------------------" >> "$REGISTRY_FILE"
fi

# Function to check if a port is in use on the host
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 1 # Port is busy
    else
        return 0 # Port is free
    fi
}

update_registry() {
    local status=$1
    sed -i "/^$CURRENT_ID |/d" "$REGISTRY_FILE"
    if [ "$status" != "DELETED" ] && [ "$status" != "STOPPED" ]; then
        echo "$CURRENT_ID | Machine_$MACHINE_NUM | $JUPYTER_PORT | $SIM_PORT | $status | $(date '+%Y-%m-%d %H:%M')" >> "$REGISTRY_FILE"
    fi
}

case $1 in
    start)
        MACHINE_NUM=$2
        [ -z "$MACHINE_NUM" ] && exit 1
        
        CURRENT_ID=$((BASE_MACHINE_ID + MACHINE_NUM))
        JUPYTER_PORT=$((BASE_JUPYTER_PORT + CURRENT_ID))
        SIM_PORT=$((BASE_SIM_PORT + CURRENT_ID))
        PROJECT_NAME="qstack_machine_${CURRENT_ID}"

        echo "🔍 Checking ports $JUPYTER_PORT and $SIM_PORT..."
        
        if ! check_port $JUPYTER_PORT || ! check_port $SIM_PORT; then
            echo "❌ ERROR: Port collision detected. Port $JUPYTER_PORT or $SIM_PORT is already in use."
            echo "   Try a different Machine ID or check 'lsof -i :$JUPYTER_PORT'"
            exit 1
        fi

        echo "🚀 Starting Machine $CURRENT_ID..."
        if JUPYTER_PORT=$JUPYTER_PORT SIM_PORT=$SIM_PORT \
           docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d; then
            update_registry "RUNNING"
            echo "✅ Machine $CURRENT_ID is live."
        else
            echo "❌ Docker failed to start the container."
            exit 1
        fi
        ;;


    stop)
        if [ -z "$MACHINE_NUM" ]; then usage; fi
        echo "Stopping Machine $CURRENT_ID..."
        docker compose -p "$PROJECT_NAME" down
        update_registry "STOPPED"
        ;;

    list)
        column -t -s "|" "$REGISTRY_FILE"
        ;;

    clean)
        # Danger: This removes volumes too (wipes survey data)
        if [ -z "$MACHINE_NUM" ]; then usage; fi
        docker compose -p "$PROJECT_NAME" down -v
        update_registry "DELETED"
        ;;
    *)
        usage
        ;;
esac