
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
from Problem_2.Network_2_generator import generate_data

__version__ = '1.1.1'

################################################################################################################

# =========================================================== Generate data
hub, hub_ref, max_continuous_operation, average_load_factor, \
aircraft_dict, airports_dict, distances_df, routes_dict, traffic_df, yield_df = generate_data()


# -> Creating model
model = gp.Model("APO_assignment_model_2")

# -> Disabling the gurobi console output, set to 1 to enable
model.Params.OutputFlag = 1

# =========================================================== Prepare network edge dataframe
# -> Create network edge dataframe
edges_df = pd.DataFrame(index=np.arange(len(airports_dict)),
                        columns=np.arange(len(airports_dict)))

edges_df.columns = list(node for node in airports_dict.keys())
edges_df = edges_df.reindex(index=list(node for node in airports_dict.keys()), fill_value=0)

# =========================================================== Setup decision variables
# Routes: binary list, x: integer list, w: integer list
decision_variable_dict = {"aircrafts": {},
                          "routes": {}}

# ----------------> Creating structure
# ... for every aircraft
for aircraft_ref, aircraft in aircraft_dict.items():

    # -> Adding aircraft count decision variable
    decision_variable_dict["aircrafts"][aircraft_ref] = {"z": {},
                                                         "count": model.addVar(vtype=GRB.INTEGER,
                                                                               name="#_" + aircraft_ref)}
    # ... for every route
    for route_ref, route in routes_dict.items():
        decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref] = 0

# ... for every route
for route_ref, route in routes_dict.items():
    decision_variable_dict["routes"][route_ref] = {"x": deepcopy(edges_df),
                                                   "w": {}}
    for route_ref_2, route_2 in routes_dict.items():
        decision_variable_dict["routes"][route_ref]["w"][route_ref_2] = deepcopy(edges_df)

# ----------------> Filling x/w/z decision variables
# ... for every route
for route_ref, route in routes_dict.items():

    # ... for every aircraft
    for aircraft_ref, aircraft in aircraft_dict.items():

        # Do not create x decision variables if aircraft is not compatible with route
        if aircraft["routes viability"][route_ref] == 0:
            pass
        else:
            # Make z_r_ij a decision variable
            decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref] = \
                model.addVar(vtype=GRB.INTEGER,
                             name="z-" + aircraft_ref + "-" + route_ref)

    # ... for every leg
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            if airport_i_ref == airport_j_ref:
                pass
            else:
                # If leg is part of route
                if routes_dict[route_ref]["path df"].loc[airport_i_ref, airport_j_ref] == 1:

                    # Make x_ij a decision variable
                    decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref] = \
                        model.addVar(vtype=GRB.INTEGER,
                                     name="x-" + route_ref + "--" + airport_i_ref + "->" + airport_j_ref)

                    # Make w_ij a decision variable
                    for route_ref_2, route_2 in routes_dict.items():
                        if route_ref == route_ref_2:
                            pass
                        else:
                            decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref] = \
                                model.addVar(vtype=GRB.INTEGER,
                                             name="w-" + route_ref + "|" + route_ref_2 + "--" + airport_i_ref + "->" + airport_j_ref)

# ============================================================================= Setting up constraints
# =========================================================== Demand constraint
"""
Demand constraints:

Overall leg demand:
    "Total flow assigned for leg <= demand for leg"

Demand 2:
    "Direct flow assigned <= demand * auxiliary_parameter_route"

Demand 3:
    "Transfer flow assigned <= demand * auxiliary_parameter_route * auxiliary_parameter_route 2"

note: each constraint sums flows across aircraft types per routes, legs are directional

:return:
"""
# ----------- Overall leg demand
# ... for every possible leg (i,j in N)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg
        constraint_l = gp.LinExpr()

        # ... for every route (r in R)
        for route_ref, route in routes_dict.items():

            # ... For every route 2 (n in R)
            leg_w_lst = []
            for route_ref_2, route_2 in routes_dict.items():
                if route_ref_2 == route_ref:
                    pass
                else:
                    leg_w_lst.append(decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref])

            constraint_l += decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref] + sum(leg_w_lst)

        model.addConstr(constraint_l <= traffic_df.loc[airport_i_ref, airport_j_ref],
                        name="Constraint-Total_demand-" + airport_i_ref + "->" + airport_j_ref)

# ----------- Direct leg demand
# ... for every possible leg (i,j in N)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():

        # ... for every route (r in R)
        for route_ref, route in routes_dict.items():
            # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg per route
            constraint_l = gp.LinExpr()

            constraint_l += decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref]

            model.addConstr(constraint_l <= traffic_df.loc[airport_i_ref, airport_j_ref]
                            * routes_dict[route_ref]["path df"].loc[airport_i_ref, airport_j_ref],
                            name="Constraint-Direct_demand-" + route_ref + "--" + airport_i_ref + "->" + airport_j_ref)

# ----------- Indirect leg demand
# ... for every possible leg (i,j in N)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():

        # ... for every route (r in R)
        for route_ref, route in routes_dict.items():

            # ... for every route 2 (n in R)
            for route_ref_2, route_2 in routes_dict.items():
                if route_ref == route_ref_2:
                    pass
                else:
                    # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg per route per route
                    constraint_l = gp.LinExpr()

                    constraint_l += decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref]

                    model.addConstr(constraint_l <= traffic_df.loc[airport_i_ref, airport_j_ref]
                                    * routes_dict[route_ref]["path df"].loc[airport_i_ref, hub_ref]
                                    * routes_dict[route_ref_2]["path df"].loc[hub_ref, airport_j_ref],
                                    name="Constraint-Indirect_demand-" + route_ref + "|" + route_ref_2 + "--" + airport_i_ref + "->" + airport_j_ref)

# =========================================================== Flow constraint
"""
Used to generate the flow constraints (1 for from hub to node, 1 for from node to node, 1 for from node to hub)

Flow constraint: Flow assigned matches corresponding capacity

from the hub node:
    "sum of flow from hub + sum of flow through hub <= # flights * # seats per aircraft * avg. load factor"

between spokes:
    "sum of flow from origin to destination + sum of flow through origin"

to the hub node:
    "sum of flow to hub + sum of flow through hub <= # flights * # seats per aircraft * avg. load factor"


note: each constraint sums flows across aircraft types

:return: None
"""

# ----------- From hub constraint
# ... for every route (r in R)
for route_ref, route in routes_dict.items():
    # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per route
    constraint_l = gp.LinExpr()
    constraint_r = gp.LinExpr()

    # ------ Left hand of constraint
    # ... for every subsequent node from hub (m in srh)
    for subsequent_ref in routes_dict[route_ref]["subsequent nodes"][hub_ref]:
        # x_r_Hm
        constraint_l += decision_variable_dict["routes"][route_ref]["x"].loc[hub_ref, subsequent_ref]

        # ... for every route 2 (n in R)
        for route_ref_2, route_2 in routes_dict.items():

            # ... for every destination from hub 2 (p in N)
            for airport_p_ref, airport_p in airports_dict.items():
                # w_nr_pm
                constraint_l += decision_variable_dict["routes"][route_ref_2]["w"][route_ref].loc[airport_p_ref, subsequent_ref]

    # ------ Right hand of constraint
    # ... for every aircraft (k in K)
    for aircraft_ref, aircraft in aircraft_dict.items():
        constraint_r += decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref] \
                        * aircraft_dict[aircraft_ref]["seats"] \
                        * average_load_factor

    model.addConstr(constraint_l <= constraint_r, "Constraint-Flow(from_hub)-" + route_ref)


# ----------- Between spokes constraint
# ... for every route greater than 2 nodes (r in R)
for route_ref, route in routes_dict.items():
    if len(route["path"]) < 2:
        # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per route with more than 2 nodes
        constraint_l = gp.LinExpr()
        constraint_r = gp.LinExpr()

        airport_i_ref = route["path"][1]
        airport_j_ref = route["path"][2]

        # ... for every subsequent node from hub (m in srj)
        for subsequent_ref in airports_dict[routes_dict[route_ref]["subsequent nodes"][airport_j_ref]]:
            # x_r_im
            constraint_l += decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, subsequent_ref]

        # ... for every precedent_ref node from hub (m in Pri)
        for precedent_ref in routes_dict[route_ref]["precedent nodes"][airport_i_ref]:
            # x_r_mj
            constraint_l += decision_variable_dict["routes"][route_ref]["x"].loc[precedent_ref, airport_j_ref]

        # ... for every route (n in R)
        for route_ref_2, route_2 in routes_dict.items():
            # ... for every node (p in N)
            for airport_p_ref, airport_p in airports_dict.items():
                constraint_l += decision_variable_dict["routes"][route_ref_2]["w"][route_ref].loc[airport_p_ref, airport_j_ref]
                constraint_l += decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_p_ref]

        # ------ Right hand of constraint
        # ... for every aircraft (k in K)
        for aircraft_ref, aircraft in aircraft_dict.items():
            constraint_r += decision_variable_dict["aircraft"][aircraft_ref]["z"][route_ref] \
                            * aircraft_dict[aircraft_ref]["seats"] \
                            * average_load_factor

        model.addConstr(constraint_l <= constraint_r, "Constraint-Flow(between_spokes)-" + route_ref)

# ----------- To hub constraint
# ... for every route (r)
for route_ref, route in routes_dict.items():
    # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per route
    constraint_l = gp.LinExpr()
    constraint_r = gp.LinExpr()

    airport_i_ref = route["path"][2]
    # ------ Left hand of constraint
    # ... for every precedent_ref node from hub (m in Pri)
    for precedent_ref in routes_dict[route_ref]["precedent nodes"][airport_i_ref]:
        # x_r_mH
        constraint_l += decision_variable_dict["routes"][route_ref]["x"].loc[precedent_ref, hub_ref]

        # ... for every route 2 (n in R)
        for route_ref_2, route_2 in routes_dict.items():

            # ... for every destination from hub 2 (p in N)
            for airport_p_ref, airport_p in airports_dict.items():
                # w_nr_pm
                constraint_l += decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[precedent_ref, airport_p_ref]

    # ------ Right hand of constraint
    # ... for every aircraft
    for aircraft_ref, aircraft in aircraft_dict.items():
        constraint_r += decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref] \
                        * aircraft_dict[aircraft_ref]["seats"] \
                        * average_load_factor

    model.addConstr(constraint_l <= constraint_r, "Constraint-Flow(to_hub)-" + route_ref)


# =========================================================== Aircraft utilisation constraint
# ... for every aircraft (k in K)
for aircraft_ref, aircraft in aircraft_dict.items():
    # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per aircraft type
    constraint_l = gp.LinExpr()
    constraint_r = gp.LinExpr()

    # ... for every route (r in R)
    for route_ref, route in routes_dict.items():
        constraint_l += (route["length"]/aircraft["speed"]
                         + aircraft["avg TAT"] * (len(route["path"])-1 + 1.5) # one of the airports (hub) has a TAT of +50%
                         + aircraft["extra charging time"]) \
                         * decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref]

    constraint_r += max_continuous_operation * decision_variable_dict["aircrafts"][aircraft_ref]["count"]

    model.addConstr(constraint_l <= constraint_r, "Constraint-Utilisation-" + aircraft_ref)

# =========================================================== Aircraft allocation constraints
'''
Already accounted for in the generation of decision variables (viability of routes per aircraft type is solved for
during data preprocessing in route generation). If a route is not viable, corresponding x/y/z
'''

# =========================================================== Fleet budget constraint

# =========================================================== Building objective function
# --> Initiating objective function linear expression
objective_function = gp.LinExpr()

# --> Adding decision variables
# ... for every route
for route_ref, route in routes_dict.items():
    # ... for every leg making up the route
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            if airport_i_ref == airport_j_ref:
                continue
            else:
                # > For every other route served by AC type
                leg_w_lst = []
                for route_ref_2, route_2 in routes_dict.items():
                    leg_w_lst.append(decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref])

                # -> Adding total yield per leg
                objective_function += yield_df.loc[airport_i_ref, airport_j_ref] \
                                      * distances_df.loc[airport_i_ref, airport_j_ref] \
                                      * (decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref]
                                         + sum(leg_w_lst) * 0.9) # 10% discount for costumers connecting at the hub

    # ... for every aircraft
    for aircraft_ref, aircraft in aircraft_dict.items():
        total_route_cost = 0
        for i in range(len(route["path"])-1):
            airport_i_ref = route["path"][i]
            airport_j_ref = route["path"][i+1]

            total_route_cost += aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref]

        # -> Adding total cost per leg
        objective_function -= total_route_cost \
                              * aircraft["seats"] \
                              * decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref]

# ... for every aircraft
for aircraft_ref, aircraft in aircraft_dict.items():
    # -> Adding leasing cost per week for ac type
    objective_function -= decision_variable_dict["aircrafts"][aircraft_ref]["count"] \
                          * aircraft["weekly lease cost"]

# --> Setting objective
model.setObjective(objective_function, GRB.MAXIMIZE)

# ============================================================================= Optimise model
model.write("Model_2.lp")
print("Model compiled!!!")
# model.optimize()