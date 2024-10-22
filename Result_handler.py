from Model_generator_3 import Model_3
from matplotlib import pyplot as plt
import time

class Results():
    def __init__(self,show=False,save=True,max_time=3600):
        self.show = show
        self.save = save
        start_time = time.time()
        self.model = Model_3(max_time=max_time) # 2 hours
        self.run_time = time.time()-start_time
        print(f"\nruntime: {round(self.run_time,3)} seconds")
        self.print_stats()
        self.plot_graph()

    def timestep2day(self,timestep):
        '''converts the time step into a string with hour and day number for plotting'''
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
        '''plots and saves the graph that represents the model'''
        model = self.model
        c_code = {"AC_1": (1, 0, 0),
                  "AC_2": (0, 0, 1)}
        results = model.model.getVars()

        plt.figure(figsize=[11,4])
        plt.xticks(range(25),self.timestep2day(range(25)))
        idx2ref = [""] * 6
        for airport_ref, airport in model.TSN.data.airport_dict.items():
            idx2ref[airport["index"] - 1] = airport_ref
        plt.yticks(range(7)[1:], idx2ref)

        z_dict = {}
        for r in results:
            if r.X != 0:
                if r.varName[0] == "z":
                    if r.varName[7:9] != "NS":
                        # print(r.varName[16:],r.X)
                        varName_list = r.varName[16:].replace(">", '').split('-')
                        arc_name = varName_list[0] + '-' + varName_list[1] + '->' + varName_list[2] + '-' + varName_list[3]
                        ID = int(varName_list[-1].replace("#", ''))
                        # print(arc_name, 'ID:',  ID)
                        if varName_list[1] == model.TSN.data.request_dict[ID]["airport_D"]:
                            pass
                        else:
                            try:
                                z_dict[arc_name] += model.TSN.data.request_dict[ID]["weight"]
                            except:
                                z_dict[arc_name] = model.TSN.data.request_dict[ID]["weight"]
                    else:
                        tmp = r.varName.split(' - ')[1]
                        varName_list = tmp.replace(">", '').split('-')
                        # print(tmp)
                        # print(varName_list)
                        # arc_name = varName_list[0] + '-' + varName_list[1] + '->' + varName_list[2] + '-' + varName_list[3]
                        # ID = int(varName_list[-1].replace("#", ''))
                        # print(varName_list)
                        # plt.plot(varName_list[0],model.TSN.data.airport_dict[varName_list[1]]["index"], color=(0, 0.8, 0), marker='o',markersize=4)
                        plt.plot([varName_list[0], varName_list[2]],
                                 [model.TSN.data.airport_dict[varName_list[1]]["index"],
                                  model.TSN.data.airport_dict[varName_list[3]]["index"]]
                                 , color=(0, 0.8, 0), marker='o', markersize=3, linestyle='dashed', linewidth=1, zorder=1)

        for arc_name, weight in z_dict.items():
            arc_name = arc_name.split("->")
            t = [0, 0]
            n = [0, 0]
            for i in range(2):
                t[i] = int(arc_name[i].split("-")[0])
                n[i] = int(model.TSN.data.airport_dict[arc_name[i].split("-")[1]]["index"])
            plt.plot(t, n, linewidth=weight/10, color=(0.3, 0.3, 0.3), zorder=2)

        for r in results:
            if r.X != 0:
                if r.varName[0] in ["x", "y"]:
                    # print(r.varName,r.X)
                    arc_name = r.varName[16:].split("->")
                    t = [0, 0]
                    n = [0, 0]
                    plane = arc_name[1].split("-")[-1]
                    for i in range(2):
                        t[i] = int(arc_name[i].split("-")[0])
                        n[i] = int(model.TSN.data.airport_dict[arc_name[i].split("-")[1]]["index"])
                    plt.plot(t, n, color=c_code[plane], linestyle=":", zorder = 3)
        if self.save:
            file_name = "Results_model_3"
            plt.savefig(f"{file_name}.png")
            print(f"saved figure to '{file_name}.png'")
        if self.show:
            plt.show()

    def print_stats(self):
        '''prints the stats of the model'''
        # =========================================================== Generate data
        # -> Arc used (non-NS)
        total_arc_used = 0
        f_arc_used = 0
        t_f = 0
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
                    name_list = decision_variable.varName.split('->')
                    # print(name_list)
                    t_f += self.model.TSN.data.duration_df.loc[name_list[0][-3:], name_list[1].split('-')[1]]
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
        print(f"   > Airtime percentage: {round(t_f/(t_f+g_arc_used*4)*100)}%")

        print(f"- Nb. NS arcs used: {NS_arc_used}")
        print(f"- Nb. packages handled: {len(packages_handled)}")
        print(f"- Nb. packages not handled: {len(packages_not_handled)}")
        print(f"- Total packages not handled penalty: {packages_not_handled_penalty}")

if __name__ == '__main__':
    Results(show=False,save=True,max_time=3600)
