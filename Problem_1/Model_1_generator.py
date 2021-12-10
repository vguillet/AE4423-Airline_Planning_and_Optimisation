
################################################################################################################
"""

"""

# Built-in/Generic Imports
import random
from copy import deepcopy
import sys

# Libs
import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB

# Own modules
from Problem_1.Network_1_generator import generate_data

__version__ = '1.1.1'

################################################################################################################


# =========================================================== Generate data
hub, hub_ref, max_continuous_operation, average_load_factor, \
aircraft_dict, airports_dict, distances_df, traffic_df, yield_df = generate_data()

# -> Creating model
model = gp.Model("APO_assignment_model_1B")

# -> Disabling the gurobi console output, set to 1 to enable
model.Params.OutputFlag = 1

# =========================================================== Prepare network edge dataframe
# -> Create network edge dataframe
edges_df = pd.DataFrame(index=np.arange(len(airports_dict)),
                        columns=np.arange(len(airports_dict)))

edges_df.columns = list(node for node in airports_dict.keys())
edges_df = edges_df.reindex(index=list(node for node in airports_dict.keys()), fill_value=0)

# =========================================================== Setup decision variables
decision_variable_dict = {"aircrafts": {},
                          "legs": {}}

# ... for every aircraft
for aircraft_ref, aircraft in aircraft_dict.items():

    # -> Adding aircraft count decision variable
    decision_variable_dict["aircrafts"][aircraft_ref] = {"z": deepcopy(edges_df),
                                                         "count": model.addVar(vtype=GRB.INTEGER,
                                                                               name="#_" + aircraft_ref)}

decision_variable_dict["legs"] = {"x": deepcopy(edges_df),
                                  "w": deepcopy(edges_df)}

# ----------------> Filling x/w/z decision variables
# ... for every node-node (leg)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        if airport_i_ref == airport_j_ref:
            pass
        else:
            decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref] = \
                model.addVar(vtype=GRB.INTEGER,
                             name="x-" + airport_i_ref + "->" + airport_j_ref)

            decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref] = \
                model.addVar(vtype=GRB.INTEGER,
                             name="w-" + airport_i_ref + "->" + airport_j_ref)

            # ... for every aircraft
            for aircraft_ref, aircraft in aircraft_dict.items():
                if aircraft["legs"]["viability"].loc[airport_i_ref, airport_j_ref] == 1:
                    decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref] = \
                        model.addVar(vtype=GRB.INTEGER,
                                     name="z-" + aircraft_ref + "--" + airport_i_ref + "->" + airport_j_ref)

# ============================================================================= Setting up constraints
# =========================================================== Demand constraint
# ----------- Demand Verification: # PAX <= demand C1
# ... for every node-node (leg)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        constraint_l = gp.LinExpr()

        constraint_l += decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref] \
                        + decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref]

        model.addConstr(constraint_l <= traffic_df.loc[airport_i_ref, airport_j_ref],
                        name="Constraint-C1-" + airport_i_ref + "->" + airport_j_ref)

# ----------- Demand Verification: # PAX <= demand C1*
# ... for every node-node (leg)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        constraint_l = gp.LinExpr()

        constraint_l += decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref]

        if hub_ref in [airport_i_ref,airport_j_ref]:
            constraint_r = 0
        else:
            constraint_r = traffic_df.loc[airport_i_ref, airport_j_ref]

        model.addConstr(constraint_l <= constraint_r,
                        name="Constraint-C1*-" + airport_i_ref + "->" + airport_j_ref)

# ----------- Capacity: # PAX in each leg <= seat available per leg C2
# ... for every node-node (leg)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        constraint_l = gp.LinExpr()
        constraint_r = gp.LinExpr()

        constraint_l += decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref]

        # for m in N
        for airport_m_ref, airport_m in airports_dict.items():
            if hub_ref == airport_j_ref:
                constraint_l += decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_m_ref]

            if hub_ref == airport_i_ref:
                constraint_l += decision_variable_dict["legs"]["w"].loc[airport_m_ref, airport_j_ref]

        # ... for every aircraft
        for aircraft_ref, aircraft in aircraft_dict.items():
            constraint_r += decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref] \
                            * aircraft_dict[aircraft_ref]["seats"] \
                            * average_load_factor

        model.addConstr(constraint_l <= constraint_r,
                        name="Constraint-C2-" + airport_i_ref + "->" + airport_j_ref)

# -----------  Continuity constraint: #AC inbound = #AC outbound C3
# ... for every i (leg)
for airport_i_ref, airport_i in airports_dict.items():
    # ... for every aircraft k in K
    for aircraft_ref, aircraft in aircraft_dict.items():
        constraint_l = gp.LinExpr()
        constraint_r = gp.LinExpr()

        # for j in N
        for airport_j_ref, airport_j in airports_dict.items():
            constraint_l += decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]
            constraint_r += decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_j_ref, airport_i_ref]

        model.addConstr(constraint_l == constraint_r,
                        name="Constraint-C3-" + airport_i_ref + "-" + aircraft_ref)


# ----------- AC Productivity: hours of operation <= BT * #AC C4
# ... for every aircraft
for aircraft_ref, aircraft in aircraft_dict.items():
    constraint_l = gp.LinExpr()
    constraint_r = gp.LinExpr()

    # ... for every node-node (leg)
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            constraint_l += (distances_df.loc[airport_i_ref, airport_j_ref] / aircraft["speed"]
                             + aircraft["avg TAT"] + aircraft["avg TAT"] * ((airport_j_ref == hub_ref) * 0.5)) \
                             * decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]
    # TODO: dubble check LTO = TAT?


    constraint_r += max_continuous_operation * decision_variable_dict["aircrafts"][aircraft_ref]["count"]

    model.addConstr(constraint_l <= constraint_r,
                    name="Constraint-C4-" + aircraft_ref)

### C5 is taken care of in the variable generation
### C6 is not relevant since we have no budget


# --> Initiating objective function linear expression
objective_function = gp.LinExpr()

# ... for every node-node (leg)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        objective_function += yield_df.loc[airport_i_ref, airport_j_ref] \
                              * distances_df.loc[airport_i_ref, airport_j_ref] * \
                              (decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref]
                               + decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref])

        # ... for every aircraft
        for aircraft_ref, aircraft in aircraft_dict.items():
            objective_function -= aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref]\
                                  * aircraft["seats"] \
                                  * decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]

            # Lease costs
            objective_function -= decision_variable_dict["aircrafts"][aircraft_ref]["count"] \
                                  * aircraft["weekly lease cost"]

# --> Setting objective
model.setObjective(objective_function, GRB.MAXIMIZE)

# ============================================================================= Optimise model
model.write("Model_1B.lp")
print("Model 1 compiled!!!")
model.optimize()

model.printStats()
results = model.getVars()
for r in results:
    if r.X != 0:
        print(r)
