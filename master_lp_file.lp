\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  x_0 + x_1 + x_2 + x_3 + x_4 + x_5 + x_6
Subject To
 demand_length_2: x_0 >= 4
 demand_length_3: x_1 >= 2
 demand_length_4: x_2 >= 6
 demand_length_5: x_3 >= 6
 demand_length_6: x_4 >= 2
 demand_length_7: x_5 >= 2
 demand_length_8: x_6 >= 2
Bounds
 x_0 <= 30
 x_1 <= 30
 x_2 <= 30
 x_3 <= 30
 x_4 <= 30
 x_5 <= 30
 x_6 <= 30
Generals
 x_0 x_1 x_2 x_3 x_4 x_5 x_6
End
