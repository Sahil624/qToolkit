from global_variables import *

class Node():
    def __init__(self, id, oval_id, position, status, number_of_edges, connections):
        self._node_id = id
        self._oval_id = oval_id
        self._color = dot_color
        self._position = position
        self._status = status
        self._prev_selection_status = False
        self._number_of_edges = number_of_edges
        self._type = node
        self._connections = connections

    @property
    def oval_id(self):
         return self._oval_id
    
    @property
    def id(self):
         return self._node_id
    
    @property
    def color(self):
         return self._color
       
    @color.setter
    def color(self, color):
         self._color = color
    
    @property
    def status(self):
         return self._status
       
    @status.setter
    def status(self, status):
         self._status = status
     
    @property
    def prev_selection_status(self):
         return self._prev_selection_status
       
    @prev_selection_status.setter
    def prev_selection_status(self, status):
         self._prev_selection_status = status

    @property
    def position(self):
         return self._position
    
    '''@position.setter
    def set_position(self, position, index):
         self._position[index] = position
         #self.myList = self.myList + [val]
         return self._position'''
    
    '''def myList(self, val):
        self._position = val'''

    def position_update(self, val, index):
        self._position[index] = val
        return self._position
     
    @property
    def edges(self):
         return self._number_of_edges
       
    @edges.setter
    def edges(self, edges):
         self._number_of_edges = edges

    @property
    def connections(self):
         return self._connections
    
    def connections_update(self, connections):
        self._connections.append(connections)
        return self._connections

    def show_all(self):
        return str(self._node_id) + ' '+ str(self._oval_id) + ' '+str(self._color)+ ' '+str(self._position)