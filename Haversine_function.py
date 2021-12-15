import math
from numpy import sin,cos,arcsin,pi,sqrt




# def haversine(coord1: tuple, coord2: tuple):
#     lat1, lon1 = coord1
#     lat2, lon2 = coord2
#
#     R = 6371000  # radius of Earth in meters
#     phi_1 = math.radians(lat1)
#     phi_2 = math.radians(lat2)
#
#     delta_phi = math.radians(lat2 - lat1)
#     delta_lambda = math.radians(lon2 - lon1)
#
#     a = math.sin(delta_phi / 2.0) ** 2 + \
#         math.cos(phi_1) * math.cos(phi_2) * \
#         math.sin(delta_lambda / 2.0) ** 2
#     c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
#
#     meters = R * c  # output distance in meters
#     km = meters / 1000.0  # output distance in kilometers
#
#     return meters, km


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
