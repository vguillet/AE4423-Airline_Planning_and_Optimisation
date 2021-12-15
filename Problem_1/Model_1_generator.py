
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

demand_constraints = 1
capacity_constraints = 1
continuity_constraint = 1
AC_productivity = 1

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
    # decision_variable_dict["aircrafts"][aircraft_ref] = {"z": deepcopy(edges_df),
    #                                                      "count": 10}

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

            if airport_i_ref == hub_ref or airport_j_ref == hub_ref:
                pass
            else:
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
if demand_constraints:
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
    # for airport_i_ref, airport_i in airports_dict.items():
    #     for airport_j_ref, airport_j in airports_dict.items():
    #         constraint_l = gp.LinExpr()
    #
    #         constraint_l += decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref]
    #
    #         if hub_ref in [airport_i_ref, airport_j_ref]:
    #             constraint_r = 0
    #         else:
    #             constraint_r = traffic_df.loc[airport_i_ref, airport_j_ref]
    #
    #         model.addConstr(constraint_l <= constraint_r,
    #                         name="Constraint-C1*-" + airport_i_ref + "->" + airport_j_ref)

# ----------- Capacity: # PAX in each leg <= seat available per leg C2
if capacity_constraints:
    # ... for every node-node (leg)
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            constraint_l = gp.LinExpr()
            constraint_r = gp.LinExpr()

            constraint_l += decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref]

            # for m in N
            for airport_m_ref, airport_m in airports_dict.items():
                constraint_l += decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_m_ref] * (1 - (hub_ref != airport_j_ref))
                constraint_l += decision_variable_dict["legs"]["w"].loc[airport_m_ref, airport_j_ref] * (1 - (hub_ref != airport_i_ref))

            # ... for every aircraft
            for aircraft_ref, aircraft in aircraft_dict.items():
                constraint_r += decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref] \
                                * aircraft_dict[aircraft_ref]["seats"] \
                                * average_load_factor

            model.addConstr(constraint_l <= constraint_r,
                            name="Constraint-C2-" + airport_i_ref + "->" + airport_j_ref)

# -----------  Continuity constraint: #AC inbound = #AC outbound C3
if continuity_constraint:
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

if AC_productivity:
    # ----------- AC Productivity: hours of operation <= BT * #AC C4
    # ... for every aircraft
    for aircraft_ref, aircraft in aircraft_dict.items():
        constraint_l = gp.LinExpr()
        constraint_r = gp.LinExpr()

        # ... for every node-node (leg)
        for airport_i_ref, airport_i in airports_dict.items():
            for airport_j_ref, airport_j in airports_dict.items():
                constraint_l += (aircraft["legs"]["duration"].loc[airport_i_ref, airport_j_ref] \
                                 + aircraft["avg TAT"]/60 * (1 + (airport_j_ref == hub_ref) * 0.5)) \
                                * decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]

        constraint_r += max_continuous_operation * decision_variable_dict["aircrafts"][aircraft_ref]["count"]

        model.addConstr(constraint_l <= constraint_r,
                        name="Constraint-C4-" + aircraft_ref)

### C5 is taken care of in the variable generation
### C6 is not relevant since we have no budget

# =========================================================== Building objective function
# --> Initiating objective function linear expression
objective_function = gp.LinExpr()

# ... for every node-node (leg)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        objective_function += yield_df.loc[airport_i_ref, airport_j_ref] \
                              * distances_df.loc[airport_i_ref, airport_j_ref] \
                              * (decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref]
                                 + decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref] * 0.9)

        # ... for every aircraft
        for aircraft_ref, aircraft in aircraft_dict.items():
            objective_function -= aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] \
                                  * decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]

# ... for every aircraft
# for aircraft_ref, aircraft in aircraft_dict.items():
#     # Lease costs
#     objective_function -= decision_variable_dict["aircrafts"][aircraft_ref]["count"] \
#                           * aircraft["weekly lease cost"]

# --> Setting objective
model.setObjective(objective_function, GRB.MAXIMIZE)


# '''TEST'''
# test_yield = {}
# test_operation_cost = {}
# test_leas_cost = {}
# for aircraft_ref, aircraft in aircraft_dict.items():
#     test_yield[aircraft_ref] = deepcopy(edges_df)
#     test_operation_cost[aircraft_ref] = deepcopy(edges_df)
#     test_leas_cost[aircraft_ref] = deepcopy(edges_df)
#
# for airport_i_ref, airport_i in airports_dict.items():
#     for airport_j_ref, airport_j in airports_dict.items():
#         # ... for every aircraft
#         for aircraft_ref, aircraft in aircraft_dict.items():
#             test_yield[aircraft_ref].loc[airport_i_ref, airport_j_ref] = yield_df.loc[airport_i_ref, airport_j_ref] \
#                                                                   * distances_df.loc[airport_i_ref, airport_j_ref] * \
#                                                                   (aircraft["seats"]*average_load_factor*50)
#
#             test_operation_cost[aircraft_ref].loc[airport_i_ref, airport_j_ref] = aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref]*50
#                                   # * aircraft["seats"]
#
#             # Lease costs
#             test_leas_cost[aircraft_ref].loc[airport_i_ref, airport_j_ref] = aircraft["weekly lease cost"]

# for aircraft_ref, aircraft in aircraft_dict.items():
#     print('')
#     print(f'----------------{aircraft_ref}:-------------------')
#     print((test_operation_cost[aircraft_ref]+test_leas_cost[aircraft_ref])/test_yield[aircraft_ref])
#     print(f'Yield:')
#     print(test_yield[aircraft_ref])
#     print(f'Operation costs:')
#     print(test_operation_cost[aircraft_ref])
#     print(f'Leas costs:')
#     print(test_leas_cost[aircraft_ref])
#     print(f'duration{aircraft["legs"]["duration"]}')
# '''TEST'''


# ============================================================================= Optimise model
model.write("Model_1B.lp")
print("Model 1 compiled!!!\n")
model.optimize()

model.printStats()

print("\n\n=================================================================================================================")

for aircraft_ref, aircraft in aircraft_dict.items():
    print(decision_variable_dict["aircrafts"][aircraft_ref]["count"])


#     constraint_l = 0
#     constraint_r = 0
#
#     # ... for every node-node (leg)
#     for airport_i_ref, airport_i in airports_dict.items():
#         for airport_j_ref, airport_j in airports_dict.items():
#             # constraint_l += (distances_df.loc[airport_i_ref, airport_j_ref] / aircraft["speed"]
#             #                  + aircraft["avg TAT"]) + aircraft["avg TAT"] * ((airport_j_ref == hub_ref) * 0.5)) \
#             #                  * decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]
#
#             constraint_l += (distances_df.loc[airport_i_ref, airport_j_ref] / aircraft["speed"]
#                              + aircraft["avg TAT"]) \
#                             * (decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref].x if type(decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]) != int else 0)
#             # print(decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref])
#
#     constraint_r += max_continuous_operation * (decision_variable_dict["aircrafts"][aircraft_ref]["count"].x if type(decision_variable_dict["aircrafts"][aircraft_ref]["count"]) != int else 0)

    # print("\n")
    # print(decision_variable_dict["aircrafts"][aircraft_ref]["count"])
    #
    # print(f"constraint_l:{constraint_l}")
    # print(f"constraint_r:{constraint_r}")

# results = model.getVars()


flow_x = deepcopy(edges_df)
flow_w = deepcopy(edges_df)
total_capacity = deepcopy(edges_df)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():

        if type(decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref]) != int:
            flow_x.loc[airport_i_ref, airport_j_ref] = decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref].X

        if type(decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref]) != int:
            flow_w.loc[airport_i_ref, airport_j_ref] = decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref].X

        for aircraft_ref, aircraft in aircraft_dict.items():
            if type(decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]) != int:
                total_capacity.loc[airport_i_ref, airport_j_ref] += decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref].X \
                                                                         * aircraft['seats']*average_load_factor

print("\n flow_x dataframe")
print(flow_x.to_string())

print("\n flow_w dataframe")
print(flow_w.to_string())

print("\n total_capacity dataframe")
print(total_capacity.to_string())

print("\n traffic_df dataframe")
print(traffic_df.to_string())

sum_cap = 0
for i in total_capacity.columns:
    for j in total_capacity.index:
        sum_cap += total_capacity.loc[i, j]

sum_traf = 0
for i in traffic_df.columns:
    for j in traffic_df.index:
        sum_traf += traffic_df.loc[i, j]

sum_flow = 0
for i in flow_x.columns:
    for j in flow_x.index:
        sum_flow += flow_x.loc[i, j] + flow_w.loc[i, j]

print(sum_flow, '<', sum_cap, '<', sum_traf)