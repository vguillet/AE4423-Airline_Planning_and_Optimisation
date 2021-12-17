import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt, pi, sin, cos
from numpy import arcsin
import sys
from copy import deepcopy

USD2EUR = 1           # EUR/USD in 2020
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

def generate_data():
    # -> Set Network hub
    hub = "Malmö"
    hub_ref = "ESMS"

    # -> Set fleet properties
    max_continuous_operation = 10 * 7
    average_load_factor = 0.8
    
    # =========================================================== Create aircraft dict
    ac_dict = {"AC_1": {"speed": 550,
                        "seats": 45,
                        "avg TAT": 25,
                        "max range": 1500,
                        "runway req": 1400,

                        "weekly lease cost": 15000,
                        "fixed operating cost": 300,
                        "time cost parameter": 750,
                        "fuel cost parameter": 1,

                        "color": "#4040FF"},

               "AC_2": {"speed": 820,
                        "seats": 70,
                        "avg TAT": 35,
                        "max range": 3300,
                        "runway req": 1600,

                        "weekly lease cost": 34000,
                        "fixed operating cost": 600,
                        "time cost parameter": 775,
                        "fuel cost parameter": 2,

                        "color" : "#FF3030"},

               "AC_3": {"speed": 850,
                        "seats": 150,
                        "avg TAT": 45,
                        "max range": 6300,
                        "runway req": 1800,

                        "weekly lease cost": 80000,
                        "fixed operating cost": 1250,
                        "time cost parameter": 1400,
                        "fuel cost parameter": 3.75,


                        "color" : "green"},
                        }

    # =========================================================== Import airport
    airport_df = pd.read_csv("Destination_coordinates.csv")

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
    
    # =========================================================== Prepare network edge dataframe
    # -> Create empty network edge dataframe
    edges_df = pd.DataFrame(0,
                            index=np.arange(len(airports_dict)),
                            columns=np.arange(len(airports_dict)))

    edges_df.columns = list(node for node in airports_dict.keys())
    edges_df = edges_df.reindex(index=list(node for node in airports_dict.keys()), fill_value=0)
    
    # =========================================================== Solve for edge properties
    # -> Create network legs properties per aircraft
    for aircraft in ac_dict.values():
        aircraft["legs"] = {"viability": deepcopy(edges_df),
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
                    if aircraft["max range"] >= leg_len \
                            and airport_i["runway compatibility"][aircraft_ref] == 1 \
                            and airport_j["runway compatibility"][aircraft_ref] == 1:
                        # -> Mark leg as viable
                        aircraft["legs"]["viability"].loc[airport_i_ref, airport_j_ref] = 1

                        # -> Solve for leg duration
                        aircraft["legs"]["duration"].loc[airport_i_ref, airport_j_ref] = \
                            leg_len / aircraft["speed"]

                        # -> Solve for leg total cost
                        fixed_operating_cost = aircraft["fixed operating cost"]

                        time_cost = aircraft["time cost parameter"] * (leg_len/aircraft["speed"])

                        fuel_cost = (aircraft["fuel cost parameter"]*f_eur)/1.5 * leg_len

                        if airport_i == hub_ref or airport_j == hub_ref:
                            # fixed_operating_cost + time_cost + fuel_cost are 30% cheaper if departing/arrival airport is hub
                            aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] = \
                                (fixed_operating_cost + time_cost + fuel_cost) * 0.7

                        else:
                            aircraft["legs"]["total operating cost"].loc[airport_i_ref, airport_j_ref] = \
                                fixed_operating_cost + time_cost + fuel_cost

    # =========================================================== Import network traffic
    traffic_df = pd.read_csv("Demand_forecast_2030.csv", header=[0])
    traffic_df = traffic_df.set_index("Unnamed: 0")

    return hub, hub_ref, max_continuous_operation, average_load_factor, ac_dict, airports_dict, distances_df, traffic_df, yield_df


if __name__ == "__main__":
    hub, hub_ref, max_continuous_operation, average_load_factor, ac_dict, airports_dict, distances_df, traffic_df, yield_df = generate_data()

    print("Network nodes count:", len(airports_dict))
    print("Aircraft type count:", len(ac_dict))
    print(distances_df.to_string())
