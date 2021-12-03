
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
        self.network = network

        # -> Creating model
        self.model = gp.Model("APO_assignment_model")
        self.setup_decision_variable_dict = self.setup_decision_variables()

        # --> Disabling the gurobi console output, set to 1 to enable
        self.model.Params.OutputFlag = 1

        # --> Setting up constraints
        # Demand constraint

        # Flow constraint

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
            edges_df = pd.DataFrame(index=np.arange(len(self.network.airports_lst)),
                                    columns=np.arange(len(self.network.airports_lst)))

            edges_df.columns = list(node["ref"] for node in self.network.airports_lst)
            edges_df = edges_df.reindex(index=list(node["ref"] for node in self.network.airports_lst), fill_value=None)

            # -> Creating skeleton dictionary
            decision_variable_dict[aircraft_ref] = {"aircraft count": deepcopy(edges_df),
                                                    "flight count": deepcopy(edges_df),
                                                    "x": deepcopy(edges_df),
                                                    "w": deepcopy(edges_df)}

        # -> Adding variables
            for airport_i in self.network.airports_lst:
                for airport_j in self.network.airports_lst:
                    if airport_i == airport_j \
                            or decision_variable_dict[aircraft_ref]["x"].loc[airport_i["ref"], airport_j["ref"]] is not np.nan \
                            or decision_variable_dict[aircraft_ref]["x"].loc[airport_j["ref"], airport_i["ref"]] is not np.nan:
                        continue
                    else:
                        # -> Adding flight count variable
                        variable_name = "fc_" + aircraft_ref + "_" + airport_i["ref"] + "-" + airport_j["ref"]

                        decision_variable_dict[aircraft_ref]["flight count"].loc[airport_i["ref"], airport_j["ref"]] = \
                            self.model.addVar(vtype=GRB.INTEGER, name=variable_name)

                        # -> Adding x variable
                        variable_name = "x_" + aircraft_ref + "_" + airport_i["ref"] + "-" + airport_j["ref"]

                        decision_variable_dict[aircraft_ref]["x"].loc[airport_i["ref"], airport_j["ref"]] = \
                            self.model.addVar(vtype=GRB.INTEGER, name=variable_name)

                        # -> Adding w variable
                        variable_name = "w_" + aircraft_ref + "_" + airport_i["ref"] + "-" + airport_j["ref"]

                        decision_variable_dict[aircraft_ref]["w"].loc[airport_i["ref"], airport_j["ref"]] = \
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
                    airport_i = route["path"][i]
                    airport_j = route["path"][i + 1]

                    # -> Adding yield
                    objective_function += aircraft["legs"]["yield per RPK"].loc[airport_i, airport_j] \
                                          * self.network.distances_df.loc[airport_i, airport_j] \
                                          * (self.decision_variable_dict[aircraft_ref]["x"].loc[airport_i, airport_j],
                                          + sum(self.decision_variable_dict[aircraft_ref_2]["w"].loc[airport_i, airport_j] for aircraft_ref_2 in self.network.ac_dict.keys()))

                    # -> Adding cost
                    objective_function -= aircraft["legs"]["total operating cost"].loc[airport_i, airport_j] \
                                          * self.network.distances_df.loc[airport_i, airport_j] \
                                          * aircraft["seats"] \
                                          * self.decision_variable_dict[aircraft_ref]["flight count"].loc[airport_i, airport_j]

        # --> Setting objective
        self.model.setObjective(objective_function, GRB.MAXIMIZE)

        return

    def build_flow_constraints(self):
        """
        Used to generate the flow constraints (1 for from hub to node, 1 for from node to node, 1 for from node to hub)

        from the hub node:
            "sum of flow from hub + sum of flow through hub <= # flights * # seats per aircraft * avg. load factor"

        between spokes

        to the hub node:
            "sum of flow to hub + sum of flow through hub <= # flights * # seats per aircraft * avg. load factor"

        :return: None
        """

        for destination in self.network.airports_lst:
            if destination["ref"] != self.network.hub_ref:
                for aircraft_ref, aircraft in self.network.ac_dict.items():
                    pass

        # sum(self.build_flow_constraints())

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
