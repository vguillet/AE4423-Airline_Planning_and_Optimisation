import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt
from Haversine_function import haversine


class Network:
    def __init__(self):
        # -> Setup aircraft dict
        self.ac_dict = self.create_aircraft_dict()

        # -> Import network nodes
        self.network_nodes_lst = self.import_network_nodes()
        print(self.network_nodes_lst)

        self.network_edges_dict = self.solve_network_edges()
        print(self.network_edges_dict)

    @staticmethod
    def create_aircraft_dict():
        return {"AC 1": {"speed": 550,
                         "seats": 45,
                         "avg TAT": 25,
                         "extra charging time": 0,
                         "max range": 1500,
                         "runway req": 1400,

                         "weekly lease cost": 15000,
                         "fixed operating cost": 300,
                         "time cost parameter": 750,
                         "fuel cost parameter": 1,
                         "batteries energy": 0},

                "AC 2": {"speed": 820,
                         "seats": 70,
                         "avg TAT": 35,
                         "extra charging time": 0,
                         "max range": 3300,
                         "runway req": 1600,

                         "weekly lease cost": 34000,
                         "fixed operating cost": 600,
                         "time cost parameter": 775,
                         "fuel cost parameter": 2,
                         "batteries energy": 0},

                "AC 3": {"speed": 850,
                         "seats": 150,
                         "avg TAT": 45,
                         "extra charging time": 0,
                         "max range": 6300,
                         "runway req": 1800,

                         "weekly lease cost": 80000,
                         "fixed operating cost": 1250,
                         "time cost parameter": 1400,
                         "fuel cost parameter": 3.75,
                         "batteries energy": 0},

                "AC 4": {"speed": 350,
                         "seats": 20,
                         "avg TAT": 20,
                         "extra charging time": 20,
                         "max range": 400,
                         "runway req": 750,

                         "weekly lease cost": 12000,
                         "fixed operating cost": 90,
                         "time cost parameter": 750,
                         "fuel cost parameter": 0,
                         "batteries energy": 2130},

                "AC 5": {"speed": 480,
                         "seats": 48,
                         "avg TAT": 25,
                         "extra charging time": 45,
                         "max range": 1000,
                         "runway req": 950,

                         "weekly lease cost": 22000,
                         "fixed operating cost": 120,
                         "time cost parameter": 750,
                         "fuel cost parameter": 0,
                         "batteries energy": 8216}
                }

    def import_network_nodes(self):
        df = pd.read_csv("Destination_coordinates.csv")

        # -> Reshape data
        df = df.transpose()
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)

        # -> Remove unnecessary data
        df = df.drop("Population", 1)

        # -> Adjust type
        df["Latitude (deg)"] = pd.to_numeric(df["Latitude (deg)"])
        df["Longitude (deg)"] = pd.to_numeric(df["Longitude (deg)"])
        df["Runway (m)"] = pd.to_numeric(df["Runway (m)"])

        # -> Create a node per destination
        network_nodes = []

        for index, row in df.iterrows():
            # -> Solving for runway viability for each aircraft type
            runway_compatibility_lst = []

            for aircraft_type, value in self.ac_dict.items():
                if value["runway req"] <= row["Runway (m)"]:
                    runway_compatibility_lst.append(1)

                else:
                    runway_compatibility_lst.append(0)

            network_nodes.append({"ref": row["ICAO Code"],
                                  "lat": row["Latitude (deg)"],
                                  "lon": row["Longitude (deg)"],
                                  "runway": row["Runway (m)"],
                                  "runway compatibility lst": runway_compatibility_lst})

        return network_nodes

    def solve_network_edges(self):
        network_edges_dict = {"len": np.zeros((len(self.network_nodes_lst), len(self.network_nodes_lst))),
                              "AC 1": np.zeros((len(self.network_nodes_lst), len(self.network_nodes_lst))),
                              "AC 2": np.zeros((len(self.network_nodes_lst), len(self.network_nodes_lst))),
                              "AC 3": np.zeros((len(self.network_nodes_lst), len(self.network_nodes_lst))),
                              "AC 4": np.zeros((len(self.network_nodes_lst), len(self.network_nodes_lst))),
                              "AC 5": np.zeros((len(self.network_nodes_lst), len(self.network_nodes_lst)))}

        # -> Solving for edge values
        for node_id in range(len(self.network_nodes_lst)):

            # -> Solving for distance between nodes using haversine equation
            for other_node in range(len(self.network_nodes_lst)):
                if other_node == node_id:
                    continue
                else:
                    edge_len = \
                        haversine((self.network_nodes_lst[node_id]["lat"],
                                   self.network_nodes_lst[node_id]["lon"]),
                                  (self.network_nodes_lst[other_node]["lat"],
                                   self.network_nodes_lst[other_node]["lon"])
                                  )[1]

                    network_edges_dict["len"][node_id, other_node] = edge_len

                    # -> Solving for air path viability for each aircraft type
                    for aircraft_type, value in self.ac_dict.items():
                        if value["max range"] >= edge_len:
                            network_edges_dict[aircraft_type][node_id, other_node] = 1

                        else:
                            pass

        return network_edges_dict


if __name__ == "__main__":
    Network()
