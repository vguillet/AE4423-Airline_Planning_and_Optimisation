import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt
import sys
from copy import deepcopy

from Haversine_function import haversine


class Network:
    def __init__(self, question=0):
        """
        Data structure:"

        - self.airports_dict contains all the airports with their respective properties
            self.airports_dict = [airport_ref]: {"lat",
                                                 "lon",
                                                 "runway",
                                                 "runway compatibility": {[ac]: binary}
                                                 }

            Note: "runway compatibility lst" is a list of lists, with item 0 : aircraft ref
                                                                      item 1 : compatible (binary)

        - self.ac_dict contains all the aircraft types and their respective properties.
        It is a double nested dictionary with aircraft type are the keys to l1, and properties as l2 keys.

            self.ac_dict = {[aircraft_type]: {"speed": int,
                                              "seats": int,
                                              "avg TAT": int,
                                              "extra charging time": int,
                                              "max range": int,
                                              "runway req": int,

                                              "weekly lease cost": int,
                                              "fixed operating cost": int,
                                              "time cost parameter": int,
                                              "fuel cost parameter": int,
                                              "batteries energy": int,

                                              "legs": {"viability": df of binaries,
                                                       "duration": df of floats,
                                                       "total operating cost": df of floats,
                                                       "yield per RPK": df of floats}

                                              "routes viability": {[route_ref]: binary}
                                              }

        - self.distances_df is a dataframe containing the distance flown between airports
        - self.traffic is a dataframe containing the amount of traffic for each route

        All dataframes are indexed using the airports ICAO codes for convenience
        """

        if question == 0:
            include_extra = False

        else:
            include_extra = True

        # -> Set Network hub
        self.hub = "Malmö"
        self.hub_ref = "ESMS"

        # -> Set fleet properties
        self.max_continuous_operation = 10
        self.average_load_factor = 0.8

        # -> Setup aircraft dict
        self.ac_dict = self.create_aircraft_dict(include_electric_ac=include_extra)

        # -> Import network nodes
        self.airports_dict = self.import_network_airports()

        # -> Solve for network legs properties
        self.distances_df = self.solve_edges_properties()

        # -> Solve for possible routes
        self.routes_dict = self.determine_routes_properties(include_two_stop_routes=include_extra)

        # -> Import network traffic
        self.demand_df = self.import_network_traffic()

    @staticmethod
    def create_aircraft_dict(include_electric_ac):
        fuel_ac = {"AC 1": {"speed": 550,
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
                            "batteries energy": 0}}

        electric_ac = {"AC 4": {"speed": 350,
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
                                "batteries energy": 8216}}

        if include_electric_ac:
            return {**fuel_ac, **electric_ac}

        else:
            return fuel_ac

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
        airports_dict = {}

        # -> Solving for runway viability for each aircraft type
        for index, row in df.iterrows():
            runway_compatibility = {}

            for aircraft_type, aircraft in self.ac_dict.items():
                if aircraft["runway req"] <= row["Runway (m)"]:
                    runway_compatibility[aircraft_type] = 1

                else:
                    runway_compatibility[aircraft_type] = 0

            airports_dict[row["ICAO Code"]] = {"lat": row["Latitude (deg)"],
                                               "lon": row["Longitude (deg)"],
                                               "runway": row["Runway (m)"],
                                               "runway compatibility": runway_compatibility}

        return airports_dict

    def solve_edges_properties(self):
        # -> Create network edge dataframe
        edges_df = pd.DataFrame(0,
                                index=np.arange(len(self.airports_dict)),
                                columns=np.arange(len(self.airports_dict)))

        edges_df.columns = list(node for node in self.airports_dict.keys())
        edges_df = edges_df.reindex(index=list(node for node in self.airports_dict.keys()), fill_value=0)

        # -> Create network legs properties per aircraft
        for aircraft in self.ac_dict.values():
            aircraft["legs"] = {
                                # "viability": deepcopy(edges_df),
                                "duration": deepcopy(edges_df),
                                "total operating cost": deepcopy(edges_df),
                                "yield per RPK": deepcopy(edges_df)}

        # -> Create network legs len df
        legs_len_df = deepcopy(edges_df)

        # -> Solving for legs values
        for airport_i_ref, airport_i in self.airports_dict.items():
            # -> Solving for distance between nodes using haversine equation
            for airport_j_ref, airport_j in self.airports_dict.items():
                if airport_i_ref == airport_j_ref:
                    continue
                else:
                    leg_len = \
                        haversine((airport_i["lat"], airport_i["lon"]), (airport_j["lat"], airport_j["lon"]))[1]

                    legs_len_df.loc[airport_i_ref, airport_j_ref] = leg_len

                    # -> Solving for leg property for each aircraft type
                    for aircraft_ref, aircraft in self.ac_dict.items():
                        # if aircraft["max range"] >= leg_len \
                        #         and airport_i["runway compatibility"][aircraft_ref] == 1 \
                        #         and airport_j["runway compatibility"][aircraft_ref] == 1:
                        #     # -> Mark leg as viable
                        #     aircraft["legs"]["viability"].loc[airport_i["ref"], airport_j["ref"]] = 1

                        # -> Solve for leg duration
                        aircraft["legs"]["duration"].loc[airport_i_ref, airport_j_ref] = \
                            leg_len / aircraft["speed"]

                        # -> Solve for leg total cost
                        fixed_operating_cost = aircraft["fixed operating cost"]

                        time_cost = aircraft["time cost parameter"] * (leg_len/aircraft["speed"])

                        fuel_cost = (aircraft["fuel cost parameter"]*1.42)/1.5 * leg_len

                        energy_cost = 0.07 * aircraft["batteries energy"] * leg_len/aircraft["max range"]

                        if airport_i == self.hub_ref or airport_j == self.hub_ref:
                            # fixed_operating_cost + time_cost + fuel_cost are 30% cheaper if departing/arrival airport is hub
                            aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] = \
                                (fixed_operating_cost + time_cost + fuel_cost) * 0.7 + energy_cost

                        else:
                            aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] = \
                                (fixed_operating_cost + time_cost + fuel_cost) + energy_cost

                        # Solve for leg yield per passenger
                        aircraft["legs"]["yield per RPK"].loc[airport_i_ref, airport_j_ref] = \
                            5.9*leg_len**(-0.76) + 0.043

        return legs_len_df

    def determine_routes_properties(self, include_two_stop_routes):
        # -> Create network edge dataframe
        edges_df = pd.DataFrame(0,
                                index=np.arange(len(self.airports_dict)),
                                columns=np.arange(len(self.airports_dict)))

        edges_df.columns = list(node for node in self.airports_dict.keys())
        edges_df = edges_df.reindex(index=list(node for node in self.airports_dict.keys()), fill_value=0)

        routes_dict = {}

        # -> Set single stop routes
        for airport_1_ref, airport_1 in self.airports_dict.items():
            if airport_1_ref == self.hub_ref:
                continue
            else:
                path = [self.hub_ref, airport_1_ref, self.hub_ref]
                routes_dict["-".join(path)] = {"path": path,
                                               "path df": deepcopy(edges_df),
                                               "length": 2*self.distances_df.loc[self.hub_ref, airport_1_ref]}

                routes_dict["-".join(path)]["path df"].loc[self.hub_ref, airport_1_ref] = 1
                routes_dict["-".join(path)]["path df"].loc[airport_1_ref, self.hub_ref] = 1

                if include_two_stop_routes:
                    # -> Set two stop routes
                    for airport_2_ref, airport_2 in self.airports_dict.items():
                        if airport_2_ref == self.hub_ref or airport_2_ref == airport_1_ref:
                            continue
                        else:
                            path = [self.hub_ref, airport_1_ref, airport_2_ref, self.hub_ref]
                            routes_dict["-".join(path)] = {"path": path,
                                                           "path df": deepcopy(edges_df),
                                                           "length": self.distances_df.loc[self.hub_ref, airport_1_ref]
                                                                     + self.distances_df.loc[airport_1_ref, airport_2_ref]
                                                                     + self.distances_df.loc[airport_2_ref, self.hub_ref]}

                            routes_dict["-".join(path)]["path df"].loc[self.hub_ref, airport_1_ref] = 1
                            routes_dict["-".join(path)]["path df"].loc[airport_1_ref, airport_2_ref] = 1
                            routes_dict["-".join(path)]["path df"].loc[airport_2_ref, self.hub_ref] = 1

        # -> Solve for route properties per aircraft
        for aircraft_ref, aircraft in self.ac_dict.items():
            aircraft["routes viability"] = {}

            for route_ref, route in routes_dict.items():
                # -> Checking route viability for aircraft model
                # > Checking range
                if aircraft["max range"] >= route["length"]:
                    viable = 1

                    # > Checking runways
                    for i in range(len(route["path"])-1):
                        airport_i = self.airports_dict[route["path"][i]]
                        airport_j = self.airports_dict[route["path"][i+1]]

                        if airport_i["runway compatibility"][aircraft_ref] == 1 \
                                and airport_j["runway compatibility"][aircraft_ref] == 1:
                            pass
                        else:
                            viable = 0

                    # -> Set route viability
                    aircraft["routes viability"][route_ref] = viable

                    # for i in range(len(route["path"])-1):
                    #     # -> Solve for route duration
                    #     aircraft["routes"][route_ref]["duration"] += \
                    #         aircraft["legs"]["duration"].loc[route["path"][i], route["path"][i+1]]
                    #
                    #     # -> Solve for route total cost
                    #     # > If current i is hub and not start
                    #     # if i != 0 and len(route_path) > 3 and route["path"][i] == self.hub_ref:
                    #
                    #     aircraft["routes"][route_ref]["total operating cost"] += \
                    #         aircraft["legs"]["total operating cost"].loc[route["path"][i], route["path"][i+1]]
                    #
                    #     # Solve for route yield per passenger
                    #     aircraft["routes"][route_ref]["yield per RPK"] += \
                    #         aircraft["legs"]["yield per RPK"].loc[route["path"][i], route["path"][i+1]]

        return routes_dict

    @staticmethod
    def import_network_traffic():
        df = pd.read_csv("Demand_per_week.csv", header=[0])
        df = df.set_index("Unnamed: 0")

        # TODO: Fix

        return df


if __name__ == "__main__":
    net = Network()

    # print(net.ac_dict)
    # print(net.airports_lst)
    # print(net.distances_df)
    # print(net.routes_dict)
    # print(net.traffic_df)

    print("\n")

    print("Network nodes count:", len(net.airports_dict))
    print("Aircraft type count:", len(net.ac_dict))
    print("Possible routes:", len(net.routes_dict))

    net = Network(question=1)

    # print(net.ac_dict)
    # print(net.airports_dict)
    # print(net.distances_df)
    # print(net.routes_dict)
    # print(net.traffic_df)

    print("\n")

    print("Network nodes count:", len(net.airports_dict))
    print("Aircraft type count:", len(net.ac_dict))
    print("Possible routes:", len(net.routes_dict))
