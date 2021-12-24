"""
Created on 24 dec. 2021
@author: Group 10
@course: AE4423, Airline planning and optimisation
"""


import pandas as pd


class Data_reader:
    """These are the DataFrames created from the given Excel files"""
    airport_input_df: pd.DataFrame
    # fleet_initial_final_position_input_df : pd.DataFrame
    OD_pairs_input_df: pd.DataFrame
    requests_input_df: pd.DataFrame

    """These are all the usefull dicts, lists, and DataFrames to be returned in the export function"""
    airports_dict: dict
    OD_df: pd.DataFrame
    OD_list: list
    requests_dict: dict

    def __init__(self):
        self.make_data_frames()
        self.create_airport_dict()
        self.create_OD_df()
        self.create_request_dict()

    def make_data_frames(self):
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
        self.requests_input_df = pd.read_excel(file_name)

    def create_initial_final_aircrafts_dict(self):
        """
        In this dictionary the amount of aircrafts starting and ending in each airport is stored per airport as key
            Note that since this is the same initially as finally its stored as one variable
        This dictionary will eventually be storred within the airport_dict!
        :return: The dictionary with the amount of aircrafts starting and ending at an airport (per airport, per aircraft type)
        """
        init_fin_aircrafts_dict = {}
        for i in self.airport_input_df.index:
            init_fin_aircrafts_dict[self.airport_input_df.loc[i,"Airport"]] = {
                "AC_1" : 0,
                "AC_2" : 0
            }

        # TODO: dubbel check if correct
        """This is manually filled, because we only have to do the assignment once, and this is much faster"""
        init_fin_aircrafts_dict["LUX"]["AC_1"] = 2
        init_fin_aircrafts_dict["ORD"]["AC_1"] = 1
        init_fin_aircrafts_dict["ORD"]["AC_2"] = 2

        return init_fin_aircrafts_dict

    def create_airport_dict(self):
        """
        The airport_dict is a dictionary with the airport as keys.
        The information per airport is stored in a sub_dictionary.
        One special piece of information is the 'aircrafts' key
            this key contains a dictionary with the two aircraft types see 'create_initial_final_aircrafts_dict()'
        """

        init_fin_aircrafts_dict = self.create_initial_final_aircrafts_dict()

        self.airports_dict = {}

        for i in self.airport_input_df.index:
            airport_ref = self.airport_input_df.loc[i,"Airport"]
            self.airports_dict[airport_ref] = {
                "lat"   : self.airport_input_df.loc[i,"Lat"],
                "lon"   : self.airport_input_df.loc[i,"Lon"],
                "index" : self.airport_input_df.loc[i,"Index"],
                "aircrafts" : init_fin_aircrafts_dict[airport_ref],
            }

    def create_OD_df(self):
        """The OD_df is a Dataframe, with all the airports as index and columns (IACO).
        A one indicates that this OD pair excites, otherwise its zero.
        I also created the OD_list, which is a list of tuples, you never know if it might come in handy"""
        airports = self.airports_dict.keys()
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
        self.requests_dict = {}
        for i in self.requests_input_df.index:
            self.requests_dict[self.requests_input_df.loc[i,"Request ID"]] = {
                "weight":       self.requests_input_df.loc[i,"Weight [ton]"], # TODO: check unit conversion!
                "airport_O":    self.requests_input_df.loc[i,"Origin airport"],
                "airport_D":    self.requests_input_df.loc[i,"Destination airport"],
                "release_time": self.requests_input_df.loc[i,"Release time [minutes]"], # TODO: check unit conversion!
                "due_time":     self.requests_input_df.loc[i,"Due date [minutes]"], # TODO: check unit conversion!
                "penalty":      self.requests_input_df.loc[i,"Penalty [MU/ton]"], # TODO: check unit conversion!
            }

    def export(self):
        """
        Call this function to export the usefull dictionaries, lists and DataFrames for network generation
        :return: airports_dict, OD_df, OD_list, requests_dict
        """

        return self.airports_dict, self.OD_df, self.OD_list, self.requests_dict

if __name__ == '__main__':
    D = Data_reader()
    print(D.airport_input_df)
    for airport_ref, airport in D.airports_dict.items():
        print(airport_ref,":",airport)
    # print(D.OD_list)
    # print(D.requests_dict)
    airports_dict, OD_df, OD_list, requests_dict = D.export()
    for request_ID, request in requests_dict.items():
        print(request_ID,":",request)
