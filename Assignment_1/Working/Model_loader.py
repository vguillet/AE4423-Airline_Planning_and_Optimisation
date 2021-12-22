# Built-in/Generic Imports

# Libs
import gurobipy as gp

# Own modules

# model = gp.Model("APO_assignment_model")

model = gp.read("Model_2.lp")

print("optimize")
model.optimize()

model.printStats()

print("\n\n=================================================================================================================")

# # =========================================================== Generate data
# hub, hub_ref, max_continuous_operation, average_load_factor, \
# aircraft_dict, airports_dict, distances_df, traffic_df, yield_df = generate_data()
#
#
# for aircraft_ref, aircraft in aircraft_dict.items():
#     print(decision_variable_dict["aircrafts"][aircraft_ref]["count"])
