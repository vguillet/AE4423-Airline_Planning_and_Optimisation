
################################################################################################################
"""

"""

# Built-in/Generic Imports
import random

# Libs
import numpy as np
import gurobipy as gp
from gurobipy import GRB

# Own modules

__version__ = '1.1.1'

################################################################################################################


class Model:
    def __init__(self, network):
        # -> Setting up records
        self.network = network

        self.decision_variable_dict = self.setup_decision_variables()

        # -> Creating model
        self.model = gp.Model("APO_assignment_model")

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
        decision_variable_dict = {"AC 1": {"routes": [],
                                                  "x": [],
                                                  "w": []},
                                         "AC 2": {"routes": [],
                                                  "x": [],
                                                  "w": []},
                                         "AC 3": {"routes": [],
                                                  "x": [],
                                                  "w": []},
                                         "AC 4": {"routes": [],
                                                  "x": [],
                                                  "w": []},
                                         "AC 5": {"routes": [],
                                                  "x": [],
                                                  "w": []},
                                  "Included": {},
                                  "Not_included": {}}

        for aircraft_ref in self.network.ac_dict.keys():
            decision_variable_dict[aircraft_ref] = {"AC 1": {"routes": [],
                                                    "x": [],
                                                    "w": []}

            for route_id in range(len(self.network.routes)):
                decision_variable_dict[aircraft_ref]


        return

    def build_objective(self):
        """
        Used to generate the objective function of the model

        :return: None
        """

        # --> Initiating objective function linear expression
        objective_function = gp.LinExpr()

        # --> Adding decision variables
        # ... for each airport i
        for airport_i in self.network.airports_lst:
            # ... for each airport j
            for airport_j in self.network.airports_lst:
                if airport_j == airport_i:
                    continue
                else:
                    # ... for each aircraft type
                    for aircraft in self.network.ac_dict.values():
                        objective_function += aircraft["yield per RPK"] \
                                              * self.network.distances_df.loc[airport_i["ref"], airport_j["ref"]] \
                                              * (self.decision_variable_dict["x"][airport_i["ref"]][airport_j["ref"]]
                                              + sum())

        # --> Setting objective
        self.model.setObjective(objective_function, GRB.MAXIMIZE)

        return

    def build__constraints(self):
        """
        Used to generate the demand constraints (1 per student)

            "sum of decisions variables of all houses for a given student <= 1"

        :return: None
        """
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
