
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


# Own modules
from TSN import Time_space_network
__version__ = '1.1.1'

################################################################################################################


class Model_3:
    def __init__(self,max_time = 3600):
        # -> Generate data
        self.TSN = Time_space_network()

        # -> Creating model
        self.model = gp.Model("APO_assignment_model_3")

        # -> Adjusting settings
        display_progress_bars = True

        self.model.Params.OutputFlag = 1    # Disabling the gurobi console output, set to 1 to enable

        self.model.setParam("TimeLimit",max_time)

        # -> Creating decision variables
        self.decision_variable_dict = self.generate_decision_variables()

        # -> Add constraints
        self.add_flight_arc_usage_constraint(display_progress_bars)
        self.add_conservation_of_aircraft_flow_constraint(display_progress_bars)
        self.add_conservation_of_request_flow_constraint(display_progress_bars)
        self.add_weight_capacity_constraint(display_progress_bars)
        self.add_net_aircraft_flow_constraint(display_progress_bars) #not used

        # -> Add objective function
        self.add_objective_function(display_progress_bars)

        print("\nModel compiled!!!")

        # -> Write model
        self.model.write("Model_3.lp")
        self.model.printStats()
        self.model.optimize()

        print("\nModel optimized!!!")

    def generate_decision_variables(self):
        decision_variable_dict = {"x": {},      # FLight arc decision variables
                                  "y": {},      # Ground arc decision variables
                                  "z": {}}      # All arc-request decision variables

        # -> Adding flight arc decision variables - x_f_k
        for flight_arc in self.TSN.flight_arc_lst:
            f = flight_arc.ref
            decision_variable_dict["x"][f] = {}

            for k, aircraft in self.TSN.data.aircraft_dict.items():
                decision_variable_dict["x"][f][k] = \
                    self.model.addVar(vtype=GRB.BINARY,
                                      name=f"x-{f}-{k}")

        # -> Adding ground arc decision variables - y_g_k
        for ground_arc in self.TSN.ground_arc_lst:
            g = ground_arc.ref
            decision_variable_dict["y"][g] = {}

            for k, aircraft in self.TSN.data.aircraft_dict.items():
                decision_variable_dict["y"][g][k] = \
                    self.model.addVar(vtype=GRB.INTEGER,
                                      name=f"y-{g}-{k}")

        # -> Adding arc-request decision variables - z_a_r
        for arc in self.TSN.arc_lst:
            a = arc.ref
            decision_variable_dict["z"][a] = {}

            for r, request in self.TSN.data.request_dict.items(): # TODO: these if statementes are no where mentioned in the assignment but they should be here right?
                decision_variable_dict["z"][a][r] = 0
                if arc.type == "NS":
                    if arc.request_id != r:
                        continue
                decision_variable_dict["z"][a][r] = \
                    self.model.addVar(vtype=GRB.BINARY,
                                      name=f"z-{a}-#{r}#")

        return decision_variable_dict

    def add_flight_arc_usage_constraint(self, display_progress_bars=False):

        # ... per flight arc
        for flight_arc in self.TSN.flight_arc_lst:
            f = flight_arc.ref

            constraint_l = gp.LinExpr()

            # ... per aircraft type
            for k in self.TSN.data.aircraft_dict.keys():
                constraint_l += self.decision_variable_dict["x"][f][k]

            self.model.addConstr(constraint_l <= 1,
                                 name=f"Flight_arc_usage-{f}")

    def add_conservation_of_aircraft_flow_constraint(self, display_progress_bars=False):
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

                    self.model.addConstr(constraint_l == h,
                                         name=f"Conservation_of_aircraft_flow-{t}-{airport_ref}-{k}")

    def add_conservation_of_request_flow_constraint(self, display_progress_bars=False):
        # ... per node
        for t, timestep in enumerate(self.TSN.network):     # ... per timestep
            for airport_ref, node in timestep.items():      # ... per airport

                # ... per request
                for r, request in self.TSN.data.request_dict.items():
                    constraint_l = gp.LinExpr()

                    # ... per arc existing the node
                    for arc in node.out_arc_lst:
                        a = arc.ref

                        constraint_l -= self.decision_variable_dict["z"][a][r]

                    # ... per arc entering the node
                    for arc in node.in_arc_lst:
                        a = arc.ref

                        constraint_l += self.decision_variable_dict["z"][a][r]

                    # TODO: Double check v
                    self.model.addConstr(constraint_l == node.v[r],
                                         name=f"Conservation_of_request_flow-{t}-{airport_ref}-{r}")

    def add_weight_capacity_constraint(self, display_progress_bars=False):
        # ... per flight arc
        for flight_arc in self.TSN.flight_arc_lst:
            f = flight_arc.ref

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
        # TODO/ Finish constraint / decide whether keep or not
        pass

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

    def Df(self,flight_arc):
        return self.TSN.data.distance_df.loc[flight_arc.origin_airport,flight_arc.destination_airport] # km

    def add_objective_function(self, display_progress_bars=False):
        # --> Initiating objective function linear expression
        objective_function = gp.LinExpr()

        # ... per aircraft
        for k, aircraft in self.TSN.data.aircraft_dict.items():
            # ... per flight arc
            for flight_arc in self.TSN.flight_arc_lst:
                f = flight_arc.ref
                Cfk = self.TSN.data.aircraft_dict[k]["operational_cost"] # MU/km
                Df = self.Df(flight_arc)

                objective_function += Cfk*Df*self.decision_variable_dict["x"][f][k] # TODO: check

        # ... per flight arc
        for flight_arc in self.TSN.flight_arc_lst:
            f = flight_arc.ref
            # ... per request
            for r, request in self.TSN.data.request_dict.items():
                MCf = self.MCf(flight_arc) # MU/(km*ton)
                Df = self.Df(flight_arc)
                Wr = request["weight"] #ton

                objective_function += MCf*Df*Wr*self.decision_variable_dict["z"][f][r]

        # ... per request
        for r, request in self.TSN.data.request_dict.items():
            origin = f"{request['release_step']}-{request['airport_O']}"
            destination =  f"{request['due_step']}-{request['airport_D']}"
            s = f"Arc: NS (id:{r}) - {origin}->{destination}" # TODO: not dynamic if changed in TNS arc object fix here
            PCr = request["penalty"] # MU/ton
            Wr = request["weight"] #ton

            objective_function += PCr*Wr*self.decision_variable_dict["z"][s][r]

        self.model.setObjective(objective_function, GRB.MINIMIZE)


if __name__ == "__main__":
    model = Model_3(max_time=1800)

    model = Model_3()

    print("\nModel compiled!!!")




    c_code = {"AC_1":(1,0,0),
              "AC_2":(0,0,1)}
    results = model.model.getVars()
    # plt.figure()
    # plt.xticks(range(26))
    # idx2ref = [""]*6
    # for airport_ref, airport in model.TSN.data.airport_dict.items():
    #     idx2ref[airport["index"]-1] = airport_ref
    # plt.yticks(range(7)[1:],idx2ref)


    plt.figure()
    plt.xticks(range(26))
    idx2ref = [""]*6
    for airport_ref, airport in model.TSN.data.airport_dict.items():
        idx2ref[airport["index"]-1] = airport_ref
    plt.yticks(range(7)[1:],idx2ref)
    z_dict = {}
    for r in results:
        if r.X != 0:
            if r.varName[0] == "z" and r.varName[7:9] != "NS":
                print(r.varName[16:],r.X)
                varName_list = r.varName[16:].replace(">",'').split('-')
                arc_name = varName_list[0] + '-' + varName_list[1] + '->' + varName_list[2] + '-' + varName_list[3]
                ID = int(varName_list[-1].replace("#",''))
                print(arc_name, 'ID:',  ID)
                try:
                    z_dict[arc_name] += model.TSN.data.request_dict[ID]["weight"]
                except:
                    z_dict[arc_name] = model.TSN.data.request_dict[ID]["weight"]
    for arc_name, weight in z_dict.items():
        arc_name = arc_name.split("->")
        t = [0, 0]
        n = [0, 0]
        for i in range(2):
            t[i] = int(arc_name[i].split("-")[0])
            n[i] = int(model.TSN.data.airport_dict[arc_name[i].split("-")[1]]["index"])
        plt.plot(t, n, linewidth=weight/15, color=(0, 0, 0))

    for r in results:
        if r.X != 0:
            if r.varName[0] in ["x","y"]:
                print(r.varName,r.X)
                arc_name = r.varName[16:].split("->")
                t = [0,0]
                n = [0,0]
                plane = arc_name[1].split("-")[-1]
                for i in range(2):
                    t[i] = int(arc_name[i].split("-")[0])
                    n[i] = int(model.TSN.data.airport_dict[arc_name[i].split("-")[1]]["index"])
                plt.plot(t, n, color=c_code[plane], linestyle=":")

    # =========================================================== Generate data
    # -> Arc used (non-NS)
    total_arc_used = 0
    f_arc_used = 0
    g_arc_used = 0

    # -> NS arcs used
    NS_arc_used = 0
    # -> Packages handled
    packages_handled = []
    packages_not_handled = []
    packages_not_handled_penalty = 0

    results = model.model.getVars()

    for decision_variable in results:
        if decision_variable.varName[0] in ["x", "y"] and int(decision_variable.x) == 1:
            total_arc_used += 1

            if decision_variable.varName[0] == "x":
                f_arc_used += 1
            else:
                g_arc_used += 1

        if decision_variable.varName[0] == "z" and "NS" not in decision_variable.varName:
            # print(decision_variable.varName, decision_variable.X)
            package_id = int(decision_variable.varName.split("#")[-2])

            if package_id not in packages_handled and int(decision_variable.x) == 1:
                packages_handled.append(package_id)

        if decision_variable.varName[0] == "z" and "NS" in decision_variable.varName and int(decision_variable.x) == 1:
            NS_arc_used += 1

            package_id = int(decision_variable.varName.split("#")[-2])
            if package_id not in packages_not_handled:
                packages_not_handled.append(package_id)

                request = model.TSN.data.request_dict[package_id]

                packages_not_handled_penalty += request["penalty"] * request["weight"]

    print(f"- Nb. arcs used: {total_arc_used}")
    print(f"   > Flight arcs: {f_arc_used}")
    print(f"   > Ground arcs: {g_arc_used}")

    print(f"- Nb. NS arcs used: {NS_arc_used}")
    print(f"- Nb. packages handled: {len(packages_handled)}")
    print(f"- Nb. packages not handled: {len(packages_not_handled)}")
    print(f"- Total packages not handled penalty: {packages_not_handled_penalty}")

    plt.show()
