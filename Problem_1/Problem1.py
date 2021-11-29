import pandas as pd
import numpy as np
from numpy import cos, sin, arcsin, sqrt, log, exp
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

def demand_forcast_log(ijs, k, b1, b2):
    '''formula to calcuate log of demand'''
    Dij = []
    for ij in ijs:
        i=int(ij[0])
        j=int(ij[1])
        pop_i = data[airports[i]]['Population']
        pop_j = data[airports[j]]['Population']
        dij = d[i,j]
        Dij.append(k*(pop_i*pop_j)**b1/(f*dij)**b2)
    return log(Dij)


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

x_data = np.array(x_data)
y = np.array(y)
y_data = y*(annual_growth+1)**10
y_data_log = log(y_data)

# find optimal solution using Scipy that uses least squares as cost
popt, pcov = opt.curve_fit(demand_forcast,x_data,y_data)
popt_log, pcov_log = opt.curve_fit(demand_forcast_log, x_data, y_data_log)



'''Debug'''
perr_lin = sqrt(np.diag(pcov))
perr_log = sqrt(np.diag(pcov_log))

for i , name in enumerate(['k','b1','b2']):
    print(f'optimal {name}_lin = {round(popt[i],3)} +- {round(perr_lin[i],3)},   {name}_log = {round(popt_log[i],3)} +- {round(perr_log[i],3)}')
k = popt_log[0]
b1 = popt_log[1]
b2 = popt_log[2]

D = np.zeros(d.shape)
for i, airport_i in enumerate(airports):
    for j, airport_j in enumerate(airports):
        if i!=j:
            # print(k*(data[airport_i]['Population']*data[airport_j]['Population'])**b1/(f*d[i,j])**b2)
            D[i,j] = k*(data[airport_i]['Population']*data[airport_j]['Population'])**b1/(f*d[i,j])**b2

D_df = pd.DataFrame(D,airports,airports)
print('---------------- Demand Forcast: -----------------')
print(D_df)
D_df.to_csv('Problem_1/Demand_forecast.csv')
