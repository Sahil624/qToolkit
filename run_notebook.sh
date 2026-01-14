#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down Jupyter Lab..."
    kill $JUPYTER_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Disable jupyter news letter popup
jupyter labextension disable "@jupyterlab/apputils-extension:announcements"

# check if course/data folder is empty/ non-existent. If yes, copy vector data and metadata from root folder to course folder
if [ ! -d "course/data" ] || [ -z "$(ls -A course/data 2>/dev/null)" ]; then
    echo "Copying data files to course/data..."
    mkdir -p course/data/vector_db
    cp data/vector_db/faiss.index course/data/vector_db
    cp data/vector_db/metadata.pkl course/data/vector_db
    echo "Data files copied successfully."
else
    echo "course/data folder already has data. Skipping copy."
fi

# Start Jupyter Notebook server
cd course && jupyter lab index.ipynb --ip=0.0.0.0 --port=8888 --no-browser --NotebookApp.token="" --show_tracebacks=True --allow-root --debug &
JUPYTER_PID=$!

# Wait for Jupyter to start
sleep 5

echo ""
echo ""
echo "******************************************************************"
echo "******************************************************************"
echo "**                                                              **"
echo "**  QUANTUM TOOLKIT LEARNING LAB ENVIRONMENT IS RUNNING         **"
echo "**                                                              **"
echo "**  CHECK USAGE INSTRUCTIONS IN DockerSetup.md                  **"
echo "**  Open http://127.0.0.1:8888/voila/render/index.ipynb         **"
echo "**    OR use whichever port is used                             **"
echo "**                                                              **"
echo "**  TO STOP THIS ENVIRONMENT: Press CTRL+C                      **"
echo "**                                                              **"
echo "******************************************************************"
echo "******************************************************************"
echo ""
echo ""

# Keep the script running to see the container logs
wait $JUPYTER_PID