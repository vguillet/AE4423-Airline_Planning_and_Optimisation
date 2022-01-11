from Collum_generation import CG
from matplotlib import pyplot as plt

class Results():
    def __init__(self,show=False,save=True,max_time=3600):
        self.show = show
        self.save = save
        self.model = CG()
        # self.print_stats()
        self.plot_graph()

    def timestep2day(self,timestep):
        tmp = []
        for t in timestep:
            time = t * 4
            h = int(time % 24)
            d = int((time - h) / 24 + 1)
            if h != 0:
                tmp.append(f"{h}h")
            else:
                tmp.append(f"{h}h\nDay {d}")
        return tmp

    def plot_graph(self):
        c_code = {"AC_1": (1, 0, 0),
                  "AC_2": (0, 0, 1)}
        results = self.model.decision_variable_dict

        plt.figure(figsize=[11,4])
        plt.xticks(range(25),self.timestep2day(range(25)))
        idx2ref = [""] * 6
        for airport_ref, airport in self.model.TSN.data.airport_dict.items():
            idx2ref[airport["index"] - 1] = airport_ref
        plt.yticks(range(7)[1:], idx2ref)

        request_plot_dict = {}
        # for z[p][r]
        for p, zp in results["z"].items():
            for r, zpr in zp.items():
                if type(zpr) != int:
                    path = self.model.path_dict["request paths"][r][p]
                    for arc in path.arcs:
                        a = arc.ref
                        if arc.type != "NS":
                            if self.model.TSN.data.request_dict[r]["airport_D"] != arc.origin_airport:
                                weight = self.model.TSN.data.request_dict[r]["weight"] * zpr.X
                            else:
                                weight = 0
                            try:
                                request_plot_dict[a] += weight
                            except:
                                request_plot_dict[a] = weight
                            t = [arc.origin_timestep,arc.destination_timestep]
                            n = [self.model.TSN.data.airport_dict[arc.origin_airport]["index"] , self.model.TSN.data.airport_dict[arc.destination_airport]["index"]]
                            plt.plot(t, n, linewidth=request_plot_dict[a] / 10, color=(0.3, 0.3, 0.3))
                        else:
                            plt.plot(arc.origin_timestep, self.model.TSN.data.airport_dict[arc.origin_airport]["index"], 'ro')


        for r in self.model.master.getVars():
            if r.X != 0:
                if r.varName[0] in ["x", "y"]:
                    # print(r.varName,r.X)
                    arc_name = r.varName[16:].split("->")
                    t = [0, 0]
                    n = [0, 0]
                    plane = arc_name[1].split("-")[-1]
                    for i in range(2):
                        t[i] = int(arc_name[i].split("-")[0])
                        n[i] = int(self.model.TSN.data.airport_dict[arc_name[i].split("-")[1]]["index"])
                    plt.plot(t, n, color=c_code[plane], linestyle=":")

        if self.save:
            file_name = "Results_model_4"
            plt.savefig(f"{file_name}.png")
            print(f"saved figure to '{file_name}.png'")
        if self.show:
            plt.show()

    def print_stats(self):
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

        results = self.model.model.getVars()

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

            if decision_variable.varName[0] == "z" and "NS" in decision_variable.varName and int(
                    decision_variable.x) == 1:
                NS_arc_used += 1

                package_id = int(decision_variable.varName.split("#")[-2])
                if package_id not in packages_not_handled:
                    packages_not_handled.append(package_id)

                    request = self.model.TSN.data.request_dict[package_id]

                    packages_not_handled_penalty += request["penalty"] * request["weight"]

        print(f"- Nb. arcs used: {total_arc_used}")
        print(f"   > Flight arcs: {f_arc_used}")
        print(f"   > Ground arcs: {g_arc_used}")

        print(f"- Nb. NS arcs used: {NS_arc_used}")
        print(f"- Nb. packages handled: {len(packages_handled)}")
        print(f"- Nb. packages not handled: {len(packages_not_handled)}")
        print(f"- Total packages not handled penalty: {packages_not_handled_penalty}")

if __name__ == '__main__':
    Results(show=False,save=True,max_time=3600)
