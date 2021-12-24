"""
Created on 24 dec. 2021
@author: Group 10
@course: AE4423, Airline planning and optimisation
"""

from data_processor import Data_reader


class Network_generator:
    """    Sets:
    N: set of nodes n (a,t)
    K: set of fleet types k
    R: set of requests k
    A_f: set of flight arcs f
    A_g: set of ground arcs g
    A_s: set of no-service arcs s
    A: union(A_f, A_g, A_s)
    """

    def __init__(self):
        self.D = Data_reader()

    def export_network(self):
        return self.D





if __name__ == '__main__':
    pass
