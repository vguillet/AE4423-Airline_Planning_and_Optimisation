import numpy as np
import gurobipy as gp
from gurobipy import GRB

# Own modules
from TSN import Time_space_network
__version__ = '1.1.1'

################################################################################################################


class Path:
    def __init__(self, request_id, arc_list, path_number):
        self.arcs = arc_list
        self.flight_arcs = self.find_flight_arcs()

        if arc_list[0].type == "NS":
            self.type = "NS"
        else:
            self.type = "Service"

        self.request_id = request_id
        # self.ref = f"path-{self.request_id}-{'->'.join([arc.ref for arc in self.arcs])}"
        self.ref = f"{self.request_id}-{path_number}"

    def find_flight_arcs(self):
        tmp = []
        for arc in self.arcs:
            if arc.type == "Flight":
                tmp.append(arc)
        return tmp


class CG:
    def __init__(self):
        # -> Generate data
        self.TSN = Time_space_network()

        self.path_count = 0
        self.path_dict = self.create_initial_paths()

        # -> Initialize model object
        self.master = None
        self.decision_variable_dict = None

        # -> Initial build model
        self.rebuild_master()

        # -> Run compilers
        self.run()

        print("\nModel compiled!!!")

        # -> Write model
        self.master.write("Model_4.lp")
        self.master.printStats()
        self.master.optimize()

        print("\nModel optimized!!!")

    def generate_decision_variables(self):
        decision_variable_dict = {"x": {},      # FLight arc decision variables
                                  "y": {},      # Ground arc decision variables
                                  "z": {}}      # All path-request decision variables

        # -> Adding flight arc decision variables - x_f_k
        for flight_arc in self.TSN.flight_arc_lst:
            f = flight_arc.ref
            decision_variable_dict["x"][f] = {}

            for k, aircraft in self.TSN.data.aircraft_dict.items():
                decision_variable_dict["x"][f][k] = \
                    self.master.addVar(vtype=GRB.BINARY,
                                       name=f"x-{f}-{k}")

        # -> Adding ground arc decision variables - y_g_k
        for ground_arc in self.TSN.ground_arc_lst:
            g = ground_arc.ref
            decision_variable_dict["y"][g] = {}

            for k, aircraft in self.TSN.data.aircraft_dict.items():
                decision_variable_dict["y"][g][k] = \
                    self.master.addVar(vtype=GRB.INTEGER,
                                       name=f"y-{g}-{k}")

        # -> Adding arc-request decision variables - z_p_r
        for p, path in self.path_dict["paths"].items():
            decision_variable_dict["z"][p] = {}

            for r, request in self.TSN.data.request_dict.items():
                if path.request_id == r:
                    decision_variable_dict["z"][p][r] = self.master.addVar(vtype=GRB.BINARY,
                                                                           name=f"z-{p}-#{r}#")
                else:
                    decision_variable_dict["z"][p][r] = 0
        # print(decision_variable_dict["z"])

        # for arc in self.TSN.arc_lst:
        #     a = arc.ref
        #     decision_variable_dict["z"][a] = {}
        #
        #     for r, request in self.TSN.data.request_dict.items(): #TODO: these if statementes are no where mentioned in the assignment but they should be here right?
        #         decision_variable_dict["z"][a][r] = 0
        #         if arc.type == "NS":
        #             if arc.request_id != r:
        #                 continue
        #         decision_variable_dict["z"][a][r] = \
        #             self.model.addVar(vtype=GRB.BINARY,
        #                               name=f"z-{a}-#{r}#")

        return decision_variable_dict

    def add_flight_arc_usage_constraint(self): # TODO: check if still valid
        # ... per flight arc
        for flight_arc in self.TSN.flight_arc_lst:
            f = flight_arc.ref

            constraint_l = gp.LinExpr()

            # ... per aircraft type
            for k in self.TSN.data.aircraft_dict.keys():
                constraint_l += self.decision_variable_dict["x"][f][k]

            self.master.addConstr(constraint_l <= 1,
                                 name=f"Flight_arc_usage-{f}")

    def add_conservation_of_aircraft_flow_constraint(self): # TODO: check if still valid
        # ... per node
        for t, timestep in enumerate(self.TSN.network):     # ... per timestep
            for airport_ref, node in timestep.items():      # ... per airport

                # ... per aircraft type
                for k in self.TSN.data.aircraft_dict.keys():
                    constraint_l = gp.LinExpr()

                    # ... per flight arc exiting the node
                    for flight_arc in node.out_flight_arc_lst:
                        f = flight_arc.ref

                        constraint_l -= self.decision_variable_dict["x"][f][k]

                    # ... per ground arc exiting the node
                    for ground_arc in node.out_ground_arc_lst:
                        g = ground_arc.ref

                        constraint_l -= self.decision_variable_dict["y"][g][k]

                    # ... per flight arc entering the node
                    for flight_arc in node.in_flight_arc_lst:
                        f = flight_arc.ref

                        constraint_l += self.decision_variable_dict["x"][f][k]

                    # ... per ground arc entering the node
                    for ground_arc in node.in_ground_arc_lst:
                        g = ground_arc.ref

                        constraint_l += self.decision_variable_dict["y"][g][k]

                    # TODO: Double check h sign
                    if t == 0:
                        h = -self.TSN.data.airport_dict[airport_ref]["aircrafts"][k]

                    elif t == len(self.TSN.network)-1:
                        h = self.TSN.data.airport_dict[airport_ref]["aircrafts"][k]

                    else:
                        h = 0

                    self.master.addConstr(constraint_l == h,
                                         name=f"Conservation_of_aircraft_flow-{t}-{airport_ref}-{k}")

    def add_weight_capacity_constraint(self): # TODO: check with victor
        # ... per flight arc
        for flight_arc in self.TSN.flight_arc_lst:
            f = flight_arc.ref

            constraint_l = gp.LinExpr()
            constraint_r = gp.LinExpr()

            # ... per request
            for r, request in self.TSN.data.request_dict.items():
                # ... per path of request, excluding NS paths intersected with p
                for p, path in self.path_dict["paths containing flight arc"][f][r].items():
                    if path.type == "NS":
                        pass
                    constraint_l += request["weight"] * self.decision_variable_dict["z"][p][r]

            # ... per aircraft
            for k, aircraft in self.TSN.data.aircraft_dict.items():
                constraint_r += aircraft["payload"] * self.decision_variable_dict["x"][f][k]

            self.master.addConstr(constraint_l <= constraint_r,
                                 name=f"Weight capacity--{f}")

    def add_request_paths_constraint(self):
        # ... per request
        for r, request in self.TSN.data.request_dict.items():
            constraint_l = gp.LinExpr()
            # ... per path of request
            for p, path in self.path_dict["request paths"][r].items():
                constraint_l += self.decision_variable_dict["z"][p][r]
            self.master.addConstr(constraint_l == 1,
                                  name=f"Request paths--{r}")

    def add_objective_function(self, display_progress_bars=False):
        # --> Initiating objective function linear expression
        objective_function = gp.LinExpr()

        # ... per aircraft
        for k, aircraft in self.TSN.data.aircraft_dict.items():
            # ... per flight arc
            for flight_arc in self.TSN.flight_arc_lst:
                f = flight_arc.ref
                Ck = self.TSN.data.aircraft_dict[k]["operational_cost"] # MU/km
                Df = self.Df(flight_arc)

                objective_function += Ck*Df*self.decision_variable_dict["x"][f][k] # TODO: check

        # ... per request
        for r, request in self.TSN.data.request_dict.items():
            # ... per path of request exlcuding ns
            for p, path in self.path_dict["request paths"][r].items():
                if path.type == "NS":
                    pass
                else:
                    MCpr = self.MCpr(path,request)
                    objective_function += MCpr*self.decision_variable_dict["z"][p][r]

        # ... per request
        for r, request in self.TSN.data.request_dict.items():
            # ... find Pns
            for p, path in self.path_dict["request paths"][r].items():
                if path.type == "NS":

                    PCr = request["penalty"]  # MU/ton
                    Wr = request["weight"] # ton
                    objective_function += PCr * Wr * self.decision_variable_dict["z"][p][r]

        self.master.setObjective(objective_function, GRB.MINIMIZE)

    def rebuild_master(self):
        # -> Re-initialised model
        self.master = gp.Model("APO_assignment_model_4")

        # -> Creating decision variables
        self.decision_variable_dict = self.generate_decision_variables()

        # -> Add constraints
        self.add_flight_arc_usage_constraint()  # (1)
        self.add_conservation_of_aircraft_flow_constraint()  # (2)
        self.add_weight_capacity_constraint()  # (3)
        self.add_request_paths_constraint()  # (4)
        # self.add_net_aircraft_flow_constraint() #not used

        # -> Add objective function
        self.add_objective_function()

        # -> ?Parse? rebuilt model
        self.master.update()

    def create_initial_paths(self):
        path_dict = {"request paths": {},               # path_dict[request paths][request_id][path_ref] -> path
                     "paths": {},                       # path_dict[paths][path_ref] -> path
                     "paths containing flight arc": {}} # path_dict[paths containing flight arc][f][request_id][path_ref] -> path

        # ... for every request
        for request_id, request in self.TSN.data.request_dict.items():
            path_dict["request paths"][request_id] = {}

            # start_node = self.TSN.network[request["release_step"]][request["airport_O"]]
            # end_node = self.TSN.network[request["due_step"]][request["airport_D"]]

            # -> Find corresponding ns arc in TSN
            for ns_arc in self.TSN.ns_arc_lst:
                # if ns_arc.origin == start_node.ref and ns_arc.destination == end_node.ref:
                if ns_arc.type == "NS":
                    if ns_arc.request_id == request_id:
                        self.path_count += 1

                        new_path = Path(request_id=request_id,
                                        arc_list=[ns_arc],
                                        path_number=self.path_count)

                        path_dict["request paths"][request_id][new_path.ref] = new_path
                        path_dict["paths"][new_path.ref] = new_path
                        # new path does not contain flight arc, only NS
                        break

        # -> Initialize an empty dictionary for each flight_arc - request combination
        for flight_arc in self.TSN.flight_arc_lst:
            f = flight_arc.ref
            path_dict["paths containing flight arc"][f] = {}

            for r, request in self.TSN.data.request_dict.items():
                path_dict["paths containing flight arc"][f][r] = {}

        return path_dict

    def add_path(self, request_id, x, arc_dict):
        solution = []

        for a, v in x.items():
            if v.x != 0:
                solution.append(arc_dict[a])

        self.path_count += 1
        print(f'\r path_count: {self.path_count}',end = '')
        new_path = Path(request_id=request_id,
                        arc_list=solution,
                        path_number=self.path_count)

        # -> add path to self.path_dict
        self.path_dict["request paths"][request_id][new_path.ref] = new_path
        self.path_dict["paths"][new_path.ref] = new_path

        for flight_arc in new_path.flight_arcs:
            f = flight_arc.ref
            self.path_dict["paths containing flight arc"][f][request_id][new_path.ref] = new_path

        # -> collum to master based on path

    # -> Marginal cost per flight arc
    def MCf(self, flight_arc):
        i = self.TSN.data.airport_dict[flight_arc.origin_airport]["index"]
        j = self.TSN.data.airport_dict[flight_arc.destination_airport]["index"]
        n = len(self.TSN.data.airport_dict)
        depart_time = flight_arc.origin_timestep * self.TSN.data.timestep_duration
        h = depart_time % 24
        d = (depart_time - h) / 24 + 1
        # print(f"time = {depart_time}, d = {d}, h = {h}")

        return 0.05 * (i + j) / (2 * n - 1) + 0.15 * np.sin(2 * np.pi * h / 24) ** 2 + 0.005 * d  # MU/(km*ton)

    # -> Total marginal cost per path for a specific request
    def MCpr(self, path, request):
        MCpr = 0

        for flight_arc in path.flight_arcs:
            MCpr += self.MCf(flight_arc) * self.Df(flight_arc) * request["weight"]

        return MCpr

    def Df(self, flight_arc):
        return self.TSN.data.distance_df.loc[flight_arc.origin_airport,flight_arc.destination_airport] # km

    def run(self):
        # -> Run conditional
        new_column_added = True

        while new_column_added:
            # -> Perform model relaxation
            linear_relaxation = self.master.relax()
            linear_relaxation.setParam("OutputFlag", 0)

            # -> Optimise relaxed master model
            linear_relaxation.optimize()

            # -> Obtain dual values for each constraint (based on current master model with latest columns)
            # 4 constrains, only 2 relevant for price model
            # pi_f, pi_r
            pi = {"f": {},
                  "r": {}}

            for c in linear_relaxation.getConstrs():
                if "Request paths" in c.ConstrName:
                    # f"Conservation_of_request_flow-{t}-{airport_ref}-{r}"
                    r = int(c.ConstrName.split('--')[-1])
                    pi["r"][r] = c.Pi

                if "Weight capacity" in c.ConstrName:
                    # f"Weight capacity-{f}"
                    f = c.ConstrName.split('--')[-1]
                    pi["f"][f] = c.Pi

            # -> Created and solve reduced cost and pricing problem to find new columns
            # ... for every request
            for r, request in self.TSN.data.request_dict.items():
                # -> Create secondary model
                RC = gp.Model(str(r))
                RC.setParam("OutputFlag",0)

                # -> add decision variables
                x = {}
                arc_dict = {}

                for arc in self.TSN.arc_lst_no_ns:
                    a = arc.ref
                    arc_dict[a] = arc
                    x[a] = RC.addVar(vtype=GRB.BINARY,
                                     name=f"x-{a}")

                # -> add constraints
                # ... per node
                for t, timestep in enumerate(self.TSN.network):  # ... per timestep
                    for airport_ref, node in timestep.items():  # ... per airport
                        constraint_l = gp.LinExpr()

                        # ... per arc existing the node
                        for arc in node.out_arc_lst:
                            if arc.type != "NS":
                                a = arc.ref
                                constraint_l -= x[a] # TODO: dubble check - and + for delta

                        # ... per arc entering the node
                        for arc in node.in_arc_lst:
                            if arc.type != "NS":
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
                RC.setObjective(objective_function, GRB.MINIMIZE)
                RC.update() # TODO: CHeck if needed?

                # -> optimize RC model
                RC.optimize()

                new_column_added = False

                # -> Check if optimal solution is negative, add new column if true
                if RC.Status != 3: # infeasible
                    if RC.ObjVal < 0:
                        self.add_path(r, x, arc_dict)
                        new_column_added = True

            self.rebuild_master()


if __name__ == '__main__':
    CG = CG()
