import pandas as pd

file_name = "Assignment1_Problem1_Datasheets_v2.xlsx"
sheet_name = "Group 10"

airport_data = pd.read_excel(file_name,sheet_name=sheet_name,header=1,usecols="C:Q",skiprows=4,nrows=5)
airport_data.index = ['ICAO','Latitude','Longitude','Runway','Population']

airports = airport_data.columns
keys = airport_data.index

demand_2020 = pd.read_excel(file_name,sheet_name=sheet_name,header=1,usecols="C:L",skiprows=12,nrows=10)
demand_2020.index = demand_2020.columns #from to??

# print(demand_2020)
#
# for airport in airports:
#     print(airport,airport_data[airport]['Runway'])

