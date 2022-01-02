# Built-in/Generic Imports

# Libs
import gurobipy as gp

# Own modules

# model = gp.Model("APO_assignment_model")

model = gp.read("Model_3.lp")

print("optimize")
model.optimize()

model.printStats()

print("\n\n=================================================================================================================")

# =========================================================== Generate data
# -> Number of arc used
total_arc_used = 0
results = model.getVars()

for decision_variable in results:
    print(decision_variable.varName, decision_variable.X)
    if decision_variable.varName[0] in ["x", "y"] and int(decision_variable.x) == 1:
        total_arc_used += 1

print(f"- Nb. arcs used: {total_arc_used}")

# -> Number of NS arcs used
NS_arc_used = 0

# -> Number of packages handled
total_packages_handled = 0
