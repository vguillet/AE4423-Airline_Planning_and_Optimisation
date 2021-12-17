import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt, pi, sin, cos
from numpy import arcsin
import sys
from copy import deepcopy

USD2EUR = 1  # EUR/USD in 2020
e_eur = 0.07 * USD2EUR  # EUR/kWh
f_eur = 1.42 * USD2EUR  # EUR/gallon


def haversine(coord1: tuple, coord2: tuple):
    deg2rad = pi / 180
    R = 6371
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # just for convenience
    phi_i = deg2rad * lat1
    phi_j = deg2rad * lat2
    lambda_i = deg2rad * lon1
    lambda_j = deg2rad * lon2

    term_1 = (sin((phi_i - phi_j) / 2)) ** 2
    term_2 = cos(phi_i) * cos(phi_j) * (sin((lambda_i - lambda_j) / 2)) ** 2

    km = 2 * R * arcsin(sqrt(term_1 + term_2))

    return 0, km


def generate_data(include_two_stop_routes=True, include_electric_ac=True, airports_included=15):
    # -> Set Network hub
    hub = "Malmö"
    hub_ref = "ESMS"

    # -> Set fleet properties
    max_continuous_operation = 10 * 7
    average_load_factor = 0.8

    # =========================================================== Create aircraft dict
    fuel_ac = {"AC_1": {"speed": 550,
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

               "AC_2": {"speed": 820,
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

               "AC_3": {"speed": 850,
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

    electric_ac = {"AC_4": {"speed": 350,
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

                   "AC_5": {"speed": 480,
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
        ac_dict = {**fuel_ac, **electric_ac}

    else:
        ac_dict = fuel_ac

        # =========================================================== Import airport
    airport_df = pd.read_csv("Problem_2/Destination_coordinates.csv")

    # -> Reshape data
    airport_df = airport_df.transpose()
    airport_df.columns = airport_df.iloc[0]
    airport_df = airport_df.iloc[1:].reset_index(drop=True)

    # -> Remove unnecessary data
    airport_df = airport_df.drop("Population", 1)

    # -> Adjust type
    airport_df["Latitude (deg)"] = pd.to_numeric(airport_df["Latitude (deg)"])
    airport_df["Longitude (deg)"] = pd.to_numeric(airport_df["Longitude (deg)"])
    airport_df["Runway (m)"] = pd.to_numeric(airport_df["Runway (m)"])

    # -> Create a node per destination
    airports_dict = {}

    # -> Solving for runway viability for each aircraft type
    for index, row in airport_df.iterrows():
        runway_compatibility = {}

        for aircraft_type, aircraft in ac_dict.items():
            if aircraft["runway req"] <= row["Runway (m)"]:
                runway_compatibility[aircraft_type] = 1

            else:
                runway_compatibility[aircraft_type] = 0

        airports_dict[row["ICAO Code"]] = {"lat": row["Latitude (deg)"],
                                           "lon": row["Longitude (deg)"],
                                           "runway": row["Runway (m)"],
                                           "runway compatibility": runway_compatibility}

        # ======================================================================================================
    # ======================================================================================================
    # ======================================================================================================
    # TODO: Remove once debugged

    new_airport_dict = {}

    for airport_ref in airports_dict.keys():
        airports_included -= 1
        if airports_included >= 0:
            new_airport_dict[airport_ref] = airports_dict[airport_ref]

    airports_dict = new_airport_dict
    print(airports_dict.keys())

    # ======================================================================================================
    # ======================================================================================================
    # ======================================================================================================

    # =========================================================== Prepare network edge dataframe
    # -> Create network edge dataframe
    edges_df = pd.DataFrame(0,
                            index=np.arange(len(airports_dict)),
                            columns=np.arange(len(airports_dict)))

    edges_df.columns = list(node for node in airports_dict.keys())
    edges_df = edges_df.reindex(index=list(node for node in airports_dict.keys()), fill_value=0)

    # =========================================================== Solve for edge properties
    # -> Create network legs properties per aircraft
    for aircraft in ac_dict.values():
        aircraft["legs"] = {
            # "viability": deepcopy(edges_df),
            "duration": deepcopy(edges_df),
            "total operating cost": deepcopy(edges_df),
            # "yield per RPK": deepcopy(edges_df)
        }

        # -> Create network legs len df
    distances_df = deepcopy(edges_df)
    yield_df = deepcopy(edges_df)

    # -> Solving for legs values
    for airport_i_ref, airport_i in airports_dict.items():
        # -> Solving for distance between nodes using haversine equation
        for airport_j_ref, airport_j in airports_dict.items():
            if airport_i_ref == airport_j_ref:
                continue
            else:
                leg_len = \
                    haversine((airport_i["lat"], airport_i["lon"]), (airport_j["lat"], airport_j["lon"]))[1]

                distances_df.loc[airport_i_ref, airport_j_ref] = leg_len

                # Solve for leg yield per passenger
                yield_df.loc[airport_i_ref, airport_j_ref] = 5.9 * leg_len ** (-0.76) + 0.043

                # -> Solving for leg property for each aircraft type
                for aircraft_ref, aircraft in ac_dict.items():
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

                    time_cost = aircraft["time cost parameter"] * (leg_len / aircraft["speed"])

                    fuel_cost = (aircraft["fuel cost parameter"] * f_eur) / 1.5 * leg_len

                    energy_cost = e_eur * aircraft["batteries energy"] * leg_len / aircraft["max range"]

                    if airport_i == hub_ref or airport_j == hub_ref:
                        # fixed_operating_cost + time_cost + fuel_cost are 30% cheaper if departing/arrival airport is hub
                        aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] = \
                            (fixed_operating_cost + time_cost + fuel_cost) * 0.7 + energy_cost

                    else:
                        aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] = \
                            (fixed_operating_cost + time_cost + fuel_cost) + energy_cost

                        # =========================================================== Determine route properties
    # -> Create network edge dataframe
    edges_df = pd.DataFrame(0,
                            index=np.arange(len(airports_dict)),
                            columns=np.arange(len(airports_dict)))

    edges_df.columns = list(node for node in airports_dict.keys())
    edges_df = edges_df.reindex(index=list(node for node in airports_dict.keys()), fill_value=0)

    routes_dict = {}

    # -> Set single stop routes
    for airport_1_ref, airport_1 in airports_dict.items():
        if airport_1_ref == hub_ref:
            continue
        else:
            path = [hub_ref, airport_1_ref, hub_ref]

            subsequent_nodes = {hub_ref: [airport_1_ref, hub_ref],
                                airport_1_ref: [hub_ref]}

            precedent_nodes = {hub_ref: [hub_ref],
                               airport_1_ref: [airport_1_ref, hub_ref]}

            routes_dict["-".join(path)] = {"path": path,
                                           "path df": deepcopy(edges_df),
                                           "subsequent nodes": subsequent_nodes,
                                           "precedent nodes": precedent_nodes,
                                           "length": 2 * distances_df.loc[hub_ref, airport_1_ref]}

            routes_dict["-".join(path)]["path df"].loc[hub_ref, airport_1_ref] = 1
            routes_dict["-".join(path)]["path df"].loc[airport_1_ref, hub_ref] = 1

            if include_two_stop_routes:
                # -> Set two stop routes
                for airport_2_ref, airport_2 in airports_dict.items():
                    if airport_2_ref == hub_ref or airport_2_ref == airport_1_ref:
                        continue
                    else:
                        path = [hub_ref, airport_1_ref, airport_2_ref, hub_ref]

                        subsequent_nodes = {hub_ref: [airport_1_ref, airport_2_ref, hub_ref],
                                            airport_1_ref: [airport_2_ref, hub_ref],
                                            airport_2_ref: [hub_ref]}

                        precedent_nodes = {hub_ref: [hub_ref],
                                           airport_1_ref: [airport_1_ref, hub_ref],
                                           airport_2_ref: [airport_2_ref, airport_1_ref, hub_ref]}

                        routes_dict["-".join(path)] = {"path": path,
                                                       "path df": deepcopy(edges_df),
                                                       "subsequent nodes": subsequent_nodes,
                                                       "precedent nodes": precedent_nodes,
                                                       "length": distances_df.loc[hub_ref, airport_1_ref]
                                                                 + distances_df.loc[airport_1_ref, airport_2_ref]
                                                                 + distances_df.loc[airport_2_ref, hub_ref]}

                        routes_dict["-".join(path)]["path df"].loc[hub_ref, airport_1_ref] = 1
                        routes_dict["-".join(path)]["path df"].loc[airport_1_ref, airport_2_ref] = 1
                        routes_dict["-".join(path)]["path df"].loc[airport_2_ref, hub_ref] = 1

                        # -> Solve for route properties per aircraft
    for aircraft_ref, aircraft in ac_dict.items():
        aircraft["routes viability"] = {}

        for route_ref, route in routes_dict.items():
            # -> Checking route viability for aircraft model
            # > Checking range
            viable = 0
            if aircraft["max range"] >= route["length"]:
                viable = 1

                # > Checking runways
                for i in range(len(route["path"]) - 1):
                    airport_i = airports_dict[route["path"][i]]
                    airport_j = airports_dict[route["path"][i + 1]]

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
            #     # if i != 0 and len(route_path) > 3 and route["path"][i] == hub_ref:
            #
            #     aircraft["routes"][route_ref]["total operating cost"] += \
            #         aircraft["legs"]["total operating cost"].loc[route["path"][i], route["path"][i+1]]
            #
            #     # Solve for route yield per passenger
            #     aircraft["routes"][route_ref]["yield per RPK"] += \
            #         aircraft["legs"]["yield per RPK"].loc[route["path"][i], route["path"][i+1]]

    # =========================================================== Import network traffic
    traffic_df = pd.read_csv("Demand_forecast_2030.csv", header=[0])
    traffic_df = traffic_df.set_index("Unnamed: 0")

    # TODO: Fix

    return hub, hub_ref, max_continuous_operation, average_load_factor, ac_dict, airports_dict, distances_df, routes_dict, traffic_df, yield_df


if __name__ == "__main__":
    hub, hub_ref, max_continuous_operation, average_load_factor, ac_dict, airports_dict, distances_df, routes_dict, traffic_df, yield_df = generate_data(
        question=1)

    # print(ac_dict)
    # print(airports_dict)
    # print(distances_df)
    # print(routes_dict)
    # print(traffic_df)

    print("\n")

    print("Network nodes count:", len(airports_dict))
    print("Aircraft type count:", len(ac_dict))
    print("Possible routes:", len(routes_dict))
