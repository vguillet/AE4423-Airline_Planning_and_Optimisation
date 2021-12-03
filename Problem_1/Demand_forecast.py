import pandas as pd
import scipy.optimize as opt
import numpy as np
from numpy import cos, sin, arcsin, sqrt, log


class Demand_forcast():
    def __init__(self):
        # other data
        self.f = 1.42 # USD/gallon fuel cost in 2020
        self.annual_growth = 1.1 /100 # %/year
        self.R_E = 6371 # km radius of the earth

        # import data
        self.data, self.demand_2020 = self.import_data()

        # calculate distance
        self.distance = self.calculate_distance()

        # create training data
        self.training_data = self.find_matches()

        # fit Gravity model
        self.k, self.b1, self.b2 = self.fit_gravitiy_model()

        # create forcast
        self.demand_forcast_2030 = self.gravity_model()

    def import_data(self):
        file_name = "Assignment1_Problem1_Datasheets_v2.xlsx"
        sheet_name = "Group 10"
        data = pd.read_excel(file_name, sheet_name=sheet_name, header=1, usecols="C:Q", skiprows=5, nrows=4)
        data.index = ['Latitude', 'Longitude', 'Runway', 'Population']

        demand_2020 = pd.read_excel(file_name,sheet_name=sheet_name,header=1,usecols="C:L",skiprows=12,nrows=10)
        demand_2020.index = demand_2020.columns
        return data, demand_2020

    def calculate_distance(self):
        deg2rad = np.pi/180
        airports = self.data.columns

        d = np.zeros([len(airports),len(airports)])
        for i, airport_i in enumerate(airports):
            for j, airport_j in enumerate(airports):

                ##just for conviniece
                phi_i = deg2rad * self.data[airport_i]['Latitude']
                phi_j = deg2rad * self.data[airport_j]['Latitude']
                lambda_i = deg2rad * self.data[airport_i]['Longitude']
                lambda_j = deg2rad * self.data[airport_j]['Longitude']

                term_1 = (sin( (phi_i-phi_j)/2 ))**2
                term_2 = cos(phi_i)*cos(phi_j)*(sin( (lambda_i-lambda_j)/2 ))**2

                d[i,j] =  2 * self.R_E * arcsin(sqrt(term_1+term_2))

        distance = pd.DataFrame(d,airports,airports)

        return distance

    def find_matches(self):
        matches = []
        x_training = []
        y_training = []


        for airport in self.data.columns:
            if airport in self.demand_2020.columns:
                matches.append(airport)

        for airport_i in matches:
            for airport_j in matches:
                if airport_i != airport_j:
                    x_training.append(np.array([self.distance[airport_i][airport_j],
                                                self.data[airport_i]["Population"],
                                                self.data[airport_j]["Population"]]))

                    # the training y is de avarage of the demand back and forth because the gravitiy model is symetrical
                    y = (self.demand_2020[airport_i][airport_j] + self.demand_2020[airport_j][airport_i])/2
                    y_training.append( log(y) )

        return {"x":x_training, "y":y_training}

    def gravity_model_training(self,x_training,k,b1,b2):
        y_training = []

        for x in x_training:
            y = k*(x[1]*x[2])**b1/(self.f*x[0])**b2
            y_training.append( log(y) ) # we train on a linearized method, so log
        return y_training

    def gravity_model(self, year = 2030):
        duration = year - 2020

        demand = pd.DataFrame([],self.data.columns,self.data.columns)

        for airport_i in self.data.columns:
            for airport_j in self.data.columns:
                if airport_i != airport_j:
                    population_i_forcast = self.data[airport_i]['Population'] * (1 + self.annual_growth) ** duration
                    population_j_forcast = self.data[airport_j]['Population'] * (1 + self.annual_growth) ** duration

                    numerator = self.k * (population_i_forcast * population_j_forcast) ** self.b1
                    denominator = (self.f*self.distance[airport_i][airport_j])**self.b2
                    demand[airport_i][airport_j] = int(round(numerator/denominator))
                else:
                    demand[airport_i][airport_j] = 0

        return demand

    def fit_gravitiy_model(self):
        [k,b1,b2], pcov = opt.curve_fit(self.gravity_model_training,self.training_data["x"],self.training_data["y"])
        return k, b1, b2

    def save(self,file_name = "Problem_1/Demand_forecast_2030.csv"):
        self.demand_forcast_2030.to_csv(file_name)


if __name__ == '__main__':
    D = Demand_forcast()
    D.save()
