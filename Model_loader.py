# Built-in/Generic Imports
from copy import deepcopy
import pickle

# Libs
import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB

# Own modules
from Problem_2.Network_2_generator import generate_data

model = gp.Model("APO_assignment_model")

model.read("Model.lp")

print("optimize")
model.optimize()

