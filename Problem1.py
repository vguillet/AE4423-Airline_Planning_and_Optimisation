import pandas as pd
import numpy as np
from numpy import cos, sin, arcsin, sqrt
import scipy.optimize as opt


'''Parameters'''
deg2rad = np.pi/180
file_name = "Assignment1_Problem1_Datasheets_v2.xlsx"
sheet_name = "Group 10"
R_E = 6371 # km radius of the Earth
f = 1.42 # USD/gallon fuel cost in 2020
annual_growth = 1.1 / 100 #%

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
d = np.zeros([data.shape[1], data.shape[1]]) ## dij is distance matrix in km
delta_d = np.zeros(d.shape) ## arc length

for i, airport_i in enumerate(airports):
    for j, airport_j in enumerate(airports):
        delta_d[i, j] = calc_arc(data[airport_i]['Latitude'], data[airport_j]['Latitude'], data[airport_i]['Longitude'], data[airport_j]['Longitude'])
        d[i, j] = R_E * delta_d[i, j]
        # print(f"from {airport_i} to {airport_j} is {dij[i,j]}km")
        if i > j:
            assert d[i, j] == d[j, i] #dubbelcheck

'''PromblemA'''
def demand_forcast(ijs,k,b1,b2):
    '''formula to calcuate demand'''
    Dij = []
    for ij in ijs:
        i=int(ij[0])
        j=int(ij[1])
        pop_i = data[airports[i]]['Population']
        pop_j = data[airports[j]]['Population']
        dij = d[i,j]
        Dij.append(k*(pop_i*pop_j)**b1/(f*dij)**b2)
    return Dij


# find the matches in the given demand_2020 data and the airport data,
# and save both the index of the airport in data, as well as the ICAO code
matches = []
for i, airport in enumerate(airports):
    ICAO = data[airport]['ICAO']
    if ICAO in demand_2020.index:
        matches.append([i,ICAO])

# create x and y data for fitting, by cross pairing the found matches
x_data = []
y = []
y_data = []
for i in matches:
    for j in matches:
        if i[0] != j[0]:
            x_data.append(np.array([i[0],j[0]]))
            y.append(demand_2020[i[1]][j[1]])
            y_data.append(demand_2020[i[1]][j[1]] * (1 + annual_growth) ** 10)


# find optimal solution using Scipy that uses least squares as cost
popt, pcov2 = opt.curve_fit(demand_forcast,x_data,y_data)

'''Debug'''
for i , name in enumerate(['k','b1','b2']):
    print(f'optimal {name} = {popt[i]}')

y_calc = demand_forcast(x_data,popt[0],popt[1],popt[2])
for i in range(len(y_data)):
    print(f'given demand 2020: {y[i]},    with annual growth: {round(y_data[i],3)},    optimal gravity model: {round(y_calc[i],3)}')




