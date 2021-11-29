import pandas as pd
import numpy as np
from numpy import cos, sin, arcsin, sqrt
deg2rad = np.pi/180


'''Parameters'''
file_name = "Assignment1_Problem1_Datasheets_v2.xlsx"
sheet_name = "Group 10"
R_E = 6371 # km radius of the Earth
f = 1.42 # USD/gallon fuel cost in 2020

'''Fromulas'''
def calc_arc(phi_i,phi_j,lambda_i,lambda_j,mode='deg'): ###in deg!
    if mode == 'deg':
        phi_i *= deg2rad
        phi_j *= deg2rad
        lambda_i *= deg2rad
        lambda_j *= deg2rad
    term_1 = (sin( (phi_i-phi_j)/2 ))**2
    term_2 = cos(phi_i)*cos(phi_j)*(sin( (lambda_i-lambda_j)/2 ))**2
    arc =  2 * arcsin(sqrt(term_1+term_2))
    return arc

'''import data'''
data = pd.read_excel(file_name, sheet_name=sheet_name, header=1, usecols="C:Q", skiprows=4, nrows=5)
data.index = ['ICAO', 'Latitude', 'Longitude', 'Runway', 'Population']

# for conviniece
airports = data.columns
keys = data.index

demand_2020 = pd.read_excel(file_name,sheet_name=sheet_name,header=1,usecols="C:L",skiprows=12,nrows=10)
demand_2020.index = demand_2020.columns #from to??

'''calculate distance '''
dij = np.zeros([data.shape[1], data.shape[1]]) ## dij is distance matrix in km
delta_dij = np.zeros(dij.shape) ## arc length

for i, airport_i in enumerate(airports):
    for j, airport_j in enumerate(airports):
        delta_dij[i,j] = calc_arc(data[airport_i]['Latitude'],data[airport_j]['Latitude'],data[airport_i]['Longitude'],data[airport_j]['Longitude'])
        dij[i,j] = R_E * delta_dij[i,j]
        # print(f"from {airport_i} to {airport_j} is {dij[i,j]}km")
        if i > j:
            assert dij[i,j] == dij[j,i] #dubbelcheck

'''PromblemA'''



# print(demand_2020)
#
# for airport in airports:
#     print(airport,airport_data[airport]['Runway'])


# for airport in airports:
#     ICAO = airport_data[airport]['ICAO']
#     if ICAO in demand_2020.index:
#         print(ICAO," YES")
#     else: print(ICAO, 'NO')

