import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt
import sys
from copy import deepcopy

from Haversine_function import haversine


class Network:
    def __init__(self):
        """
        Data structure:"

        - self.airports_lst contains all the airports with their respective properties
        (they are stored as dictionaries in a list to make iterating through them easier)

            self.airports_lst = [{["ref"], ["lat"], ["lon"], ["runway"], ["runway compatibility lst"]}]

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

        - self.distances_df is a dataframe containing the distance flown between airports
        - self.traffic is a dataframe containing the amount of traffic for each route

        All dataframes are indexed using the airports ICAO codes for convenience
        (which can be obtained using the key "ref" on objects in the self.airports_lst list)
        """

        # -> Set Network hub
        self.hub = "Malmö"
        self.hub_ref = "ESMS"

        # -> Set fleet properties
        self.max_continuous_operation = 10

        # -> Setup aircraft dict
        self.ac_dict = self.create_aircraft_dict()

        # -> Import network nodes
        self.airports_lst = self.import_network_airports()

        # -> Solve for network legs properties
        self.distances_df = self.solve_edges_properties()

        # -> Solve for possible routes
        self.routes_dict = self.determine_routes_properties()

        # -> Import network traffic
        self.traffic_df = self.import_network_traffic()

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

    def import_network_airports(self):
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
        airports_lst = []

        # -> Solving for runway viability for each aircraft type
        for index, row in df.iterrows():
            runway_compatibility_lst = []

            for aircraft_type, aircraft in self.ac_dict.items():
                if aircraft["runway req"] <= row["Runway (m)"]:
                    runway_compatibility_lst.append([aircraft_type, 1])

                else:
                    runway_compatibility_lst.append([aircraft_type, 0])

            airports_lst.append({"ref": row["ICAO Code"],
                                 "lat": row["Latitude (deg)"],
                                 "lon": row["Longitude (deg)"],
                                 "runway": row["Runway (m)"],
                                 "runway compatibility lst": runway_compatibility_lst})

        return airports_lst

    def solve_edges_properties(self):
        # -> Create network edge dataframe
        edges_df = pd.DataFrame(0, index=np.arange(len(self.airports_lst)), columns=np.arange(len(self.airports_lst)))

        edges_df.columns = list(node["ref"] for node in self.airports_lst)
        edges_df = edges_df.reindex(index=list(node["ref"] for node in self.airports_lst), fill_value=0)

        # -> Create network legs properties per aircraft
        for aircraft in self.ac_dict.values():
            aircraft["legs"] = {"viability": deepcopy(edges_df),
                                "total operating cost": deepcopy(edges_df),
                                "duration": deepcopy(edges_df),
                                "yield per RPK": deepcopy(edges_df)}

        # -> Create network legs len df
        legs_len_df = deepcopy(edges_df)

        # -> Solving for legs values
        for airport_i in self.airports_lst:
            # -> Solving for distance between nodes using haversine equation
            for airport_j in self.airports_lst:
                if airport_j == airport_i:
                    continue
                else:
                    leg_len = \
                        haversine((airport_i["lat"], airport_i["lon"]), (airport_j["lat"], airport_j["lon"]))[1]

                    legs_len_df.loc[airport_i["ref"], airport_j["ref"]] = leg_len

                    # -> Solving for leg property for each aircraft type
                    for aircraft in self.ac_dict.values():
                        if aircraft["max range"] >= leg_len:
                            # -> Mark leg as viable
                            aircraft["legs"]["viability"].loc[airport_i["ref"], airport_j["ref"]] = 1

                            # -> Solve for leg duration
                            aircraft["legs"]["duration"].loc[airport_i["ref"], airport_j["ref"]] = \
                                leg_len / aircraft["speed"]

                            # -> Solve for leg total cost
                            fixed_operating_cost = aircraft["fixed operating cost"]

                            time_cost = aircraft["time cost parameter"] * (leg_len/aircraft["speed"])

                            fuel_cost = (aircraft["fuel cost parameter"]*1.42)/1.5 * leg_len

                            energy_cost = 0.07 * aircraft["batteries energy"] * leg_len/aircraft["max range"]

                            if airport_i == self.hub_ref or airport_j == self.hub_ref:
                                # fixed_operating_cost + time_cost + fuel_cost are 30% cheaper if departing/arrival airport is hub
                                aircraft["legs"]["total operating cost"].loc[airport_i["ref"], airport_j["ref"]] = \
                                    (fixed_operating_cost + time_cost + fuel_cost) * 0.7 + energy_cost

                            else:
                                aircraft["legs"]["total operating cost"].loc[airport_i["ref"], airport_j["ref"]] = \
                                    (fixed_operating_cost + time_cost + fuel_cost) + energy_cost

                            # Solve for leg yield per passenger
                            aircraft["legs"]["yield per RPK"].loc[airport_i["ref"], airport_j["ref"]] = \
                                5.9*leg_len**(-0.76) + 0.043

                        else:
                            pass

        return legs_len_df

    def determine_routes_properties(self):
        routes_dict = {}

        # -> Set single stop routes
        for airport_1 in self.airports_lst:
            if airport_1["ref"] == self.hub_ref:
                continue
            else:
                path = [self.hub_ref, airport_1["ref"], self.hub_ref]
                routes_dict["-".join(path)] = {"path": path,
                                               "length": 2*self.distances_df.loc[self.hub_ref, airport_1["ref"]]}

                # -> Set two stop routes
                for airport_2 in self.airports_lst:
                    if airport_2["ref"] == self.hub_ref or airport_2["ref"] == airport_1["ref"]:
                        continue
                    else:
                        path = [self.hub_ref, airport_1["ref"], airport_2["ref"], self.hub_ref]
                        routes_dict["-".join(path)] = {"path": path,
                                                       "length": self.distances_df.loc[self.hub_ref, airport_1["ref"]]
                                                                 + self.distances_df.loc[airport_1["ref"], airport_2["ref"]]
                                                                 + self.distances_df.loc[airport_2["ref"], self.hub_ref]}

        # -> Solve for route properties per aircraft
        for aircraft in self.ac_dict.values():
            aircraft["routes"] = {}

            for route_ref, route in routes_dict.items():
                aircraft["routes"][route_ref] = {"viability": 0,
                                                 "total operating cost": 0,
                                                 "duration": 0,
                                                 "yield per RPK": 0}

                # -> Checking route viability for aircraft model
                if aircraft["max range"] >= route["length"]:
                    # -> Mark route as viable
                    aircraft["routes"][route_ref]["viability"] = 1

                    for i in range(len(route["path"])-1):
                        # -> Solve for route duration
                        aircraft["routes"][route_ref]["duration"] += \
                            aircraft["legs"]["duration"].loc[route["path"][i], route["path"][i+1]]

                        # -> Solve for route total cost
                        aircraft["routes"][route_ref]["total operating cost"] += \
                            aircraft["legs"]["total operating cost"].loc[route["path"][i], route["path"][i+1]]

                        # Solve for route yield per passenger
                        aircraft["routes"][route_ref]["yield per RPK"] += \
                            aircraft["legs"]["yield per RPK"].loc[route["path"][i], route["path"][i+1]]

        return routes_dict

    @staticmethod
    def import_network_traffic():
        df = pd.read_csv("Demand_per_week.csv", header=[0])
        df = df.set_index("Unnamed: 0")

        return df


if __name__ == "__main__":
    net = Network()

    print(net.ac_dict)
    print(net.airports_lst)
    print(net.distances_df)
    print(net.routes_dict)
    print(net.traffic_df)

    print("\n")

    print("Network nodes count:", len(net.airports_lst))
    print("Aircraft type count:", len(net.ac_dict))
    print("Possible routes:", len(net.routes_dict))
