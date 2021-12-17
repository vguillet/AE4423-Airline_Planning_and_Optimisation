
################################################################################################################
"""

"""

# Built-in/Generic Imports
from copy import deepcopy

# Libs
import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB
import plotly.graph_objects as go

# Own modules
from Network_generator_1B import generate_data

__version__ = '1.1.1'

################################################################################################################

# Boolean used to test various constraints
demand_constraints = True
capacity_constraints = True
continuity_constraint = True
AC_productivity = True

# ======================================================================================================
# ============================================================================= Generate data
# ======================================================================================================

hub, hub_ref, max_continuous_operation, average_load_factor, \
aircraft_dict, airports_dict, distances_df, demand_df, yield_df = generate_data()

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

# ======================================================================================================
# ============================================================================= Setup decision variables
# ======================================================================================================
decision_variable_dict = {"aircrafts": {},
                          "legs": {}}

# ... for every aircraft
for aircraft_ref, aircraft in aircraft_dict.items():
    decision_variable_dict["aircrafts"][aircraft_ref] = {"z": deepcopy(edges_df),
                                                         "count": model.addVar(vtype=GRB.INTEGER,
                                                                               name="#_" + aircraft_ref)}

decision_variable_dict["legs"] = {"x": deepcopy(edges_df),
                                  "w": deepcopy(edges_df)}

# ----------------> Filling x/w/z decision variables
# ... for every node-node (leg)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        if airport_i_ref != airport_j_ref:
            decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref] = \
                model.addVar(vtype=GRB.INTEGER,
                             name="x-" + airport_i_ref + "->" + airport_j_ref)

            # This if statement is effectively the same as constraint C1*
            # except it makes the model more efficient by leaving out some decision variables.
            if airport_i_ref != hub_ref and airport_j_ref != hub_ref:
                decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref] = \
                    model.addVar(vtype=GRB.INTEGER,
                                 name="w-" + airport_i_ref + "->" + airport_j_ref)

            # ... for every aircraft
            for aircraft_ref, aircraft in aircraft_dict.items():
                # This if statement is effectively includes constraint C5
                # except it makes the model more efficient by leaving out some decision variables.
                if aircraft["legs"]["viability"].loc[airport_i_ref, airport_j_ref] == 1:
                    decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref] = \
                        model.addVar(vtype=GRB.INTEGER,
                                     name="z-" + aircraft_ref + "--" + airport_i_ref + "->" + airport_j_ref)

# ======================================================================================================
# =============================================================================== Setting up constraints
# ======================================================================================================

# ----------------> Demand constraint
if demand_constraints:
    # ----------- Demand Verification: # PAX <= demand C1
    # ... for every node-node (leg)
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            constraint_l = gp.LinExpr()

            constraint_l += decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref] \
                            + decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref]

            model.addConstr(constraint_l <= demand_df.loc[airport_i_ref, airport_j_ref],
                            name="Constraint-C1-" + airport_i_ref + "->" + airport_j_ref)

    # TODO: Check line nb
    """
    This constraint was left out as it was indirectly implemented using the conditional statement on line 72
    """
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
    #             constraint_r = demand_df.loc[airport_i_ref, airport_j_ref]
    #
    #         model.addConstr(constraint_l <= constraint_r,
    #                         name="Constraint-C1*-" + airport_i_ref + "->" + airport_j_ref)

# ----------------> Capacity: # PAX in each leg <= seat available per leg C2
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

# ----------------> Continuity constraint: #AC inbound = #AC outbound C3
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

# -----------------> AC Productivity: hours of operation <= BT * #AC C4
if AC_productivity:
    # ... for every aircraft
    for aircraft_ref, aircraft in aircraft_dict.items():
        constraint_l = gp.LinExpr()
        constraint_r = gp.LinExpr()

        # ... for every node-node (leg)
        for airport_i_ref, airport_i in airports_dict.items():
            for airport_j_ref, airport_j in airports_dict.items():
                constraint_l += (aircraft["legs"]["duration"].loc[airport_i_ref, airport_j_ref]
                                 + aircraft["avg TAT"]/60 * (1 + (airport_j_ref == hub_ref) * 0.5)) \
                                * decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]

        constraint_r += max_continuous_operation * decision_variable_dict["aircrafts"][aircraft_ref]["count"]

        model.addConstr(constraint_l <= constraint_r,
                        name="Constraint-C4-" + aircraft_ref)

# -----------------> constraint C5 (range)
"""
This constraint was left out as it was indirectly implemented using the conditional statement on line 81 
in the decision variables generation
"""

# -----------------> constraint C6 (budget)
"""
This constraint was left out as the budget is not constrained in this assignment
"""

# ======================================================================================================
# ============================================================================= Building objective function
# ======================================================================================================

# -----------------> Initiating and filling the objective function as a linear expression
objective_function = gp.LinExpr()

# ... for every node-node (leg)
for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():
        # ---> Yield
        objective_function += yield_df.loc[airport_i_ref, airport_j_ref] \
                              * distances_df.loc[airport_i_ref, airport_j_ref] \
                              * (decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref]
                                 + decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref] * 0.9)

        # ---> Flight Costs
        # ... for every aircraft
        for aircraft_ref, aircraft in aircraft_dict.items():
            objective_function -= aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] \
                                  * decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]

# ---> Lease Costs
# ... for every aircraft
for aircraft_ref, aircraft in aircraft_dict.items():
    # Lease costs
    objective_function -= decision_variable_dict["aircrafts"][aircraft_ref]["count"] \
                          * aircraft["weekly lease cost"]

# -----------------> Setting objective
model.setObjective(objective_function, GRB.MAXIMIZE)

# ======================================================================================================
# ======================================================================================= Optimise model
# ======================================================================================================

model.write("Model_1B.lp")
print("Model 1 compiled!!!\n")
model.optimize()
model.printStats()

# ======================================================================================================
# ======================================================================================== Print results
# ======================================================================================================

print("\n\n===========================================================================================================")

# -----------------> Make dataframes with the results as numbers
flow_x = deepcopy(edges_df)
flow_w = deepcopy(edges_df)
zs = {}
for aircraft_ref, aircraft in aircraft_dict.items():
    zs[aircraft_ref] = deepcopy(edges_df)
total_capacity = deepcopy(edges_df)

for airport_i_ref, airport_i in airports_dict.items():
    for airport_j_ref, airport_j in airports_dict.items():

        if type(decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref]) != int:
            flow_x.loc[airport_i_ref, airport_j_ref] = \
                int(decision_variable_dict["legs"]["x"].loc[airport_i_ref, airport_j_ref].X)

        if type(decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref]) != int:
            flow_w.loc[airport_i_ref, airport_j_ref] = \
                int(decision_variable_dict["legs"]["w"].loc[airport_i_ref, airport_j_ref].X)

        for aircraft_ref, aircraft in aircraft_dict.items():
            if type(decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]) != int:
                zs[aircraft_ref].loc[airport_i_ref,airport_j_ref] = decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref].X

                total_capacity.loc[airport_i_ref, airport_j_ref] += \
                    int( round(decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref].X \
                    * aircraft['seats']*average_load_factor) ) # could be non int due the 80% LF, so its rounded

print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  Flow_x dataframe")
print(flow_x.to_string())
flow_x.to_csv("flow_x_1b.csv")

print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  Flow_w dataframe")
print(flow_w.to_string())
flow_w.to_csv("flow_w_1b.csv")

print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  z dataframes")
for aircraft_ref, aircraft in aircraft_dict.items():
    print(aircraft_ref)
    print(zs[aircraft_ref].to_string())

print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Total_capacity dataframe")
print(total_capacity.to_string())
total_capacity.to_csv("total_capacity_1b.csv")

print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ demand_df dataframe")
print(demand_df.to_string())
demand_df.to_csv("demand_df_1b.csv")

# -----------------> Print amount of aircrafts
print("\nAircraft count:")
for aircraft_ref, aircraft in aircraft_dict.items():
    print(" -", aircraft_ref, ':', int(decision_variable_dict["aircrafts"][aircraft_ref]["count"].X))

sum_cap = 0
for i in total_capacity.index:
    for j in total_capacity.columns:
        sum_cap += total_capacity.loc[i, j]

sum_dem = 0
for i in demand_df.index:
    for j in demand_df.columns:
        sum_dem += demand_df.loc[i, j]

sum_flow = 0
for i in flow_x.index:
    for j in flow_x.columns:
        sum_flow += flow_x.loc[i, j] + flow_w.loc[i, j]

spillage = 0
spoilage = 0
for i in flow_x.columns:
    for j in flow_x.index:
        diff = demand_df.loc[i, j] - total_capacity.loc[i, j]
        if diff >= 0:   # Excess demand
            spillage += diff

        else:   # Excess capacity
            spoilage += abs(diff)

print('\nTotal flow:', sum_flow)
print('Total capacity:', sum_cap)
print('Total demand:', sum_dem)
print("\nSpillage:", spillage)
print("Spoilage:", spoilage)

df_of_unreachables = total_capacity.loc[:, total_capacity.sum(axis=0) == 0]
print("\nUnreachable airports:", ', '.join(list(df_of_unreachables)))


total = 0
for j in df_of_unreachables.columns:
    sum_demand = 0
    for i in df_of_unreachables.index:
        sum_demand += demand_df.loc[i, j]

    print(" - Demand", j, ":", sum_demand)
    total += sum_demand

print("Unreachable airport total demand:", total)


lats = []
lons = []
names =[]
for airport_ref, airport in airports_dict.items():
    lats.append(airport['lat'])
    lons.append(airport['lon'])
    names.append(airport_ref)

fig = go.Figure()

fig.add_trace(go.Scattergeo(
    # locations=["Sweden"],
    # locationmode='country names',
    lon = lats,
    lat = lons,
    hoverinfo = 'text',
    text = names,
    mode = 'markers',
    marker = dict(
        size = 5,
        color = 'rgb(255, 0, 0)',
        line = dict(
            width = 3,
            color = 'rgba(68, 68, 68, 0)'
        )
    )))


flight_paths = []
for aircraft_ref, aircraft in aircraft_dict.items():
    for airport_i_ref, airport_i in airports_dict.items():
        for airport_j_ref, airport_j in airports_dict.items():
            z = decision_variable_dict["aircrafts"][aircraft_ref]["z"].loc[airport_i_ref, airport_j_ref]
            if type(z) != int:
                if z.X != 0:
                    fig.add_trace(
                        go.Scattergeo(
                            # locations=["Sweden"],
                            # locationmode='country names',
                            lon = [airport_i['lon'], airport_j['lon']],
                            lat = [airport_i['lat'], airport_j['lat']],
                            mode = 'lines',
                            line = dict(width = 1.3,color = aircraft['color']),
                            opacity = z.X/11,
                        )
                    )

fig.update_layout(
    title_text = 'Feb. 2011 American Airline flight paths<br>(Hover for airport names)',
    showlegend = False,
    geo = dict(
        scope = 'europe',
        projection_type = 'azimuthal equal area',
        showland = True,
        landcolor = 'rgb(243, 243, 243)',
        countrycolor = 'rgb(204, 204, 204)',
    ),
)

fig.show()
