from ipywidgets import Layout, Button, Box, widgets, VBox, HBox, interact, Label
import random, cmath
from QuantumNetwork import Quantum_Network as QuNetwork
from tkinter import *
#Layouts
numInputLayout=Layout(  
    width='55px'
)
strInputLayout=Layout(
    width='150px'
)

hidden = Layout(visibility='hidden')
visible = Layout(visibility='visible')
QValid1_1=widgets.Valid(value=False,readout="Incorrect",layout=hidden)
QValid1_2=widgets.Valid(value=False,readout="Incorrect",layout=hidden)

student_id =  widgets.Text(
                placeholder='Enter Student Id',
                disabled=False,
                layout = strInputLayout
            )
mode = widgets.RadioButtons(
                options=['Transmission Mode', 'Arrangement Mode'],
                #value='Transmission Mode',
                description='',
                disabled=False
            )
protocol = widgets.RadioButtons(
                options=['E91 Protocol', '3-Stage Protocol'],
                #value='E91 Protocol',
                description='',
                disabled=False
            )
task = widgets.RadioButtons(
                options=['Generate a secure key', 'Send a Message'],
                #value='Generate a secure key',
                description='',
                disabled=False
            )
message =  widgets.Text(
                placeholder='Enter a message',
                disabled=False,
                layout = strInputLayout
            )

grid_size =  widgets.Text(
                placeholder='Enter grid size',
                disabled=False,
                value="5",
                layout = strInputLayout
            )

Qbtn_1 = widgets.Button(
            description='Submit',
            disabled=False,
            button_style='success',
        )

def on_button_clicked(b):
    state = {
    'ksu_id_var': student_id.value,
    'selectedMode': mode.value, 
    'selectedProtocol':protocol.value,
    'selectedtask': task.value,
    'message_var': message.value,
    #grid_size: grid_size.value,
    }
    print(state)
    instance = QuNetwork(state)
    instance.mainloop()

Qbtn_1.on_click(on_button_clicked)

Get_Options = VBox([
    widgets.HTML(value="<b><font size=\"+2\">Quantum Network Simulator"),
    widgets.HTML(value="<b><font size=\"-1\"<b>Please select the options below.</b>"),
    widgets.HTML(value="<font size=\"+0\"> Enter your Student ID: "),
    HBox([student_id]),
    widgets.HTML(value="<font size=\"+0\"> Select the Mode: "),
    HBox([mode]),
    widgets.HTML(value="<font size=\"+0\"> Select the Quantum Network Protocol: "),
    HBox([protocol]),
    widgets.HTML(value="<font size=\"+0\"> Select a task: "),
    HBox([task]),
    widgets.HTML(value="<font size=\"+0\"> Enter a message to communicate: "),
    HBox([message]),
    widgets.HTML(value="<font size=\"+0\"> Enter the grid size: "),
    HBox([grid_size]),
     VBox([HBox([Qbtn_1])],layout=Layout(align_items='center'))
])
