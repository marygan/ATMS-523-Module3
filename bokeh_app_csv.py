

import datetime
from os.path import dirname, join
import os
import pandas as pd
from scipy.signal import savgol_filter

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Range1d, Select
from bokeh.palettes import Blues4
from bokeh.plotting import figure
from bokeh.io import show, output_notebook, push_notebook


STATISTICS = ['record_min_temp', 'average_min_temp', 'actual_low', 'actual_high', 'average_max_temp','record_max_temp']

def get_dataset(src,name, distribution):
    df = src[src.ID == name].copy()
    del df['ID']
    df['DATE'] = pd.to_datetime(df.DATE)
    #timedelta here instead of pd.DateOffset to avoid pandas bug < 0.18 (Pandas issue #11925)
    df['left'] = df.DATE - datetime.timedelta(days=0.5)
    df['right'] = df.DATE + datetime.timedelta(days=0.5)
    df = df.set_index(['DATE'])
    df.sort_index(inplace=True)
    if distribution == 'Smoothed':
        window, order = 51, 3
        for key in STATISTICS:
            df[key] = savgol_filter(df[key], window, order)

    return ColumnDataSource(data=df)

def make_plot(source, title):
    plot = figure(x_axis_type="datetime", width=800, tools="", toolbar_location=None)
    
    plot.title.text = title

    plot.quad(top='record_max_temp', bottom='record_min_temp', left='left', right='right',
              color=Blues4[2], source=source, legend_label="Record")
    plot.quad(top='average_max_temp', bottom='average_min_temp', left='left', right='right',
              color=Blues4[1], source=source, legend_label="Average")
    plot.quad(top='actual_high', bottom='actual_low', left='left', right='right',
              color=Blues4[0], alpha=0.5, line_color="black", source=source, legend_label="Actual")

    # fixed attributes
    plot.xaxis.axis_label = None
    plot.yaxis.axis_label = "Temperature (C)"
    plot.axis.axis_label_text_font_style = "bold"
    plot.grid.grid_line_alpha = 0.3
    
    # Set x-axis range for the selected year
    start_date = pd.Timestamp(f'{year}-01-01')
    end_date = pd.Timestamp(f'{year}-12-31')
    plot.x_range = Range1d(start=start_date, end=end_date)

    return plot

def update_plot(attrname, old, new):
    city = city_select.value
    year = year_select.value
    plot.title.text = "Weather data for " + cities[city]['title'] + " " + year

    src = get_dataset(df, cities[city]['ID'], distribution_select.value)
    source.data.update()


    start_date = pd.Timestamp(f'{year}-01-01')
    end_date = pd.Timestamp(f'{year}-12-31')
    plot.x_range.start = start_date
    plot.x_range.end = end_date


city = 'Chicago'
distribution = 'Discrete'
year = '1981'

cities = {
  'Chicago':
        {'ID': 'USW00094846',
        'title': 'CHICAGO'
        },
    'Miami':
        {'ID': 'USW00012839',
        'title': 'MIAMI'
        },
     'Los Angeles':
        {'ID': 'USW00023174',
        'title': 'LOS ANGELES'
        },
    'New York':
        {'ID': 'USW00094789', 
         'title': 'NEW YORK'
         },
    'Houston':
        {'ID': 'USW00012960', 
        'title': 'HOUSTON'
        },
    }


df = pd.read_csv('./combined_stations.csv') #locally saved csv
source = get_dataset(df, cities[city]['ID'], distribution)
plot = make_plot(source, f"Weather data for {cities[city]['title']} in {year}")

# Dropdowns
city_select = Select(value=city, title='City', options=sorted(cities.keys()))
year_select = Select(value=year, title='Year', options=[str(i) for i in range(1981, 2024)])
distribution_select = Select(value=distribution, title='Distribution', options=['Discrete', 'Smoothed'])


distribution = distribution_select.value
city = city_select.value
year = year_select.value

#onchange
city_select.on_change('value', update_plot)
year_select.on_change('value', update_plot)
distribution_select.on_change('value', update_plot)


# Layout of the controls and plot
inputs = column(city_select, year_select, distribution_select)
layout = row(plot, inputs)

curdoc().add_root(row(layout))
curdoc().title = "Dropdown"


