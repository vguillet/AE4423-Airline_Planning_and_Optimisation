
################################################################################################################
"""

"""

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
from Progress_bar import Progress_bar
# from Progress_bar_tool import Progress_bar_1

__version__ = '1.1.1'

################################################################################################################

demand_constraints = 1
flow_constraints_1 = 1
flow_constraints_2 = 1
flow_constraints_3 = 1
utilisation_constraint = 1

# =========================================================== Generate data
display_progress_bars = True
airports_included = 8
hub, hub_ref, max_continuous_operation, average_load_factor, \
aircraft_dict, airports_dict, distances_df, routes_dict, traffic_df, yield_df = generate_data(question=2,airports_included=airports_included)

# -> Creating model
model = gp.Model("APO_assignment_model")

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

print("----------------> Creating structure")
# pb = Progress_bar_1(len(routes_dict.keys())+len(aircraft_dict.keys()))
pb = Progress_bar(len(routes_dict.keys())+len(aircraft_dict.keys()))
# ----------------> Creating structure
# ... for every aircraft
for aircraft_ref, aircraft in aircraft_dict.items():
    if display_progress_bars:
        pb.update()
    # -> Adding aircraft count decision variable
    decision_variable_dict["aircrafts"][aircraft_ref] = {"z": {},
                                                         "count": model.addVar(vtype=GRB.INTEGER,
                                                                               name="#_" + aircraft_ref)}
    # ... for every route
    for route_ref, route in routes_dict.items():
        decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref] = 0

# ... for every route
for route_ref, route in routes_dict.items():
    if display_progress_bars:
        pb.update()
    decision_variable_dict["routes"][route_ref] = {"x": deepcopy(edges_df),
                                                   "w": {}}
    for route_ref_2, route_2 in routes_dict.items():
        decision_variable_dict["routes"][route_ref]["w"][route_ref_2] = deepcopy(edges_df)

print("----------------> Filling x/w/z decision variables")
pb = Progress_bar(len(routes_dict.keys()))
# ----------------> Filling x/w/z decision variables
# ... for every route
for route_ref, route in routes_dict.items():
    if display_progress_bars:
        pb.update()
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
                        if airport_i_ref == hub_ref or airport_j_ref == hub_ref:
                            pass # no transfer if you start or end at the hub
                        elif route_ref == route_ref_2:
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
if demand_constraints:
    print("----------------> Overall leg demand")
    pb = Progress_bar(len(airports_dict.keys())**2)
    # ----------- Overall leg demand
    # ... for every possible leg (i,j in N)
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            if display_progress_bars:
                pb.update()
            # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg
            constraint_l = gp.LinExpr()

            # ... for every route (r in R)
            for route_ref, route in routes_dict.items():

                # ... For every route 2 (n in R)
                for route_ref_2, route_2 in routes_dict.items():
                    constraint_l += decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref]

                constraint_l += decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref]

            model.addConstr(constraint_l <= traffic_df.loc[airport_i_ref, airport_j_ref],
                            name="Constraint-Total_demand-" + airport_i_ref + "->" + airport_j_ref)

    print("----------------> Direct leg demand")
    pb = Progress_bar(len(airports_dict.keys())**2)
    # ----------- Direct leg demand
    # ... for every possible leg (i,j in N)
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            if display_progress_bars:
                pb.update()
            # ... for every route (r in R)
            for route_ref, route in routes_dict.items():
                # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg per route
                constraint_l = gp.LinExpr()

                constraint_l += decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref]

                model.addConstr(constraint_l <= traffic_df.loc[airport_i_ref, airport_j_ref]
                                * routes_dict[route_ref]["path df"].loc[airport_i_ref, airport_j_ref],
                                name="Constraint-Direct_demand-" + route_ref + "--" + airport_i_ref + "->" + airport_j_ref)

    print("----------------> Indirect leg demand")
    pb = Progress_bar(len(airports_dict.keys())**2)
    # ----------- Indirect leg demand
    # ... for every possible leg (i,j in N)
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            if display_progress_bars:
                pb.update()
            # ... for every route (r in R)
            for route_ref, route in routes_dict.items():

                # ... for every route 2 (n in R)
                for route_ref_2, route_2 in routes_dict.items():
                    if route_ref == route_ref_2:
                        pass
                    else:
                        # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg per route per route
                        constraint_l = gp.LinExpr()
                        constraint_r = traffic_df.loc[airport_i_ref, airport_j_ref]

                        constraint_l += decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref]

                        constraint_r *= routes_dict[route_ref]["path df"].loc[airport_i_ref, hub_ref]
                        constraint_r *= routes_dict[route_ref_2]["path df"].loc[hub_ref, airport_j_ref]

                        model.addConstr(constraint_l <= constraint_r,
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

if flow_constraints_1:
    print("----------------> From hub constraint")
    pb = Progress_bar(len(routes_dict.keys()))
    # ----------- From hub constraint
    # ... for every route (r in R)
    for route_ref, route in routes_dict.items():
        if display_progress_bars:
            pb.update()
        # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per route
        constraint_l = gp.LinExpr()
        constraint_r = gp.LinExpr()

        # airport_j_ref = route["path"][1]

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
                    # TODO: Double check nr/rn order
                    constraint_l += decision_variable_dict["routes"][route_ref_2]["w"][route_ref].loc[airport_p_ref, subsequent_ref]

        # ------ Right hand of constraint
        # ... for every aircraft (k in K)
        for aircraft_ref, aircraft in aircraft_dict.items():
            constraint_r += decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref] \
                            * aircraft_dict[aircraft_ref]["seats"] \
                            * average_load_factor

        model.addConstr(constraint_l <= constraint_r, "Constraint-Flow(from_hub)-" + route_ref)

if flow_constraints_2:
    print("----------------> Between spokes constraint")
    pb = Progress_bar(len(routes_dict.keys()))
    # ----------- Between spokes constraint
    # ... for every route greater than 2 nodes (r in R)
    for route_ref, route in routes_dict.items():
        if display_progress_bars:
            pb.update()
        if len(route["path"]) > 3:
            # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per route with more than 2 nodes
            constraint_l = gp.LinExpr()
            constraint_r = gp.LinExpr()

            airport_i_ref = route["path"][1]
            airport_j_ref = route["path"][2]

            # ... for every subsequent node from hub (m in srj)
            for subsequent_ref in routes_dict[route_ref]["subsequent nodes"][airport_j_ref]:
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
                constraint_r += decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref] \
                                * aircraft_dict[aircraft_ref]["seats"] \
                                * average_load_factor

            model.addConstr(constraint_l <= constraint_r, "Constraint-Flow(between_spokes)-" + route_ref)

if flow_constraints_3:
    print("----------------> To hub constraint")
    pb = Progress_bar(len(routes_dict.keys()))
    # ----------- To hub constraint
    # ... for every route (r)
    for route_ref, route in routes_dict.items():
        if display_progress_bars:
            pb.update()
        # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per route
        constraint_l = gp.LinExpr()
        constraint_r = gp.LinExpr()

        airport_i_ref = route["path"][-2]
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
                    # TODO: Double check nr/rn order
                    constraint_l += decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[precedent_ref, airport_p_ref]

        # ------ Right hand of constraint
        # ... for every aircraft
        for aircraft_ref, aircraft in aircraft_dict.items():
            constraint_r += decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref] \
                            * aircraft_dict[aircraft_ref]["seats"] \
                            * average_load_factor

        model.addConstr(constraint_l <= constraint_r, "Constraint-Flow(to_hub)-" + route_ref)


# =========================================================== Aircraft utilisation constraint
if utilisation_constraint:
    print("----------------> Aircraft utilisation constraint")
    pb = Progress_bar(len(aircraft_dict.keys()))
    # ... for every aircraft (k in K)
    for aircraft_ref, aircraft in aircraft_dict.items():
        if display_progress_bars:
            pb.update()
        # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per aircraft type
        constraint_l = gp.LinExpr()
        constraint_r = gp.LinExpr()

        # ... for every route (r in R)
        for route_ref, route in routes_dict.items():
            constraint_l += (route["length"]/aircraft["speed"]
                             + aircraft["avg TAT"]/60 * (len(route["path"])-1 + 0.5) # one of the airports (hub) has a TAT of +50%
                             + aircraft["extra charging time"]/60) \
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
print("----------------> Building objective function...")
pb = Progress_bar(len(routes_dict.keys()))


# --> Initiating objective function linear expression
objective_function = gp.LinExpr()

# --> Adding decision variables
# ... for every route
for route_ref, route in routes_dict.items():
    if display_progress_bars:
        pb.update()
    # ... for every leg making up the route
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            if airport_i_ref == airport_j_ref:
                pass
            else:
                # > For every other route served by AC type
                leg_w_lst = []
                for route_ref_2, route_2 in routes_dict.items():
                    leg_w_lst.append(decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref])

                # -> Adding total yield per leg
                objective_function += yield_df.loc[airport_i_ref, airport_j_ref] \
                                      * distances_df.loc[airport_i_ref, airport_j_ref] \
                                      * (decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref]
                                         + sum(leg_w_lst) * 0.9) # 10% discount for customers connecting at the hub

    # ... for every aircraft
    for aircraft_ref, aircraft in aircraft_dict.items():
        total_route_cost = 0
        for i in range(len(route["path"])-1):
            airport_i_ref = route["path"][i]
            airport_j_ref = route["path"][i+1]

            total_route_cost += aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref]

        # -> Adding total cost per leg
        objective_function -= total_route_cost \
                              * decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref]

# ... for every aircraft
# for aircraft_ref, aircraft in aircraft_dict.items():
#     # Lease costs
#     objective_function -= decision_variable_dict["aircrafts"][aircraft_ref]["count"] \
#                           * aircraft["weekly lease cost"]

# --> Setting objective
print("--> Setting objective")
model.setObjective(objective_function, GRB.MAXIMIZE)

# ============================================================================= Optimise model
print("write_mode....")
model.write("Model.lp")
print("\nModel compiled!!!")

print("optimize")
model.optimize()

for aircraft_ref, aircraft in aircraft_dict.items():
    print(decision_variable_dict["aircrafts"][aircraft_ref]["count"])

flow_x = deepcopy(edges_df)
flow_w = deepcopy(edges_df)
total_capacity = deepcopy(edges_df)

for route_ref, route in routes_dict.items():
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():

            if type(decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref]) != int:
                flow_x.loc[airport_i_ref, airport_j_ref] += decision_variable_dict["routes"][route_ref]["x"].loc[airport_i_ref, airport_j_ref].X

            for route_ref_2, route_2 in routes_dict.items():
                if type(decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref]) != int:
                    flow_w.loc[airport_i_ref, airport_j_ref] += decision_variable_dict["routes"][route_ref]["w"][route_ref_2].loc[airport_i_ref, airport_j_ref].X

    for aircraft_ref, aircraft in aircraft_dict.items():
        for i in range(len(route["path"])-1):
            airport_i_ref = route["path"][i]
            airport_j_ref = route["path"][i+1]

            if type(decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref]) != int:
                total_capacity.loc[airport_i_ref, airport_j_ref] += decision_variable_dict["aircrafts"][aircraft_ref]["z"][route_ref].X \
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
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
           sum_traf += traffic_df.loc[airport_i_ref, j]

sum_flow = 0
for i in flow_x.columns:
    for j in flow_x.index:
        sum_flow += flow_x.loc[i, j] + flow_w.loc[i, j]

print("\n", sum_flow, '<', sum_cap, '<', sum_traf)
