# QEducationToolkit Project Summary

## Overview
QEducationToolkit is a comprehensive platform designed for interactive quantum computing and communication education. It integrates a dynamic course generation system with a feature-rich quantum network simulator, allowing students to learn theoretical concepts and experiment with practical simulations.

## High-Level Architecture

The project consists of three main pillars:
1.  **Course Content & Management** (`content/`, `course/`)
2.  **Quantum Network Simulator** (`q-sim/`)
3.  **Entry Points & Tools** (`master.ipynb`, `utils/`)

### 1. Course Content & Management
*   **Source Material (`content/`)**:
    *   The raw educational content is authored in Jupyter Notebooks, organized hierarchically by Units (e.g., *Quantum Foundations*, *Principles of Quantum Communication*).
    *   Each unit contains multiple learning modules (e.g., `the_qbit.ipynb`, `quantum_key_distribution.ipynb`).
*   **Course Generator (`course/`)**:
    *   **Logic**: The core logic resides in `course/pyfiles/course_exporter.py`. This tool allows for the creation of customized courses by selecting specific "Learning Objectives" (LOs).
    *   **Process**: It scans source notebooks, extracts relevant cells based on metadata, injects custom navigation (Previous/Next buttons) and progress tracking scripts, and exports a simplified, linear sequence of notebooks to `generated_course/`.
    *   **UI**: `course/pyfiles/course_selector_ui.py` provides an interface (likely a widget) for instructors to select modules and trigger the generation process.

### 2. Quantum Network Simulator (`q-sim/`)
A standalone interactive simulator for hybrid classical-quantum networks.
*   **Backend (`q-sim/server/`)**:
    *   Built with **FastAPI**.
    *   Manages the simulation state and handles client communication via **WebSockets** (`server/app.py`).
    *   Core components include `ClassicalHost`, `QuantumHost`, `QuantumChannel`, and `QuantumRepeater`.
*   **Frontend (`q-sim/ui/`)**:
    *   A **React**-based web interface (served from `ui/dist`) that visualizes the network topology, packet flow, and qubit states in real-time.
*   **Simulation Engine**:
    *   `q-sim/main.py` demonstrates the setup of a "World" containing multiple "Zones" (Classical and Quantum).
    *   It simulates network traffic, routing, and quantum phenomena like entanglement and teleportation.

### 3. Key Workflows

#### Student Learning Flow
1.  **Access**: Students open `master.ipynb` for a full index or navigate through a custom-generated course in `generated_course/`.
2.  **Study**: They interact with notebook cells containing text, math, and code.
3.  **Simulate**: For complex protocols (e.g., QKD, Teleportation), students launch the `q-sim` environment to visualize the protocol in action.

#### Instructor Flow
1.  **Author**: Modify or add notebooks in `content/`.
2.  **Build**: Use the `Course Selector` tool to define a syllabus.
3.  **Deploy**: Run the exporter to package the selected modules for students.

## Directory Structure Highlights

```text
/
├── content/               # Raw course notebooks (Units 1-3+)
├── course/
│   └── pyfiles/
│       ├── course_exporter.py    # Logic to stitch notebooks together
│       └── course_selector_ui.py # UI for selecting course modules
├── q-sim/                 # Quantum Network Simulator
│   ├── main.py            # Simulation entry point/example
│   ├── server/            # FastAPI backend
│   └── ui/                # React frontend
└── master.ipynb           # Main index for the static course
```
