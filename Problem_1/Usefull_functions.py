import numpy as np
from numpy import cos, sin, arcsin, sqrt, log, exp
from numpy import pi as PI

'''rad to deg'''
deg2rad = PI/180


def Distance(phi_i,phi_j,lambda_i,lambda_j,mode='deg'): ###in deg!
    '''phi and lamda are the latitude and longitude of the airports i and j respectively
    returns the distance between two airporst'''
    R_E = 6371
    if mode == 'deg':
        phi_i *= deg2rad
        phi_j *= deg2rad
        lambda_i *= deg2rad
        lambda_j *= deg2rad
    term_1 = (sin( (phi_i-phi_j)/2 ))**2
    term_2 = cos(phi_i)*cos(phi_j)*(sin( (lambda_i-lambda_j)/2 ))**2
    arc =  2 * arcsin(sqrt(term_1+term_2))
    return arc * R_E
