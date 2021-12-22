s='''
    aqua, aquamarine,
    blue,
    blueviolet, brown, cadetblue,
    chartreuse, chocolate, coral, cornflowerblue,
    crimson, cyan, darkblue, darkcyan,
    darkgoldenrod, darkgreen,
    darkkhaki, darkmagenta, darkolivegreen, darkorange,
    darkorchid, darkred, darksalmon, darkseagreen,
    darkslateblue, darkslategray,
    darkturquoise, darkviolet, deeppink, deepskyblue,
    dodgerblue, firebrick,
    floralwhite, forestgreen, fuchsia, gainsboro,
    gold, goldenrod, gray, green,
    greenyellow, honeydew, hotpink, indianred, indigo,
    khaki, lavender, lawngreen,
    lightblue, lightcoral,
    lightgoldenrodyellow,
    lightgreen, lightpink, lightsalmon, lightseagreen,
    lightskyblue,
    lightsteelblue, lime, limegreen,
    magenta, maroon, mediumaquamarine,
    mediumblue, mediumorchid, mediumpurple,
    mediumseagreen, mediumslateblue, mediumspringgreen,
    mediumturquoise, mediumvioletred,
    olive, olivedrab, orange, orangered,
    orchid, palegoldenrod, palegreen, paleturquoise,
    palevioletred, papayawhip, peachpuff, peru, pink,
    plum, powderblue, purple, red, rosybrown,
    royalblue, saddlebrown, salmon, sandybrown,
    seagreen, seashell, sienna, skyblue,
    slateblue, springgreen,
    steelblue, teal, thistle, tomato, turquoise,
    violet, wheat, yellow,
    yellowgreen
    '''
li=s.split(',')
li=[l.replace('\n','') for l in li]
li=[l.replace(' ','') for l in li]

import pandas as pd
import plotly.graph_objects as go

df=pd.DataFrame.from_dict({'colour': li})
fig = go.Figure(data=[go.Table(
  header=dict(
    values=["Plotly Named CSS colours"],
    line_color='black', fill_color='white',
    align='center', font=dict(color='black', size=14)
  ),
  cells=dict(
    values=[df.colour],
    line_color=[df.colour], fill_color=[df.colour],
    align='center', font=dict(color='black', size=11)
  ))
])

fig.show()
