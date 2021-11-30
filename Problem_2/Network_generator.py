import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt
import sys
from copy import deepcopy

from Haversine_function import haversine
from RPK_function import eur_yield


class Network:
    def __init__(self):
        """
        Data structure:"

        - self.nodes_lst contains all the airports with their respective properties
        (they are stored as dictionaries in a list to make iterating through them easier)

            self.nodes_lst = [{["ref"], ["lat"], ["lon"], ["runway"], ["runway compatibility lst"]}]

            Note: "runway compatibility lst" is a list of lists, with item 0 : aircraft ref
                                                                      item 1 : compatible (binary)

        - self.ac_dict contains all the aircraft types and their respective properties.
        It is a double nested dictionary with aircraft type are the keys to l1, and properties as l2 keys.

            self.ac_dict = {[aircraft type]: {["speed"],
                                              ["seats"],
                                              ["avg TAT"],
                                              ["extra charging time"],
                                              ["max range"],
                                              ["runway req"],

                                              ["weekly lease cost"],
                                              ["fixed operating cost"],
                                              ["time cost parameter"],
                                              ["fuel cost parameter"],
                                              ["batteries energy"],

                                              ["viability"],
                                              ["total operating cost"],
                                              ["yield per RPK"]}}

        - self.edge_df is a dataframe containing the length of each route
        - self.traffic is a dataframe containing the amount of traffic for each route

        All dataframes are indexed using the airports ICAO codes for convenience
        (which can be obtained using the key "ref" on objects in the self.nodes_lst list)
        """
        # -> Setup aircraft dict
        self.ac_dict = self.create_aircraft_dict()

        # -> Import network nodes
        self.nodes_lst = self.import_network_nodes()

        # -> Solve for network edge properties
        self.edges_df = self.solve_network_edges()

        # -> Import network traffic
        self.traffic_df = self.import_network_traffic()

        print(self.ac_dict)
        print(self.nodes_lst)
        print(self.edges_df)
        print(self.traffic_df)

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

        # -> Solving for runway viability for each aircraft type
        for index, row in df.iterrows():
            runway_compatibility_lst = []

            for aircraft_type, aircraft in self.ac_dict.items():
                if aircraft["runway req"] <= row["Runway (m)"]:
                    runway_compatibility_lst.append([aircraft_type, 1])

                else:
                    runway_compatibility_lst.append([aircraft_type, 0])

            network_nodes.append({"ref": row["ICAO Code"],
                                  "lat": row["Latitude (deg)"],
                                  "lon": row["Longitude (deg)"],
                                  "runway": row["Runway (m)"],
                                  "runway compatibility lst": runway_compatibility_lst})

        return network_nodes

    @staticmethod
    def import_network_traffic():
        df = pd.read_csv("Demand_per_week.csv", header=[0])
        df = df.set_index("Unnamed: 0")

        return df

    def solve_network_edges(self):
        # -> Create network edge dataframe
        edges = pd.DataFrame(0, index=np.arange(len(self.nodes_lst)), columns=np.arange(len(self.nodes_lst)))

        edges.columns = list(node["ref"] for node in self.nodes_lst)
        edges = edges.reindex(index=list(node["ref"] for node in self.nodes_lst), fill_value=0)

        # -> Create network edge properties per aircraft
        for aircraft_type in self.ac_dict:
            self.ac_dict[aircraft_type]["viability"] = deepcopy(edges)
            # self.ac_dict[aircraft_type]["duration"] = deepcopy(edges)
            self.ac_dict[aircraft_type]["total operating cost"] = deepcopy(edges)
            self.ac_dict[aircraft_type]["yield per RPK"] = deepcopy(edges)

        # -> Create network edge len df
        edges_len = deepcopy(edges)

        # -> Solving for edge values
        for node in self.nodes_lst:
            # -> Solving for distance between nodes using haversine equation
            for other_node in self.nodes_lst:
                if other_node == node:
                    continue
                else:
                    edge_len = \
                        haversine((node["lat"], node["lon"]), (other_node["lat"], other_node["lon"]))[1]

                    edges_len.loc[node["ref"], other_node["ref"]] = edge_len

                    # -> Solving for edge property for each aircraft type
                    for aircraft_type, aircraft in self.ac_dict.items():
                        if aircraft["max range"] >= edge_len:
                            # -> Mark edge as viable
                            aircraft["viability"].loc[node["ref"], other_node["ref"]] = 1

                            # -> Solve for trip duration
                            # aircraft["duration"].loc[node["ref"], other_node["ref"]] = edge_len / aircraft["speed"]

                            # -> Solve for edge total cost
                            time_cost = aircraft["time cost parameter"] * (edge_len/aircraft["speed"])

                            fuel_cost = (aircraft["fuel cost parameter"]*1.42)/1.5 * edge_len

                            energy_cost = 0.07 * aircraft["batteries energy"] * edge_len/aircraft["max range"]

                            aircraft["total operating cost"].loc[node["ref"], other_node["ref"]] = \
                                aircraft["fixed operating cost"] + time_cost + fuel_cost + energy_cost

                            # Solve for edge yield per passenger
                            aircraft["yield per RPK"].loc[node["ref"], other_node["ref"]] = \
                                5.9*edge_len**(-0.76) + 0.043

                        else:
                            pass

        return edges


if __name__ == "__main__":
    Network()
