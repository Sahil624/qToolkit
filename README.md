# Quantum Education Toolkit

Run the Quantum Education Toolkit and simulator in one place using Docker. No need to install Python or Node.js on your computer.

---

## Prerequisites

You only need **Docker** installed. Nothing else.

---

## 1. Install Docker

Install Docker for your operating system using the official guide:

- **All platforms (recommended):** [Get Docker](https://docs.docker.com/get-docker/) — this page helps you pick the right version.
- **Windows:** [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **macOS:** [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Linux:** [Docker Engine for Linux](https://docs.docker.com/engine/install/) or [Docker Desktop for Linux](https://docs.docker.com/desktop/install/linux-install/)

After installation, open Docker Desktop (on Windows or Mac) or start the Docker service (on Linux). Make sure Docker is running before the next steps.

---

## 2. Download the release

1. Go to **Releases**: [https://github.com/Sahil624/qToolkit/releases](https://github.com/Sahil624/qToolkit/releases)
2. Open the **latest release** (top of the list).
3. Download the **zip file** attached to that release (for example, `qToolkit-v1.0.0.zip`).

**Important:** Use the zip file attached to the release, not the "Source code (zip)" button on the main repo page. The release zip includes everything needed to run the toolkit (including the simulator).

---

## 3. Unzip the file

Unzip the downloaded file to a folder you can find easily (for example, Desktop or Documents). Remember where you put it — you will open that folder in the next step.

---

## 4. Open a terminal in that folder

- **Windows:** Open Command Prompt or PowerShell. Use `cd` to go to the folder where you unzipped the file, for example:
  ```text
  cd C:\Users\YourName\Desktop\qToolkit-v1.0.0
  ```
  (Replace with your actual path and folder name.)

- **Mac:** Open Terminal. Use `cd` to go to the folder, for example:
  ```text
  cd ~/Desktop/qToolkit-v1.0.0
  ```

- **Linux:** Open Terminal and `cd` to the folder where you unzipped the file.

---

## 5. Build and run with Docker

In the same terminal, run:

**First time (build the image):**
```bash
docker compose build
```

**Start the toolkit:**
```bash
docker compose up
```

Or do both in one step:
```bash
docker compose up --build
```

Wait until you see a short message with two web addresses (URLs). That means the toolkit is ready.

---

## 6. Use the toolkit in your browser

Open your web browser and go to:

- **Jupyter Lab (notebooks and course):** [http://localhost:8888](http://localhost:8888)
- **Simulator:** [http://localhost:8001](http://localhost:8001)

You can use both at the same time.

---

## 7. Stop the toolkit

- In the terminal where `docker compose up` is running, press **Ctrl+C** to stop it.
- If you want to stop and remove the container completely, run:
  ```bash
  docker compose down
  ```

---

## Need help?

- For **logs, support bundle export, and troubleshooting**, see [DockerSetup.md](DockerSetup.md).
- If something goes wrong, you can export a support bundle (logs and data) and share it; instructions are in DockerSetup.md.
