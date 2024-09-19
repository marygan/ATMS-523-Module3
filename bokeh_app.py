# %%
import pandas  as pd

# %%
stn_ids = pd.read_fwf('http://noaa-ghcn-pds.s3.amazonaws.com/ghcnd-stations.txt', header=None, infer_nrows=1000)
stn_ids.columns = ['ID','LAT','LON','ELEV','UKN','NAME','GSN','WBAN']
stn_ids

# %%
#pick 5 cities and pull station IDs
def city_station(city):
    # function to sort through stn ids for city name so that it can be searched in next bit of code which only pulls by station for elements
    stn = stn_ids[stn_ids['NAME'].str.contains(city, na=False)]
    return stn[['ID', 'NAME']]



# %%
def get_available_years(station_id):
    df = pd.read_csv(
        "s3://noaa-ghcn-pds/csv/by_station/" + station_id + ".csv",
        storage_options={"anon": True},
        parse_dates=['DATE']
    )
    print(df['DATE'].dt.year.unique())  # Returns the unique years presen

# %%
#pull city station info into list based on airport data

city_airports= ['CHICAGO OHARE INTL AP','MIAMI INTL AP','LOS ANGELES INTL AP','JFK INTL AP','HOUSTON INTERCONTINENTAL AP']
station_ids = []

for airport in city_airports:
    station_info = city_station(airport)
    station_ids.append(station_info)


station_ids_df = pd.concat(station_ids, ignore_index=True)

station_ids_df['NAME'] = station_ids_df['NAME'].replace({'CHICAGO OHARE INTL AP':'Chicago','MIAMI INTL AP':'Miami','LOS ANGELES INTL AP': "Los Angeles",'JFK INTL AP': 'New York City','HOUSTON INTERCONTINENTAL AP':'Houston'})
station_ids_df

# %%
# set date range
import datetime

time_start = '1981-01-01'
time_end = datetime.datetime.now().strftime('%Y-%m-%d')


# %%
def station_data_values(station_id, time_start, time_end):
    #reads in data
    df = (
    pd.read_csv(
        "s3://noaa-ghcn-pds/csv/by_station/" + station_id + ".csv",
        storage_options={"anon": True},  # Anonymous access to S3
        dtype={'Q_FLAG': 'object', 'M_FLAG': 'object'},  # Define data types
        parse_dates=['DATE']  # Parse the 'DATE' column as datetime
    )
    .set_index('DATE')  # Set 'DATE' as the DataFrame index
    .sort_index()  
)
    df_range = df.loc[time_start:time_end]

     #find max tmax and min tmin
    df_tmax = df_range.loc[df_range['ELEMENT'] == 'TMAX', 'DATA_VALUE'] /10
    df_tmin = df_range.loc[df_range['ELEMENT'] == 'TMIN', 'DATA_VALUE'] /10
   
    #annual mean min temp
    ser=df_tmin[~((df_tmin.index.month==2)&(df_tmin.index.day==29))]
    tmin_mean =ser.groupby(ser.index.day_of_year).mean()
    ser2=df_tmax[~((df_tmax.index.month==2)&(df_tmax.index.day==29))]
    tmax_mean=ser2.groupby(ser2.index.day_of_year).mean()

    #record min
    record_tmin = ser.groupby(ser.index.day_of_year).min()
    record_tmax = ser2.groupby(ser2.index.day_of_year).max()  
    
    #create pandas df of all values

    df_grouped = pd.DataFrame(
        {'record_min_temp': record_tmin, 'average_min_temp': tmin_mean, 'average_max_temp': tmax_mean,'record_max_temp':record_tmax},
    )

    df_actual = pd.DataFrame(
        {'actual_low':df_tmin, 'actual_high': df_tmax}
    )

    df_actual['day_of_year'] = df_actual.index.day_of_year

    df_merged = pd.merge(df_actual, df_grouped, left_on='day_of_year', right_index=True, how='left')
    df_merged.drop('day_of_year', axis=1, inplace=True)
    
    return df_merged


# %%
#output and example
station_data_values('USW00094846', time_start, time_end)

# %%
stations_data = []

for station_id in station_ids_df['ID']:
    station_data = station_data_values(station_id,time_start,time_end)
    station_data['ID'] = station_id
    stations_data.append(station_data)

combined_stations_df = pd.concat(stations_data, ignore_index=False)


# %%
#combined_stations_df.to_csv("combined_stations.csv")

# %%

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

def get_dataset(src, name, distribution):
    df = src[src['ID'] == name].copy()
    del df['ID']
    df.index = pd.to_datetime(df.index)  # in this DF date is index
    df['left'] = df.index - pd.Timedelta(days=0.5)
    df['right'] = df.index + pd.Timedelta(days=0.5)

    # Sort the dataframe based on the datetime index
    df.sort_index(inplace=True)
    #keeping smoothing
    if distribution == 'Smoothed':
        window, order = 51, 3
        for key in STATISTICS:
            df[key] = savgol_filter(df[key], window, order)

    # Return the dataframe as a Bokeh ColumnDataSource
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


    plot.xaxis.axis_label = None
    plot.yaxis.axis_label = "Temperature (C)"
    plot.axis.axis_label_text_font_style = "bold"
    plot.grid.grid_line_alpha = 0.3
    
    # Set x-axis range for the selected year
    start_date = pd.Timestamp(f'{year}-01-01')
    end_date = pd.Timestamp(f'{year}-12-31')
    plot.x_range = Range1d(start=start_date, end=end_date) #set range of plot so that it zooms in on year

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


df = combined_stations_df
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


