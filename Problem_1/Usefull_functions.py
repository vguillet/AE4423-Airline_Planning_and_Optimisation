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

def pcol(input,c):
    style = {'black' : '\033[30m',
             'r'    : '\033[31m',
             'g'  : '\033[32m',
              'o' : '\033[33m',
             'y' : '\033[93m',
             'b'   : '\033[34m',
              'lb'   : '\033[94m',
             'p'  : '\033[35m',
             'm'  : '\033[95m',
             'c'   : '\033[36m',
             'w' : '\033[97m',
             'END'   : '\033[0m',
             'B'   : '\033[1m',
             'DIM' : '\033[2m',
             'U' : '\033[4m',
             'BLINK' : '\033[5m'}

    string = ''
    if c == 'RAINBOW':
        rainbow = ['r','y','g','lb','b','p','m']
        for i , s in enumerate(str(input)):
            string+= style[rainbow[i%len(rainbow)]] + s
    else:
        c = c.split()
        for i in c:
            string += style[i]
        string += f'{input}'

    return string + style["END"]
