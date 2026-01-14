from qiskit import QuantumCircuit, QuantumRegister, Aer
#from qiskit_aer.aerprovider import AerSimulator as Aer
from qiskit.quantum_info import Statevector, partial_trace
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from qiskit.visualization import plot_state_qsphere
import numpy as np

quantumcirc= None
window_local = None
canvas_widget = None
save1 = None
save2 = None
save3 = None
counter = 1

def make_entanglement(quantumcirc, a, b):
    quantumcirc.h(a)
    quantumcirc.cx(a, b)

def final_qubit_state(stateVector, matrix):
    """Get the statevector for the first qubit, discarding the rest."""
    # get the full statevector of all qubits
    full_statevector = stateVector

    # get the density matrix for the first qubit by taking the partial trace
    partial_density_matrix = partial_trace(full_statevector, matrix)

    # extract the statevector out of the density matrix
    partial_statevector = np.diagonal(partial_density_matrix)

    return partial_statevector

def create_or_reload_canvas(new_fig, col):
    global canvas_widget
    # Clear the existing canvas
    if canvas_widget:
        canvas_widget.get_tk_widget().destroy()

    # Create a new FigureCanvasTkAgg widget with the new figure
    window_local = FigureCanvasTkAgg(new_fig)
    window_local.get_tk_widget().grid(row=col, column=4) 
    window_local = FigureCanvasTkAgg(new_fig)
    window_local.get_tk_widget().grid(row=col, column=5) 

def intialize_circuit(window):
    global window_local
    window_local = window
    quantumcirc = QuantumCircuit()
    return quantumcirc

def BinaryToDecimal(binary): 
    binary1 = binary 
    decimal, i, n = 0, 0, 0
    while(binary != 0): 
        dec = binary % 10
        decimal = decimal + dec * pow(2, i) 
        binary = binary//10
        i += 1
    return (decimal)    

def BinarytoString(binary):  
    str_data =' '
    binary_data=''.join([str(item) for item in binary])
    print(binary_data)
    str_data =  ''.join(chr(int(binary_data[i:i+8], 2)) for i in range(0, len(binary_data), 8))
    return str_data

def transmit_message(number_of_nodes, message, window):
    print(message)
    message_circuits = []
    sent_message = []
    recieved_message = []
    for message_bit in message:
        quantumcirc = intialize_circuit(window)
        nodes = number_of_nodes*2-2
        qr = QuantumRegister(nodes*2)
        quantumcirc.add_register(qr)
        # for qubit in range(nodes*2):
        #     quantumcirc.initialize(input_state, qubit)

        create_entangled_qubits(quantumcirc, number_of_nodes, message_bit)
        message_circuits.append(quantumcirc)
    
    print(message_circuits[0])
    
    for i,message_circuit in enumerate(message_circuits):
        
        message_circuit.measure_all()
        aer_sim = Aer.get_backend('aer_simulator')

        # Execute the circuit on the simulator
        result = aer_sim.run(message_circuit, shots=1, memory=True).result()
        measured_bit = result.get_memory()[0]
        print(message[i], measured_bit, measured_bit[-1] )
        sent_message.append(int(measured_bit[-1]))
        recieved_message.append(int(measured_bit[0]))
        # sv = Statevector.from_label(f'{message[i]}{message[i]}{message[i]}{message[i]}')
        # print(message[i])
        
        # sv.seed([message[i],message[i],message[i],message[i]])
        # print(sv)
        # sv = sv.evolve(message_circuit)
        # print(sv.draw())
        # print(sv.measure())
        #print(sv.measure_all())
        #print(sv.measure())
    print(BinarytoString(sent_message), BinarytoString(recieved_message))
    return recieved_message


def create_entangled_qubits(quantumcirc, number_of_nodes, message_bit):
    #print('here', index)
    nodes = number_of_nodes*2-2
    for index in range(nodes):
        # if message_bit == '1':
        #      quantumcirc.x(index*2)
        #      quantumcirc.x(index*2+1)
        quantumcirc.h(index*2)
        quantumcirc.cx(index*2, index*2 + 1)
    global save1
    save1 = Statevector(quantumcirc)

    for index in range(nodes):
        if(index>0):
            quantumcirc.barrier(index*2, index*2-1)
            quantumcirc.cx(index*2-1, index*2)
            quantumcirc.h(index*2-1)
            quantumcirc.barrier(index*2, index*2-1)
    global save2
    save2 = Statevector(quantumcirc)
    

    for qubit in range(1,nodes*2-2,2):
            quantumcirc.cz(qubit, 0)
            quantumcirc.cx(qubit+1, nodes*2-1)
    global save3
    save3 = Statevector(quantumcirc)
    #return quantumcirc
    #plot = plot_state_qsphere(save3)
    # plot = plot_state_qsphere(final_qubit_state(save2, [2,3]))
    # create_or_reload_canvas(plot,0)
    # plot = plot_state_qsphere(final_qubit_state(save2, [0,1]))
    # create_or_reload_canvas(plot,1)
    global counter
    if(counter ==1):
        list = []
        if number_of_nodes == 2:
            list = [1,2]
        elif number_of_nodes == 3:
            list = [1,2,3,4,5,6]
        elif number_of_nodes == 4:
            list = [1,2,3,4,5,6,7, 8,9,10]
        elif number_of_nodes == 5:
            list = [1,2,3,4,5,6,7,8,9,10,11,12,13,14]
        plot = plot_state_qsphere(final_qubit_state(save3, list))
        create_or_reload_canvas(plot,0)
        counter +=1
    
