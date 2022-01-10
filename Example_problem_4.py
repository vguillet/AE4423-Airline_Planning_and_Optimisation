# -- coding: utf-8 --
"""
Created on Thu Jun 24 15:31:04 2021

@author: abombelli
"""

import numpy as np
import os
import pandas as pd
import time
from gurobipy import Model,GRB,LinExpr,Column

paths = [[1,0,0,0,0,0,0],
          [0,1,0,0,0,0,0],
          [0,0,1,0,0,0,0],
          [0,0,0,1,0,0,0],
          [0,0,0,0,1,0,0],
          [0,0,0,0,0,1,0],
          [0,0,0,0,0,0,1]]

B      = 9
length = [2,3,4,5,6,7,8]
demand = [4,2,6,6,2,2,2]

# Setup master
master = Model()

# Define one decision variable per path
x = {}
for i in range(0,len(paths)):
    x[i]=master.addVar(lb=0, ub=30, vtype=GRB.INTEGER,name="x_%s"%(i))
n_paths = len(paths)

# Define constraints
demand_constraints = {}
for i in range(0,len(demand)):
    thisLHS = LinExpr()
    for j in range(0,len(paths)):
        if paths[j][i] >0:
            thisLHS += paths[j][i]*x[j]
    demand_constraints[i] = master.addConstr(lhs=thisLHS, sense=GRB.GREATER_EQUAL, rhs=demand[i],
                            name='demand_length_%i'%(length[i]))

obj = LinExpr()

for i in range(0,len(paths)):
    obj += x[i]

master.setObjective(obj,GRB.MINIMIZE)
master.update()
master.setParam('OutputFlag', 0)
master.write('master_lp_file.lp')

# Solve
master.setParam('MIPGap',0.01)
master.setParam('TimeLimit',6*3600)
master.setParam('MIPFocus',3)
master.setParam('Presolve',1)
master.setParam('Heuristics',0.05)
master.setParam('Cuts',2)
master.setParam('FlowCoverCuts',2)

exit_condition = False
cont           = 0

while exit_condition is False and cont<100:
    linear_relaxation = master.relax()
    linear_relaxation.optimize()
    linear_relaxation.setParam('OutputFlag', 0)

    pi = [c.Pi for c in linear_relaxation.getConstrs()]

    # Solving the knapsack master (pricing problem)
    knapsack = Model("KP")
    y = {}

    # -> Generating constraints
    for i in range(0,len(length)):
        y[i] = knapsack.addVar(ub=demand[i], vtype="I", name="y[%d]"%i)


    thisLHS = LinExpr()
    for i in range(0,len(length)):
        thisLHS += length[i]*y[i]
    knapsack.addConstr(lhs=thisLHS, sense=GRB.LESS_EQUAL, rhs=B,
                                        name='feasible_pattern')

    obj_kp = LinExpr()

    for i in range(0,len(demand)):
        obj_kp -= pi[i]*y[i]
    obj_kp += 1

    knapsack.setObjective(obj_kp,GRB.MINIMIZE)

    knapsack.update()

    startTime = time.time()
    knapsack.optimize()
    knapsack.setParam('OutputFlag', 0)
    endTime   = time.time()

    solution = []

    # Retrieve variable names and values
    for v in knapsack.getVars():
          solution.append([v.varName,v.x])

    #print(solution)

    # Adding new column if reduced cost is smaller than original cost
    if knapsack.ObjVal < 0:
        new_path = [int(y[i].x) for i in y]
        paths.append(new_path)
        col = Column()
        for i in range(0,len(demand)):
            if new_path[i] > 0:
                col.addTerms(new_path[i],demand_constraints[i])
        x[n_paths] = master.addVar(obj=1,lb=0, ub=30, vtype=GRB.CONTINUOUS,name="x_%s"%(n_paths),column=col)
        master.update()
        n_paths += 1
        print('### Iteration %i ###'%(cont+1))
        print('Added path', new_path)
        print('with reduced cost %f'%(knapsack.ObjVal))
        print('')

    else:
        exit_condition = True

    cont += 1



# Setup master
master = Model()

# Define one decision variable per path
x = {}
for i in range(0,len(paths)):
    x[i]=master.addVar(lb=0, ub=30, vtype=GRB.INTEGER,name="x_%s"%(i))
n_paths = len(paths)

# Define constraints
demand_constraints = {}
for i in range(0,len(demand)):
    thisLHS = LinExpr()
    for j in range(0,len(paths)):
        if paths[j][i] >0:
            thisLHS += paths[j][i]*x[j]
    demand_constraints[i] = master.addConstr(lhs=thisLHS, sense=GRB.GREATER_EQUAL, rhs=demand[i],
                            name='demand_length_%i'%(length[i]))

obj = LinExpr()

for i in range(0,len(paths)):
    obj += x[i]

master.setObjective(obj,GRB.MINIMIZE)
master.optimize()

solution = []

# Retrieve variable names and values
for v in master.getVars():
    solution.append([v.varName,v.x])

print(solution)

# Determining solution in terms of rolls. Each roll contains the items that are
# obtained from that roll. E.g., a roll [2,2,5] implies that two items of
# length 2 and one item of length 5 are obtained from it. Remember that the
# summation of the lengths contained in each roll should be <= B (9 in our case)

# First approach using list comprehension (1-liner!)
rolls1 = []
# Cycling over all paths that were generated
for k in x:
    # Checking how many replicas of such path are
    for j in range(int(x[k].X)):
        # Here we are telling Python to do the following:
        # - add element length[i] ---> the length of the i-th piece (ranging from 2 to 8) : length[i] for i in range(len(demand))
        # - only if this element is present in the current path : if paths[k][i]>0
        # - repeat the operation as many times as the number of times this piece appears in this path : for j in range(paths[k][i])

        rolls1.append(sorted([length[i] for i in range(len(demand)) if paths[k][i]>0 for j in range(paths[k][i])]))
rolls1.sort()

# Second approach using for cycles. The two outputs are of course the same (check!)
rolls = []
for k in x:
    # Checking how many replicas of such path are
    for j in range(int(x[k].X)):
        this_roll = []
        for i in range(0,len(paths[k])):
            for ii in range(0,paths[k][i]):
                this_roll.append(length[i])
        rolls.append(sorted(this_roll))
rolls = sorted(rolls)
