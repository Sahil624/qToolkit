from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.visualization import plot_bloch_multivector
from gates.Gate import *

window_local = None
canvas_widget = None
qc = None
counter = None
channel_order = None

def printCircuit():
    state = Statevector(qc)
    return plot_bloch_multivector(state)

# Function to create a Matplotlib figure
def initialize_circuit():
    global qc
    qc = QuantumCircuit(1)
    return printCircuit()

def start(window):
    global window_local
    window_local = window
    initial_circuit = initialize_circuit()
    create_or_reload_canvas(initial_circuit)

# Function to create or reload the canvas with a given figure
def create_or_reload_canvas(new_fig):
    global canvas_widget
    # Clear the existing canvas
    if canvas_widget:
        canvas_widget.get_tk_widget().destroy()

    # Create a new FigureCanvasTkAgg widget with the new figure
    window_local = FigureCanvasTkAgg(new_fig)
    window_local.get_tk_widget().grid(row=0, column=4, sticky="nsew")  # Use grid for placement


# Function to periodically update the canvas
def periodic_update():
    global window_local, counter, canvas_widgets, channel_order
    print("in periodic update", channel_order)
    if (counter < len(channel_order)):
        print(counter)
        circuit_transition(channel_order[counter])
        window_local.after(500, periodic_update)  # Update every 500 milliseconds (0.5 second)
    return counter 

def circuit_transition(gate):
    global counter
    print("transmitting "+ gate)
    counter += 1
    circuit = draw_circuit(gate)
    create_or_reload_canvas(new_fig=circuit)

def draw_circuit(gate):
    if(gate.__eq__("xgate")):
        xgate(qc=qc)

    elif (gate.__eq__("ugate")):
        ugate(qc=qc)

    elif (gate.__eq__("igate")):
        igate(qc=qc)

    elif (gate.__eq__("hgate")):
        hgate(qc=qc)

    return printCircuit()

def setGlobalValues(gate_order, gate_count, window):
    global window_local, counter, channel_order
    window_local = window
    counter = gate_count
    channel_order = gate_order
    print(channel_order)