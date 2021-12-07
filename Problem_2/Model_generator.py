
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
import pandas as pd

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
        for aircraft_ref, aircraft in self.network.ac_dict.items():
            # -> Create network edge dataframe
            edges_df = pd.DataFrame(index=np.arange(len(self.network.airports_dict)),
                                    columns=np.arange(len(self.network.airports_dict)))

            edges_df.columns = list(node for node in self.network.airports_dict.keys())
            edges_df = edges_df.reindex(index=list(node for node in self.network.airports_dict.keys()), fill_value=None)

            # -> Creating skeleton dictionary
            decision_variable_dict[aircraft_ref] = {"aircraft count": deepcopy(edges_df),
                                                    "flight count": deepcopy(edges_df),
                                                    "x": deepcopy(edges_df),
                                                    "w": deepcopy(edges_df),
                                                    "routes counter": {}}

        # -> Adding variables
            for airport_i_ref, airport_i in self.network.airports_dict.items():
                for airport_j_ref, airport_j in self.network.airports_dict.items():
                    if airport_i_ref == airport_j_ref:
                        continue
                    else:
                        # -> Adding flight count variable
                        variable_name = "fc_" + aircraft_ref + "_" + airport_i_ref + "-" + airport_j_ref

                        decision_variable_dict[aircraft_ref]["flight count"].loc[airport_i_ref, airport_j_ref] = \
                            self.model.addVar(vtype=GRB.INTEGER, name=variable_name)

                        # -> Adding x variable
                        variable_name = "x_" + aircraft_ref + "_" + airport_i_ref + "-" + airport_j_ref

                        decision_variable_dict[aircraft_ref]["x"].loc[airport_i_ref, airport_j_ref] = \
                            self.model.addVar(vtype=GRB.INTEGER, name=variable_name)

                        # -> Adding w variable
                        variable_name = "w_" + aircraft_ref + "_" + airport_i_ref + "-" + airport_j_ref

                        decision_variable_dict[aircraft_ref]["w"].loc[airport_i_ref, airport_j_ref] = \
                            self.model.addVar(vtype=GRB.INTEGER, name=variable_name)

        # -> Adding routes flown counter for each aircraft
            for route_ref, route in self.network.routes_dict.items():
                # Fetching viability boolean for given aircraft/route combination
                variable_name = "route_counter_" + aircraft_ref + "_" + route_ref
                if self.aircraft["routes viability"][route_ref] == 0:
                    decision_variable_dict[aircraft_ref]["routes counter"][route_ref] = 0

                else:
                    decision_variable_dict[aircraft_ref]["routes counter"][route_ref] = \
                        self.model.addVar(vtype=GRB.INTEGER, name=variable_name)

        print(decision_variable_dict)
        return decision_variable_dict

    def build_objective(self):
        """
        Used to generate the objective function of the model

        :return: None
        """

        # --> Initiating objective function linear expression
        objective_function = gp.LinExpr()

        # --> Adding decision variables
        # -> For each aircraft type
        for aircraft_ref, aircraft in self.network.ac_dict.items():

            # -> ... for each route
            for route_ref, route in self.network.routes_dict.items():

                # -> ... for each route legs
                for i in range(len(route["path"]) - 1):
                    airport_i_ref = route["path"][i]
                    airport_j_ref = route["path"][i + 1]

                    # -> Adding yield per leg
                    objective_function += aircraft["legs"]["yield per RPK"].loc[airport_i_ref, airport_j_ref] \
                                          * self.network.distances_df.loc[airport_i_ref, airport_j_ref] \
                                          * (self.decision_variable_dict[aircraft_ref]["x"].loc[airport_i_ref, airport_j_ref]
                                          + self.decision_variable_dict[aircraft_ref]["w"])

                    # objective_function += aircraft["legs"]["yield per RPK"].loc[airport_i_ref, airport_j_ref] \
                    #                       * self.network.distances_df.loc[airport_i_ref, airport_j_ref] \
                    #                       * (self.decision_variable_dict[aircraft_ref]["x"].loc[airport_i_ref, airport_j_ref]
                    #                       + sum(self.decision_variable_dict[aircraft_ref_2]["w"].loc[airport_i_ref, airport_j_ref] for aircraft_ref_2 in self.network.ac_dict.keys()))

                    # -> Adding cost per leg
                    objective_function -= aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] \
                                          * self.network.distances_df.loc[airport_i_ref, airport_j_ref] \
                                          * aircraft["seats"] \
                                          * self.decision_variable_dict[aircraft_ref]["flight count"].loc[airport_i_ref, airport_j_ref]

            # -> Adding leasing cost
            objective_function -= self.decision_variable_dict[aircraft_ref]["aircraft count"] \
                                  * aircraft["weekly lease cost"]

        # --> Setting objective
        self.model.setObjective(objective_function, GRB.MAXIMIZE)

        return

    def build_route_conditionals(self):
        """
        Used to generate route conditional constraints.

        Total # flights on edges == # flights for route containing leg

        :return:
        """

        # ... for every leg
        for airport_i_ref, airport_i in self.network.airports_dict.items():
            for airport_j_ref, airport_j in self.network.airports_dict.items():
                if airport_i_ref == airport_j_ref:
                    continue
                else:
                    # ----------- Sum (flights on edge across aircrafts) == sum(# times a route is served across aircrafts)
                    constraint_l = gp.LinExpr()
                    constraint_r = gp.LinExpr()

                    # ... for every aircraft
                    for aircraft_ref, aircraft in self.network.ac_dict.items():

                        # ... for every route
                        for route_ref, route in self.network.routes_dict.items():
                            for i in range(len(route["path"]) - 1):
                                if route["path"][i] == airport_i_ref and route["path"][j] == airport_j_ref:
                                    # -> Add nb. time route is served
                                    constraint_r += self.decision_variable_dict[aircraft_ref]["routes counter"][route_ref]

                        # -> Add number of time leg is served
                        constraint_l += self.decision_variable_dict[aircraft_ref]["flight count"].loc[airport_i_ref, airport_j_ref]

                    # -> Add constraint to model
                    self.model.addConstr(constraint_l == constraint_r,
                                         "Constraint - Route conditional - " + airport_i_ref + "->" + airport_j_ref)

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
        for origin_ref, origin in self.network.airports_dict.items():
            for destination_ref, destination in self.network.airports_dict.items():
                constraint_l = gp.LinExpr()
                constraint_r = gp.LinExpr()

                for aircraft_ref, aircraft in self.network.ac_dict.items():
                    constraint_l += self.decision_variable_dict[aircraft_ref]["x"].loc[origin_ref, destination_ref]
                    constraint_l += self.decision_variable_dict[aircraft_ref]["w"].loc[origin_ref, destination_ref]

                constraint_r += self.network.demand_df.loc[origin_ref, destination_ref]

                self.model.addConstr(constraint_l <= constraint_r,
                                     "Constraint - Demand - " + origin_ref + "->" + destination_ref)

        # ----------- Demand 2
        # for origin in self.network.airports_lst:
        #     for destination in self.network.airports_lst:
        #         constraint_l = gp.LinExpr()
        #         constraint_r = gp.LinExpr()
        #
        #         for aircraft_ref, aircraft in self.network.ac_dict.items():
        #             constraint_l += self.decision_variable_dict[aircraft_ref]["x"].loc[origin_ref, destination["ref"]]
        #             constraint_l += self.decision_variable_dict[aircraft_ref]["w"].loc[origin_ref, destination["ref"]]
        #
        #         constraint_r += self.network.demand_df.loc[origin_ref, destination["ref"]]
        #
        #         self.model.addConstr(constraint_l <= constraint_r, "Constraint - Demand - ")

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
