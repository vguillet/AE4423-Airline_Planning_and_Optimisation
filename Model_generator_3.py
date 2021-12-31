
################################################################################################################
"""

"""

# Built-in/Generic Imports
from copy import deepcopy
from math import log

# Libs
import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB
import plotly.graph_objects as go

# Own modules
from TSN import Time_space_network
__version__ = '1.1.1'

################################################################################################################


class Model_3:
    def __init__(self):
        # -> Generate data
        self.TSN = Time_space_network()

        # -> Creating model
        self.model = gp.Model("APO_assignment_model_3")

        # -> Adjusting settings
        display_progress_bars = True

        self.model.Params.OutputFlag = 1    # Disabling the gurobi console output, set to 1 to enable

        self.model.setParam("TimeLimit", 1800)

        # -> Creating decision variables
        self.decision_variable_dict = self.generate_decision_variables()

        # -> Add constraints
        self.add_flight_arc_usage_constraint(display_progress_bars)
        self.add_conservation_of_aircraft_flow_constraint(display_progress_bars)
        self.add_conservation_of_request_flow_constraint(display_progress_bars)
        self.add_weight_capacity_constraint(display_progress_bars)
        self.add_net_aircraft_flow_constraint(display_progress_bars)

        # -> Add objective function
        self.add_objective_function(display_progress_bars)

        # -> Write model
        self.model.write("Model_3.lp")

    def generate_decision_variables(self):
        decision_variable_dict = {"x": {},
                                  "y": {},
                                  "z": {}}

        # -> Adding flight arc decision variables - x_f_k
        for arc in self.TSN.flight_arc_lst:
            decision_variable_dict["x"][arc.ref] = {}

            for aircraft_ref, aircraft in self.TSN.data.aircraft_dict.items():
                decision_variable_dict["x"][arc.ref][aircraft_ref] = \
                    self.model.addVar(vtype=GRB.BINARY,
                                      name=f"x-{arc.ref}-{aircraft_ref}")

        # -> Adding ground arc decision variables - y_g_k
        for arc in self.TSN.ground_arc_lst:
            decision_variable_dict["y"][arc.ref] = {}

            for aircraft_ref, aircraft in self.TSN.data.aircraft_dict.items():
                decision_variable_dict["y"][arc.ref][aircraft_ref] = \
                    self.model.addVar(vtype=GRB.INTEGER,
                                      name=f"y-{arc.ref}-{aircraft_ref}")

        # -> Adding arc-request decision variables - z_a_r
        for arc in self.TSN.arc_lst:
            decision_variable_dict["z"][arc.ref] = {}

            for request_ID, request in self.TSN.data.request_dict.items():
                decision_variable_dict["z"][arc.ref][request_ID] = \
                    self.model.addVar(vtype=GRB.BINARY,
                                      name=f"z-{arc.ref}-{request_ID}")

        return decision_variable_dict

    def add_flight_arc_usage_constraint(self, display_progress_bars=False):

        # ... per flight arc
        for f in self.decision_variable_dict["x"].keys():
            constraint_l = gp.LinExpr()

            # ... per aircraft type
            for k in self.decision_variable_dict["x"][f].keys():
                constraint_l += self.decision_variable_dict["x"][f][k]

            self.model.addConstr(constraint_l <= 1,
                                 name=f"Flight_arc_usage-{f}")

    def add_conservation_of_aircraft_flow_constraint(self, display_progress_bars=False):
        pass

    def add_conservation_of_request_flow_constraint(self, display_progress_bars=False):
        pass

    def add_weight_capacity_constraint(self, display_progress_bars=False):
        # TODO: Double check constraint
        # ... per flight arc
        for f in self.decision_variable_dict["x"].keys():
            constraint_l = gp.LinExpr()
            constraint_r = gp.LinExpr()

            # ... per request
            for r, request in self.TSN.data.request_dict.items():
                constraint_l += request["weight"] * self.decision_variable_dict["z"][f][r]

            # ... per aircraft
            for k, aircraft in self.TSN.data.aircraft_dict.items():
                constraint_r += aircraft["payload"] * self.decision_variable_dict["x"][f][k]

            self.model.addConstr(constraint_l <= constraint_r,
                                 name=f"Weight capacity-{f}")

    def add_net_aircraft_flow_constraint(self, display_progress_bars=False):
        pass

    def add_objective_function(self, display_progress_bars=False):
        pass


if __name__ == "__main__":
    # ======================================================================================================
    # ============================================================================= Optimise model
    # ======================================================================================================

    model = Model_3()

    print("\nModel compiled!!!")
