import gurobipy
import numpy as np
import gurobipy as gp
from gurobipy import GRB
from gurobipy import Column


# Own modules
from TSN import Time_space_network
__version__ = '1.1.1'

################################################################################################################


class CG:
    def __init__(self,max_time = 3600):
        # -> Generate data
        self.TSN = Time_space_network()

        self.path_dict = self.create_initial_paths()

        self.master = gp.Model("APO_assignment_model_4")

        # # -> Creating decision variables
        # self.decision_variable_dict = self.generate_decision_variables()
        #
        # # -> Add constraints
        # self.add_flight_arc_usage_constraint()
        # self.add_conservation_of_aircraft_flow_constraint()
        # self.add_conservation_of_request_flow_constraint()
        # self.add_weight_capacity_constraint()
        # self.add_net_aircraft_flow_constraint() #not used
        #
        # # -> Add objective function
        # self.add_objective_function()

        self.run()

    def create_initial_paths(self):
        paths_dict = {"request paths": {},
                      "paths": [],
                      "paths containing flight arc": {}}

        for request_id, request in self.TSN.data.request_dict.items():
            paths_dict["request paths"][request_id] = []

            start_node = self.TSN.network[request["release_step"]][request["airport_O"]]
            end_node = self.TSN.network[request["due_step"]][request["airport_D"]]

            for ns_arc in self.TSN.ns_arc_lst:
                if ns_arc.origin == start_node.ref and ns_arc.destination == end_node.ref:
                    paths_dict["request paths"][request_id].append([ns_arc])
                    break

        return  paths_dict

    def add_path(self,request_id,vars):
        # -> add path to self.path_dict

        # -> collum to master based on path


    # -> Marginal cost per flight arc
    def MCf(self,flight_arc):
        i = self.TSN.data.airport_dict[flight_arc.origin_airport]["index"]
        j = self.TSN.data.airport_dict[flight_arc.destination_airport]["index"]
        n = len(self.TSN.data.airport_dict)
        depart_time = flight_arc.origin_timestep * self.TSN.data.timestep_duration
        h = depart_time % 24
        d = (depart_time - h) / 24 + 1
        # print(f"time = {depart_time}, d = {d}, h = {h}")
        MCf = 0.05 * (i + j) / (2 * n - 1) + 0.15 * np.sin(2 * np.pi * h / 24) ** 2 + 0.005 * d  # MU/(km*ton)
        return MCf

    def run(self):
        new_column_added = True

        while new_column_added:
            linear_relaxation = self.master.relax()
            linear_relaxation.optimize()

            # -> Obtain dual values for each constraint (based on current master model with latest columns)
            # pi_f, pi_r
            pi = {"f": {},
                  "r": {}}

            for c in linear_relaxation.getConstrs():
                if "Conservation_of_request_flow" in c.name:    #TODO: Check c.name
                    # f"Conservation_of_request_flow-{t}-{airport_ref}-{r}"
                    r = c.name.split('-')[-1]
                    pi["r"][r] = c.Pi

                if "Weight capacity" in c.name:    #TODO: Check c.name
                    # f"Weight capacity-{f}"
                    f = c.name.split('-')[-1]
                    pi["f"][f] = c.Pi

            # ... for every request
            for request_id, request in self.TSN.data.request_dict.items():
                # -> Create secondary model
                RC = gp.Model(request_id)

                # -> add decision variables
                x = {}
                for arc in self.TSN.arc_lst_no_ns:
                    a = arc.ref
                    x[a] = RC.addVar(vtype=GRB.BINARY,
                                     name=f"x-{a}")

                # -> add constraints
                # ... per node
                for t, timestep in enumerate(self.TSN.network):  # ... per timestep
                    for airport_ref, node in timestep.items():  # ... per airport
                        constraint_l = gp.LinExpr()

                        # ... per arc existing the node
                        for arc in node.out_arc_lst:
                            a = arc.ref
                            constraint_l -= x[a] # TODO: dubble check - and + for delta

                        # ... per arc entering the node
                        for arc in node.in_arc_lst:
                            a = arc.ref
                            constraint_l += x[a] # TODO: dubble check - and + for delta

                        RC.addConstr(constraint_l == node.v[r],
                                     name=f"Constraint-{t}-{airport_ref}")

                # -> add objective
                objective_function = gp.LinExpr()
                for flight_arc in self.TSN.flight_arc_lst:
                    f = flight_arc.ref
                    Df = self.TSN.data.distance_df.loc[flight_arc.origin_airport, flight_arc.destination_airport]
                    MCf = self.MCf(flight_arc)
                    Wr = request["weight"] #ton

                    objective_function += (MCf*Df*Wr - Wr*pi["f"][f])*x[f]

                objective_function -= pi["r"][r]
                RC.setObjective(objective_function,GRB.MINIMIZE)

                # -> optimize RC
                RC.optimize()
                new_column_added = False
                if RC.ObjVal < 0:
                    self.add_path(r, RC.getVars())
                    new_column_added = True

