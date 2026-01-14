from tkinter import *
from global_variables import *
from QuantumNetwork import Quantum_Network as QNetwork

class Home():
    def __init__(self):
        self.HomeWindow = Tk()
        self.HomeWindow.title('Quantum Key Distribution Network') 
        self.page = 1

        l = Label(self.HomeWindow, text = "Welcome !!!")
        l.config(font =("Courier", 16))

        self.ksu_id_var=StringVar()
        self.name_var=IntVar()
        self.name_var.set(5)

        ksu_id_label = Label(self.HomeWindow, text = 'Enter your Student ID:')
        ksu_id_entry = Entry(self.HomeWindow,textvariable = self.ksu_id_var)

        mode_label = Label(self.HomeWindow, text = 'Select the mode')
        self.selectedMode = StringVar()
        self.selectedMode.set(transmission)
        r1 = Radiobutton(self.HomeWindow, text='Transmission Mode', value=transmission, variable=self.selectedMode)
        r2 = Radiobutton(self.HomeWindow, text='Arrangement Mode', value=rearrange, variable=self.selectedMode)

        protocol_label = Label(self.HomeWindow, text = 'Select the Quantum Network Protocol')
        self.selectedProtocol = StringVar()
        self.selectedProtocol.set(E91)
        r3 = Radiobutton(self.HomeWindow, text='E91 Protocol', value=E91, variable=self.selectedProtocol)
        r4 = Radiobutton(self.HomeWindow, text='3-Stage Protocol', value=ThreeStage, variable=self.selectedProtocol)

        self.selectedtask = StringVar()
        self.selectedtask.set(generate_key)
        task_label = Label(self.HomeWindow, text = 'Select a task')
        r5 = Radiobutton(self.HomeWindow, text='Generate a secure key', value=generate_key, variable=self.selectedtask)
        r6 = Radiobutton(self.HomeWindow, text='Send a Message (only for 3-stage)', value= send_message, variable=self.selectedtask)
        self.message_var=StringVar()
        message_label = Label(self.HomeWindow, text = 'Enter a message to communicate:')
        message_entry = Entry(self.HomeWindow,textvariable = self.message_var)

        name_label = Label(self.HomeWindow, text = 'Enter the grid size:')
        name_entry = Entry(self.HomeWindow,textvariable = self.name_var)
        
        l.grid(row=0, column=0, padx=20, pady=20, sticky='E')
        ksu_id_label.grid(row=1, column=0, padx=20, pady=20, sticky='W')
        ksu_id_entry.grid(row=1, column=1, padx=20, pady=20, sticky='W')
        mode_label.grid(row=2, column=0, padx=20, sticky='W')
        r1.grid(row=3, column=0, padx=35, sticky='W')
        r2.grid(row=4, column=0,padx=35, sticky='W')
        protocol_label.grid(row=5, column=0, padx=20, sticky='W')
        r3.grid(row=6, column=0, padx=35, sticky='W')
        r4.grid(row=7, column=0,padx=35,sticky='W')

        task_label.grid(row=8, column=0, padx=20, sticky='W')
        r5.grid(row=9, column=0, padx=35, sticky='W')
        r6.grid(row=10, column=0,padx=35,sticky='W')
        message_label.grid(row=11,column=0, padx=35, sticky='W')
        message_entry.grid(row=11,column=1, padx=20, sticky='W')

        name_label.grid(row=12,column=0, padx=20, pady=20, sticky='W')
        name_entry.grid(row=12,column=1, padx=20, pady=20, sticky='W')

        sub_btn=Button(self.HomeWindow,text = 'Submit', command= self.onSubmit)
        sub_btn.grid(row=13, padx=20, pady=20,  sticky='E')
        self.HomeWindow.mainloop()
    
    # def mainloop(self):
    #     self.HomeWindow.mainloop()
    
    def onSubmit(self):
        self.HomeWindow.destroy()
        instance = QNetwork(self)
        #instance.mainloop()

game_instance = Home()
