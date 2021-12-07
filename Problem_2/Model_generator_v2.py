
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

__version__ = '1.1.1'

################################################################################################################


class Model:
    def __init__(self, network):
        # -> Setting up records
        self.network = network()

        # -> Creating model
        self.model = gp.Model("APO_assignment_model")
        self.decision_variable_dict = self.setup_decision_variables()

        # --> Disabling the gurobi console output, set to 1 to enable
        self.model.Params.OutputFlag = 1

        # --> Setting up constraints
        # Routes conditionals
        self.build_route_conditionals()

        # Demand constraint
        self.build_demand_constraints()

        # Flow constraint
        self.build_flow_constraints()

        # Aircraft utilisation constraint

        # Aircraft allocation constraints

        # Fleet budget constraint

        # --> Building objective function
    def setup_decision_variables(self):
        # Routes: binary list, x: integer list, w: integer list
        decision_variable_dict = {"Included": {},
                                  "Not_included": {}}

        # -> Creating structure
        # ... for every aircraft
        for aircraft_ref, aircraft in self.network.ac_dict.items():
            # -> Create network edge dataframe
            edges_df = pd.DataFrame(index=np.arange(len(self.network.airports_dict)),
                                    columns=np.arange(len(self.network.airports_dict)))

            edges_df.columns = list(node for node in self.network.airports_dict.keys())
            edges_df = edges_df.reindex(index=list(node for node in self.network.airports_dict.keys()), fill_value=0)

            # -> Adding aircraft count decision variable
            decision_variable_dict[aircraft_ref] = {"aircraft count": self.model.addVar(vtype=GRB.INTEGER,
                                                                                        name="# " + aircraft_ref)}
            # ... for every route
            for route_ref, route in self.network.routes_dict.items():
                decision_variable_dict[aircraft_ref][route_ref] = {"x": deepcopy(edges_df),
                                                                   "w": deepcopy(edges_df)}

                if aircraft["routes viability"][route_ref] == 0:
                    decision_variable_dict[aircraft_ref][route_ref]["flight count"] = 0

                else:
                    decision_variable_dict[aircraft_ref][route_ref]["flight count"] = \
                        self.model.addVar(vtype=GRB.INTEGER, name="# " + aircraft_ref)

                    # -> Adding x and w decision variables
                    # ... for every leg
                    for airport_i_ref, airport_i in self.network.airports_dict.items():
                        for airport_j_ref, airport_j in self.network.airports_dict.items():
                            if airport_i_ref == airport_j_ref:
                                continue
                            else:
                                if self.network.routes_dict[route_ref]["path df"].loc[airport_i_ref, airport_j_ref] == 1:
                                    variable_name = "x - " + aircraft_ref + " - " + route_ref + " - " + airport_i_ref + "->" + airport_j_ref
                                    decision_variable_dict[aircraft_ref][route_ref]["x"].loc[airport_i_ref, airport_j_ref] = \
                                        self.model.addVar(vtype=GRB.INTEGER, name=variable_name)

                                    variable_name = "w - " + aircraft_ref + " - " + route_ref + " - " + airport_i_ref + "->" + airport_j_ref
                                    decision_variable_dict[aircraft_ref][route_ref]["w"].loc[airport_i_ref, airport_j_ref] = \
                                        self.model.addVar(vtype=GRB.INTEGER, name=variable_name)

        return decision_variable_dict

    def build_objective(self):
        """
        Used to generate the objective function of the model

        :return: None
        """

        # --> Initiating objective function linear expression
        objective_function = gp.LinExpr()

        # --> Adding decision variables
        # ... for every aircraft
        for aircraft_ref, aircraft in self.network.ac_dict.items():

            # ... for every route
            for route_ref, route in self.network.routes_dict.items():

                # ... for every leg making up the route
                for airport_i_ref, airport_i in self.network.airports_dict.items():
                    for airport_j_ref, airport_j in self.network.airports_dict.items():
                        if airport_i_ref == airport_j_ref:
                            continue
                        else:

                            # > For every other route served by AC type
                            leg_ws = []
                            for route_ref_2, route_2 in self.network.routes_dict.items():
                                if route_ref_2 == route_ref:
                                    pass
                                else:
                                    leg_ws.append(self.decision_variable_dict[aircraft_ref][route_ref_2]["w"].loc[airport_i_ref, airport_j_ref])

                            # -> Adding total yield per leg
                            objective_function += aircraft["legs"]["yield per RPK"].loc[airport_i_ref, airport_j_ref] \
                                                  * self.network.distances_df.loc[airport_i_ref, airport_j_ref] \
                                                  * (self.decision_variable_dict[aircraft_ref][route_ref]["x"].loc[airport_i_ref, airport_j_ref]
                                                     + sum(leg_ws))

                            # -> Adding total cost per leg
                            objective_function -= aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] \
                                                  * self.network.distances_df.loc[airport_i_ref, airport_j_ref] \
                                                  * aircraft["seats"] \
                                                  * self.decision_variable_dict[aircraft_ref][route_ref]["flight count"]

                            # -> Adding leading cost per week for ac type
                            objective_function -= self.decision_variable_dict[aircraft_ref]["aircraft count"] \
                                                  * aircraft["weekly lease cost"]

        # --> Setting objective
        self.model.setObjective(objective_function, GRB.MAXIMIZE)

        return

    def build_demand_constraints(self):
        """
        Demand constraints:

        Overall leg demand:
            "Total flow assigned for leg <= demand for leg"

        Demand 2:
            "Direct flow assigned <= demand * auxiliary_parameter_route"

        Demand 3:
            "Transfer flow assigned <= demand * auxiliary_parameter_route * "

        note: each constraint sums flows across aircraft types per routes, legs are directional

        :return:
        """
        # ----------- Overall leg demand
        # ... for every possible leg
        for airport_i_ref, airport_i in self.network.airports_dict.items():
            for airport_j_ref, airport_j in self.network.airports_dict.items():
                # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg
                constraint_l = gp.LinExpr()

                # ... for every route
                for route_ref, route in self.network.routes_dict.items():

                    # ... for every aircraft
                    for aircraft_ref, aircraft in self.network.ac_dict.items():

                        # > For every other route served by AC type
                        leg_ws = []
                        for route_ref_2, route_2 in self.network.routes_dict.items():
                            if route_ref_2 == route_ref:
                                pass
                            else:
                                leg_ws.append(self.decision_variable_dict[aircraft_ref][route_ref_2]["w"].loc[airport_i_ref, airport_j_ref])

                        constraint_l += self.decision_variable_dict[aircraft_ref][route_ref]["x"].loc[airport_i_ref, airport_j_ref] \
                                        + sum(leg_ws)

                self.model.addConstr(constraint_l <= self.network.demand_df.loc[airport_i_ref, airport_j_ref],
                                     "Constraint - Total demand - " + airport_i_ref + "->" + airport_j_ref)

        # ----------- Direct leg demand
        # ... for every possible leg
        for airport_i_ref, airport_i in self.network.airports_dict.items():
            for airport_j_ref, airport_j in self.network.airports_dict.items():

                # ... for every route
                for route_ref, route in self.network.routes_dict.items():
                    # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg per route
                    constraint_l = gp.LinExpr()

                    # ... for every aircraft
                    for aircraft_ref, aircraft in self.network.ac_dict.items():
                        constraint_l += \
                            self.decision_variable_dict[aircraft_ref][route_ref]["x"].loc[airport_i_ref, airport_j_ref]

                    self.model.addConstr(constraint_l <= self.network.demand_df.loc[airport_i_ref, airport_j_ref]
                                         * self.network.routes_dict[route_ref]["path df"].loc[airport_i_ref, airport_j_ref],
                                         "Constraint - Direct demand - " + route_ref + " - " + airport_i_ref + "->" + airport_j_ref)

        # ----------- Indirect leg demand
        # ... for every possible leg
        for airport_i_ref, airport_i in self.network.airports_dict.items():
            for airport_j_ref, airport_j in self.network.airports_dict.items():

                # ... for every route
                for route_ref, route in self.network.routes_dict.items():

                    # ... for every route 2
                    for route_ref_2, route_2 in self.network.routes_dict.items():
                        if route_ref == route_ref_2:
                            pass
                        else:
                            # ~~~~~~~~~~~~~~~~~~~~~~~~~ 1 constraint per leg per route per route
                            constraint_l = gp.LinExpr()

                            # ... for every aircraft
                            for aircraft_ref, aircraft in self.network.ac_dict.items():
                                constraint_l += \
                                    self.decision_variable_dict[aircraft_ref][route_ref_2]["w"].loc[airport_i_ref, airport_j_ref]

                            self.model.addConstr(constraint_l <= self.network.demand_df.loc[airport_i_ref, airport_j_ref]
                                                 * self.network.routes_dict[route_ref]["path df"].loc[airport_i_ref, airport_j_ref]
                                                 * self.network.routes_dict[route_ref_2]["path df"].loc[airport_i_ref, airport_j_ref],
                                                 "Constraint - Indirect demand - " + route_ref + "|" + route_ref_2 + " - " + airport_i_ref + "->" + airport_j_ref)

        return

    def build_flow_constraints(self):
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
        for destination_ref, destination in self.network.airports_dict.items():
            if destination_ref != self.network.hub_ref:
                constraint_l = gp.LinExpr()
                constraint_r = gp.LinExpr()

                for aircraft_ref, aircraft in self.network.ac_dict.items():
                    constraint_l += self.decision_variable_dict[aircraft_ref]["x"].loc[self.network.hub_ref, destination_ref]
                    constraint_l += self.decision_variable_dict[aircraft_ref]["w"].loc[self.network.hub_ref, destination_ref]

                    constraint_r += self.decision_variable_dict[aircraft_ref]["flight count"] \
                                    * self.network.ac_dict[aircraft_ref]["seats"] \
                                    * self.network.average_load_factor

                self.model.addConstr(constraint_l <= constraint_r, "Constraint - Flow - " + self.network.hub_ref + "->" + destination_ref)

        # ----------- Between nodes constraint (excluding hub)
        for origin_ref, origin in self.network.airports_dict.items():
            if origin_ref != self.network.hub_ref:
                for destination_ref, destination in self.network.airports_dict.items():
                    if destination_ref != self.network.hub_ref:
                        constraint_l = gp.LinExpr()
                        constraint_r = gp.LinExpr()

                        for aircraft_ref, aircraft in self.network.ac_dict.items():
                            constraint_l += self.decision_variable_dict[aircraft_ref]["x"].loc[origin_ref, destination_ref]
                            constraint_l += self.decision_variable_dict[aircraft_ref]["w"].loc[origin_ref, destination_ref]

                            constraint_r += self.decision_variable_dict[aircraft_ref]["flight count"] \
                                            * self.network.ac_dict[aircraft_ref]["seats"] \
                                            * self.network.average_load_factor

                        self.model.addConstr(constraint_l <= constraint_r, "Constraint - Flow - " + origin_ref + "->" + destination_ref)

        # ----------- To hub constraint
        for origin_ref, origin in self.network.airports_dict.items():
            if origin_ref != self.network.hub_ref:
                constraint_l = gp.LinExpr()
                constraint_r = gp.LinExpr()

                for aircraft_ref, aircraft in self.network.ac_dict.items():
                    constraint_l += self.decision_variable_dict[aircraft_ref]["x"].loc[origin_ref, self.network.hub_ref]
                    constraint_l += self.decision_variable_dict[aircraft_ref]["w"].loc[origin_ref, self.network.hub_ref]

                    constraint_r += self.decision_variable_dict[aircraft_ref]["flight count"] \
                                    * self.network.ac_dict[aircraft_ref]["seats"] \
                                    * self.network.average_load_factor

                self.model.addConstr(constraint_l <= constraint_r, "Constraint - Flow - " + origin_ref + "->" + self.network.hub_ref)

        return

    def recursive_add_to_linear_expression(self, decision_variable_dict, linear_expression):
        """
        Recursively add all the variables stored in a dictionary to a gurobi linear expression

        :param decision_variable_dict: Dictionary to be recursively iterated through
        :param linear_expression: Linear expression to append to
        :return: augmented linear expression
        """

        for _, variable in decision_variable_dict.items():
            if isinstance(variable, dict):
                self.recursive_add_to_linear_expression(variable, linear_expression)
            else:
                if variable is not None:
                    linear_expression += variable
        return linear_expression

    def output_to_lp(self):
        """
        Used to generate an LP file from the generated model

        :return: None
        """

        self.model.write("Model.lp")

    def optimize(self):
        self.model.optimize()


if __name__ == '__main__':
    from Network_generator import Network

    model = Model(network=Network())
