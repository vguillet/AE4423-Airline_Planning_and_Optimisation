"""
Created on 24 dec. 2021
@author: Group 10
@course: AE4423, Airline planning and optimisation
"""


import pandas as pd
from numpy import pi, sin, cos, arcsin, sqrt, ceil, floor


class Data_processor:
    """These are the DataFrames created from the given Excel files"""
    airport_input_df: pd.DataFrame
    # fleet_initial_final_position_input_df : pd.DataFrame
    OD_pairs_input_df: pd.DataFrame
    request_input_df: pd.DataFrame

    """These are all the usefull dicts, lists, and DataFrames to be returned in the export function"""
    airport_dict: dict
    OD_df: pd.DataFrame
    OD_list: list
    request_dict: dict
    distance_df : pd.DataFrame
    aircraft_dict : dict
    duration_df : pd.DataFrame
    max_arc_time : int

    def __init__(self):
        self.make_input_data_frames()
        self.timestep_duration = 4 # hours
        self.planning_horizon = 96 # TODO: take from here in netwerk gereration

        self.create_airport_dict()
        self.create_OD_df()
        self.create_request_dict()
        self.create_distance_df()
        self.create_aircraft_dict()
        self.create_duration_df()

    def make_input_data_frames(self):
        """
        The given excel files will be put into Dataframes.
        """

        dir = "G10"
        file_name = f"{dir}/airports_input_data.xlsx"
        self.airport_input_df = pd.read_excel(file_name)

        # file_name = f"{dir}/fleet_initial_final_position_input_data.xlsx"
        # self.fleet_initial_final_position_input_df = pd.read_excel(file_name)

        file_name = f"{dir}/OD_pairs_input_data.xlsx"
        self.OD_pairs_input_df = pd.read_excel(file_name)

        file_name = f"{dir}/requests_input_data.xlsx"
        self.request_input_df = pd.read_excel(file_name)

    def create_initial_final_aircrafts_dict(self):
        """
        In this dictionary the amount of aircrafts starting and ending in each airport is stored per airport as key
            Note that since this is the same initially as finally its stored as one variable
        This dictionary will eventually be storred within the airport_dict!
        :return: The dictionary with the amount of aircrafts starting and ending at an airport (per airport, per aircraft type)
        """
        init_fin_aircraft_dict = {}
        for i in self.airport_input_df.index:
            init_fin_aircraft_dict[self.airport_input_df.loc[i,"Airport"]] = {
                "AC_1" : 0,
                "AC_2" : 0
            }

        # TODO: dubbel check if correct
        """This is manually filled, because we only have to do the assignment once, and this is much faster"""
        init_fin_aircraft_dict["LUX"]["AC_1"] = 2
        init_fin_aircraft_dict["ORD"]["AC_1"] = 1
        init_fin_aircraft_dict["ORD"]["AC_2"] = 2

        return init_fin_aircraft_dict

    def create_airport_dict(self):
        """
        The airport_dict is a dictionary with the airport as keys.
        The information per airport is stored in a sub_dictionary.
        One special piece of information is the 'aircrafts' key
            this key contains a dictionary with the two aircraft types see 'create_initial_final_aircrafts_dict()'
        """

        init_fin_aircraft_dict = self.create_initial_final_aircrafts_dict()

        self.airport_dict = {}

        for i in self.airport_input_df.index:
            airport_ref = self.airport_input_df.loc[i,"Airport"]
            self.airport_dict[airport_ref] = {
                "lat"   : self.airport_input_df.loc[i,"Lat"],
                "lon"   : self.airport_input_df.loc[i,"Lon"],
                "index" : self.airport_input_df.loc[i,"Index"],
                "aircrafts" : init_fin_aircraft_dict[airport_ref],
            }

    def create_OD_df(self):
        """The OD_df is a Dataframe, with all the airports as index and columns (IACO).
        A one indicates that this OD pair excites, otherwise its zero.
        I also created the OD_list, which is a list of tuples, you never know if it might come in handy"""
        airports = self.airport_dict.keys()
        self.OD_df = pd.DataFrame(index=airports,columns=airports,data=0)
        self.OD_list = []
        for i in self.OD_pairs_input_df.index:
            airport_o_ref = self.OD_pairs_input_df.loc[i,'O']
            airport_d_ref = self.OD_pairs_input_df.loc[i,'D']
            self.OD_df.loc[airport_o_ref,airport_d_ref] = 1
            self.OD_list.append((airport_o_ref,airport_d_ref))

    def create_request_dict(self):
        """The request_dict is a dictionary with all the request ID's as key.
        The item per ID is the request, which is a sub_dictionary with the information about the reqeust"""
        self.request_dict = {}
        for i in self.request_input_df.index:
            release_step = int(ceil(self.request_input_df.loc[i,"Release time [minutes]"]/60/self.timestep_duration))
            if release_step < 0:
                release_step = 0

            due_step = int(floor(self.request_input_df.loc[i,"Due date [minutes]"]/60/self.timestep_duration))
            if due_step > self.planning_horizon/self.timestep_duration:
                due_step = self.planning_horizon/self.timestep_duration

            self.request_dict[self.request_input_df.loc[i,"Request ID"]] = {
                "weight":        self.request_input_df.loc[i,"Weight [ton]"], # TODO: check unit conversion!
                "airport_O":     self.request_input_df.loc[i,"Origin airport"],
                "airport_D":     self.request_input_df.loc[i,"Destination airport"],
                "release_time":  self.request_input_df.loc[i,"Release time [minutes]"], # TODO: check unit conversion!
                "release_step":  release_step,
                "due_time":      self.request_input_df.loc[i,"Due date [minutes]"], # TODO: check unit conversion!
                "due_step":      due_step,
                "penalty":       self.request_input_df.loc[i,"Penalty [MU/ton]"], # TODO: check unit conversion!
            }

    def create_distance_df(self):
        deg2rad = pi/180
        R_E = 6371 # km

        airports = self.airport_dict.keys()
        self.distance_df = pd.DataFrame(index=airports,columns=airports,data=0)

        for airport_i_ref, airport_i in self.airport_dict.items():
            for airport_j_ref, airport_j in self.airport_dict.items():

                ##just for conviniece
                lat_i = deg2rad * airport_i["lat"]
                lat_j = deg2rad * airport_j["lat"]
                lon_i = deg2rad * airport_i["lon"]
                lon_j = deg2rad * airport_j["lon"]

                term_1 = (sin( (lat_i-lat_j)/2 ))**2
                term_2 = cos(lat_i)*cos(lat_j)*(sin( (lon_i-lon_j)/2 ))**2

                self.distance_df.loc[airport_i_ref,airport_j_ref] = 2 * R_E * arcsin(sqrt(term_1+term_2)) # TODO: check unit conversion

    def create_aircraft_dict(self):
        """
        The aircraft dict has the information about each aircraft type
        """
        self.aircraft_dict = {
            "AC_1" : {
                "speed"             : 800, # km/h TODO: check unit conversion
                "payload"           : 50, # ton TODO: check unit conversion
                "TAT"               : 2, # h TODO: check unit conversion
                "LTO"               : 0.5, # h TODO: check unit conversion
                "operational_cost"  : 8 # MU/km TODO: check unit conversion
            },
            "AC_2" : {
                "speed"             : 800, # km/h TODO: check unit conversion
                "payload"           : 40, # ton TODO: check unit conversion
                "TAT"               : 2, # h TODO: check unit conversion
                "LTO"               : 0.5, # h TODO: check unit conversion
                "operational_cost"  : 6 # MU/km TODO: check unit conversion
            }
        }

    def create_duration_df(self):
        """
        Duration of a flight arc rounded up to fit the timesteps
            Note that the duration is equal for both aircraft types, because they have equal speed, LTO and TAT.
        """
        airports = self.airport_dict.keys()
        self.duration_df = pd.DataFrame(index=airports,columns=airports,data=0)

        self.max_arc_time = 0
        for airport_i_ref, airport_i in self.airport_dict.items():
            for airport_j_ref, airport_j in self.airport_dict.items():

                denominator = self.distance_df.loc[airport_i_ref,airport_j_ref]/self.aircraft_dict["AC_1"]["speed"] + \
                           self.aircraft_dict["AC_1"]["TAT"] + self.aircraft_dict["AC_1"]["LTO"]

                if airport_i_ref != airport_j_ref:
                    arc_time = ceil(denominator/self.timestep_duration)*self.timestep_duration
                    self.max_arc_time = max(arc_time,self.max_arc_time)
                    self.duration_df.loc[airport_i_ref,airport_j_ref] = arc_time

if __name__ == '__main__':
    D = Data_reader()
    # print(D.airport_input_df)
    # for airport_ref, airport in D.airport_dict.items():
    #     print(airport_ref,":",airport)
    # # print(D.OD_list)
    # # print(D.request_dict)
    # airport_dict, OD_df, OD_list, request_dict, distance_df, aircraft_dict = D.export()
    # for request_ID, request in request_dict.items():
    #     print(request_ID,":",request)
    #
    # print(distance_df)
    # print(OD_list)
    print(vars(D)["duration_df"])
