from gurobipy import Model, GRB, quicksum
from Usefull_functions import *

# Data
Airports = ['A1','A2','A3']
airports = range(len(Airports))
CASK = 0.12
LF = 0.75
s = 120
sp = 870
LTO = 20/60
BT = 10
AC = 2
y = 0.18  # yield
q = [[0, 1000, 200],
          [1000, 0, 300],
          [200, 300, 0]]
distance = [[0, 2236, 3201],
          [2236, 0, 3500],
          [3201, 3500, 0]]

# Start modelling optimization problem
m = Model('practice')
x = {}
z = {}
for i in airports:
    for j in airports:
        x[i,j] = m.addVar(obj = y*distance[i][j],lb=0,
                           vtype=GRB.INTEGER)
        z[i,j] = m.addVar(obj = -CASK*distance[i][j]*s, lb=0,
                           vtype=GRB.INTEGER)

m.update()
m.setObjective(m.getObjective(), GRB.MAXIMIZE)  # The objective is to maximize revenue

for i in airports:
    for j in airports:
        m.addConstr(x[i,j], GRB.LESS_EQUAL, q[i][j]) #C1
        m.addConstr(x[i, j], GRB.LESS_EQUAL, z[i,j]*s*LF) #C2
    m.addConstr(quicksum(z[i,j] for j in airports), GRB.EQUAL, quicksum(z[j, i] for j in airports)) #C3

m.addConstr(quicksum(quicksum((distance[i][j]/sp+LTO)*z[i,j] for i in airports) for j in airports),
            GRB.LESS_EQUAL, BT*AC) #C4


m.update()
# m.write('test.lp')
# Set time constraint for optimization (5minutes)
# m.setParam('TimeLimit', 1 * 60)
# m.setParam('MIPgap', 0.009)
m.optimize()
# m.write("testout.sol")
status = m.status

if status == GRB.Status.UNBOUNDED:
    print('The model cannot be solved because it is unbounded')

elif status == GRB.Status.OPTIMAL or True:
    f_objective = m.objVal
    print('***** RESULTS ******')
    print('\nObjective Function Value: \t %g' % f_objective)

elif status != GRB.Status.INF_OR_UNBD and status != GRB.Status.INFEASIBLE:
    print('Optimization was stopped with status %d' % status)


# Print out Solutions
print()
print(pcol("Frequencies:----------------------------------","r"))
print()
for i in airports:
    for j in airports:
        if z[i,j].X >0:
            print(Airports[i], ' to ', Airports[j], z[i,j].X)
