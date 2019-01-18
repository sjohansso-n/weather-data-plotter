"""
Weather app downloading and plotting weather data from 
SMHI, Swedens Meteorological and Hydrological Institute. 
Current parameters is air temperature and relative 
air humidity collected over the past four months. 
"""

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import matplotlib.pyplot as plt
from matplotlib import rcParams
import plotly.graph_objs as go
from matplotlib import pylab
import seaborn as sns
import pandas as pd
import settings
import random
import plotly
import sys
import re

DIRECTORY = settings.DIRECTORY
WEATHER_STATIONS_FILE = settings.DATA_LOOKUP_FILE
PARAMS = settings.PARAMS
INDEX = settings.INDEX

class DataHandler():

	def __init__(self, station):
		self.stations_df = pd.read_csv(WEATHER_STATIONS_FILE, sep=';')
		self.station = station.lower()
		self.station_id = 0
		self.params = [param for param_num, param in PARAMS]
		self.param_nums = [param_num for param_num, param in PARAMS]
		self.index = INDEX

	def __str__(self):
		return f'Data from { self.station.capitalize() } with id {self.station_id}.'

	def check_id(self):
		"""
		Checks if the user provided station/city name is 
		to be found in the STATIONS_FILE and, if so, assigns 
		the matching id to self.station_id.
		"""
		try:
			# Checks for complete lowercase match 
			self.station_id = self.stations_df['Id'][self.stations_df['Namn'].apply(lambda name: str(name).lower())==self.station].iloc[0]
			return True
		except:
			try:
				# Checks if there is a station name that begins with the user provided name.
				# The first match if there are several.
				self.station_id = self.stations_df['Id'][self.stations_df['Namn'].apply(lambda name: str(name).lower().startswith(self.station))].iloc[0]
				return True
			except:
				print('The station was not found. Are you sure you spelled it correctly?')
				return False

	def download_data(self, param_num):
		"""
		Downloads data for the past four months and saves to 
		csv file.
		"""
		url = f'https://opendata-download-metobs.smhi.se/api/version/latest/parameter/{ param_num }/station/{ self.station_id }/period/latest-months/data.csv'
		try:
			response = urlopen(Request(url))
			with open(f'{ self.station_id }_{ param_num }_data_file.csv', 'wb') as f:
				f.write(response.read())
		except:
			print("Couldn't download data.")		

	def clean_file(self, param_num):
		"""
		Removes unnecessary rows and columns from the data file.
		"""
		df = pd.read_csv(f'{ self.station_id }_{ param_num }_data_file.csv', header=7, sep=';', usecols=[0,1,2,3])
		print(df.head())
		if df.columns.values[0] != 'Datum':
			df = pd.read_csv(f'{ self.station_id }_{ param_num }_data_file.csv', header=6, sep=';', usecols=[0,1,2,3])
		df.to_csv(f'{ self.station_id }_{ param_num }_data_file.csv')

	def merge_files(self):
		"""
		Merges the csv files for all parameters and saves to a 
		new file with station specific name.
		"""
		file_list = list(map(lambda param_num: pd.read_csv(f'{ self.station_id }_{ param_num }_data_file.csv', index_col=0), self.param_nums))
		file1 = file_list[0]
		for file2 in file_list[1:]:
			file1 = pd.merge(file1, file2)
		file1.to_csv(f'{ self.station_id }_data_file.csv', index=False)

	def change_dtype(self):
		"""
		Changes the data type of the date index from string 
		to datetime and changes the data type for all parameter 
		columns from string to numeric.
		"""
		df = pd.read_csv(f'{ self.station_id }_data_file.csv')
		df[self.index[0]] = pd.to_datetime(df[self.index[0]])
		for param in self.params:
			df[param] = pd.to_numeric(df[param])
		df.to_csv(f'{ self.station_id }_data_file.csv')


class DataPlotter():

	def __init__(self, file, station, param):
		self.df = pd.read_csv(file, index_col=0)
		self.station = station
		self.param = param
		self.param_name = param.replace(' ', '_')
		self.params = [param for param_num, param in PARAMS]
		self.index = INDEX
		sns.set(rc={'figure.figsize':(12,4)})
		rcParams['figure.figsize'] = 12,4

	def __str__(self):
		pass

	def set_multiindex(self):
		"""
		Changes the index of the dataframe to a multiindex 
		with the columns in self.index as index levels. 
		Currently date is set as outer index and time as 
		inner index.
		"""
		self.df.set_index(self.index, inplace=True)

	def gen_hours(self):
		"""
		Removes minutes and seconds from the time string 
		and returns a list of the hours.
		"""
		return list(map(lambda time: time.split(':')[0], self.df.index.levels[1]))

	def gen_days(self):
		"""
		Removes time from datetime object.
		"""
		return list(map(lambda date: str(date).split(' ')[0], self.df.index.levels[0]))

	def sns_lineplot(self):
		"""
		Creates and saves a line plot of the mean per date 
		of the parameter over the whole time period.
		"""
		fig, ax = plt.subplots(figsize=(12,4))
		sns.lineplot(self.index[0], self.param, data=self.df.reset_index())
		plt.xticks(range(0, self.df[self.index[0]].nunique(), 4), self.df[self.index[0]].unique()[::4])
		pylab.xticks(rotation=45)
		plt.savefig(f'{ DIRECTORY }snslineplot_{ self.param_name }.png', bbox_inches='tight')
		plt.clf()

	def pd_lineplot(self):
		"""
		Creates and saves a line plot of the parameter 
		measurements from the last five days. Each day has 
		its own curve.
		"""
		fig = plt.figure()
		ax = fig.add_axes([0,0,1,1])
		ax.plot(self.df.iloc[-121:][self.param].unstack(level=0))
		hours = self.gen_hours()
		plt.xticks(range(len(self.df.index.levels[1])), hours)
		plt.savefig(f'{ DIRECTORY }pdlineplot_{ self.param_name }.png', bbox_inches='tight')
		plt.clf()

	def pd_plot_mean_date(self):
		"""
		Creates and saves a line plot of the mean per date 
		of the parameter over the whole time period.
		"""
		self.df[self.param].unstack(level=0).mean().plot()
		plt.savefig(f'{ DIRECTORY }pdplotmean_{ self.param_name }.png', bbox_inches='tight')
		plt.clf()

	def pd_plot_mean_hour(self):
		"""
		Creates and saves a line plot of the mean per hour 
		value of the parameter over the whole time period.
		"""
		self.df[self.param].unstack(level=1).mean().plot()
		hours = self.gen_hours()
		plt.xticks(range(len(self.df.index.levels[1])), hours)
		plt.savefig(f'{ DIRECTORY }pdplotmeanhour_{ self.param_name }.png', bbox_inches='tight')
		plt.clf()

	def sns_heatmap(self):
		"""
		Creates and saves a heatmap comparing dates and  
		time of day values of the parameter over the whole 
		time period.
		"""
		df3 = self.df.pivot_table(index=self.index[0], columns=self.index[1], values=self.param)
		fig, ax = plt.subplots(figsize=(20,20))
		hours = self.gen_hours()
		days = self.gen_days()
		sns.heatmap(df3,xticklabels=hours, yticklabels=days)
		plt.savefig(f'{ DIRECTORY }snsheatmap_{ self.param_name }.png', bbox_inches='tight')
		plt.clf()

	def sns_clustermap(self):
		"""
		Creates and saves a clustermap comparing dates and  
		time of day values of the parameter over the whole 
		time period.
		"""
		df3 = self.df.pivot_table(index=self.index[0], columns=self.index[1], values=self.param)
		hours = self.gen_hours()
		days = self.gen_days()
		sns.clustermap(df3.dropna(), cmap='viridis', figsize=(20,20), xticklabels=hours, yticklabels=days)
		plt.yticks(rotation=45)
		plt.savefig(f'{ DIRECTORY }snsclustermap_{ self.param_name }.png', bbox_inches='tight')
		plt.clf()

	def sns_jointplot(self):
		"""
		Creates and saves a jointplot comparing the 
		distribution of the (two first) parameters and how 
		they are related to each other.
		"""
		sns.jointplot(x=self.params[0], y=self.params[1], data=self.df)
		plt.savefig(f'{ DIRECTORY }snsjointplot.png', bbox_inches='tight')

	def sns_pairplot(self, hue=INDEX[1]):
		"""
		Creates and saves a pairplot comparing the 
		distribution of the parameters and how they 
		are related to each other. Default hue is time 
		of day.
		"""
		sns.pairplot(self.df.reset_index(), hue=hue)
		plt.savefig(f'{ DIRECTORY }snspairplot.png', bbox_inches='tight')

	def gen_color(self):
		"""
		Returns a random rgb color
		"""
		return f'rgb{ tuple(random.randint(0,255) for _ in range(3)) }'

	def plotly_plot(self):
		"""
		Creates and saves an interactive plotly plot 
		and saves it to an html file. It plots the values 
		of all parameters for the whole time period.
		"""
		colors = ['rgb(214,12,140)']
		if len(self.params) >= 2:
			colors.append('rgb(1,130,118)')
			if len(self.params) > 2:
				colors = colors + [self.gen_color() for _ in range(len(self.params))]

		# If there are 1 parameter or more than 2 there 
		# will only be one y-axis.
		if len(self.params) == 1 or len(self.params) > 2:
			data = []
			for param, color in list(zip(self.params, colors)):
				trace = go.Scatter(
						x = self.df.index.levels[0],
						y=self.df[param].unstack(level=0).mean(),
						marker=dict(
							color=color,
							),
						name=param
					)
				data.append(trace)

		# If there are 2 parameters there will be two y-axes.
		else:
			trace1 = go.Scatter(
					x = self.df.index.levels[0],
					y=self.df[self.params[0]].unstack(level=0).mean(),
					marker=dict(
						color=colors[0],
						),
					name=self.params[0]
				)
			trace2 = go.Scatter(
					x = self.df.index.levels[0],
					y=self.df[self.params[1]].unstack(level=0).mean(),
					marker=dict(
						color=colors[1],
						),
					yaxis='y2',
					name=self.params[1]
				)
			data = [trace1, trace2]
		layout = go.Layout(
			xaxis=dict(
				title=self.df.index.names[0],
			),
			yaxis=dict(
				title=self.params[0],
			),
			yaxis2=dict(
				title=self.params[1],
				overlaying='y',
				side='right',
			)
		)
		plotly.offline.plot({
			'data': data,
			'layout': layout,
		}, filename=f'{ DIRECTORY }{ self.station }_plot.html', auto_open=False)

def main(station):

	get = DataHandler(station)
	
	# Check if station exists
	if get.check_id():

		# Download data
		for param_num, param in PARAMS:
			get.download_data(param_num)
			get.clean_file(param_num)
		get.merge_files()
		get.change_dtype()

		file = f'{ get.station_id }_data_file.csv'

		# Plot data
		for param_num, param in PARAMS:
			data = DataPlotter(file, station, param)
			data.sns_lineplot()
			data.set_multiindex()
			data.pd_lineplot()
			data.pd_plot_mean_date()
			data.pd_plot_mean_hour()
			data.sns_heatmap()
			data.sns_clustermap()

		data.sns_jointplot()
		data.sns_pairplot()
		data.plotly_plot()

if __name__ == '__main__':
	try:
		station = sys.argv[1]
	except:
		print('Missing required argument. You must provide a city or weather station name.')
		sys.exit()
	main(station)





