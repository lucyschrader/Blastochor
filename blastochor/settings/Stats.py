# -*- coding: utf-8 -*-

from datetime import datetime
from math import floor
from blastochor.settings.Settings import config

class AppStats():
	def __init__(self):
		self.start_time = None
		self.end_harvest_time = None
		self.end_extrarecords_time = None
		self.harvest_time = None
		self.extrarecords_time = None
		self.processing_time = None
		self.run_time = None
		self.api_call_count = 0
		self.search_result_count = 0
		self.list_count = 0
		self.extension_records_count = 0
		self.file_write_counts = {}
		self.quality_score_lower = None
		self.quality_score_upper = None

	def start(self):
		self.start_time = datetime.now()

	def end_harvest(self):
		self.end_harvest_time = datetime.now()

	def end_extrarecords(self):
		self.end_extrarecords_time = datetime.now()

	def end(self):
		end_time = datetime.now()

		# Record how long script took to run in total
		delta = end_time - self.start_time
		self.run_time = self.datetime_to_string(delta.total_seconds())

		# Record how long script took to perform initial harvest
		delta = self.end_harvest_time - self.start_time
		self.harvest_time = self.datetime_to_string(delta.total_seconds())

		# Record how long script took to perform extra queries
		delta = self.end_extrarecords_time - self.end_harvest_time
		self.extrarecords_time = self.datetime_to_string(delta.total_seconds())

		# Record how long script took to perform processing
		delta = end_time - self.end_extrarecords_time
		self.processing_time = self.datetime_to_string(delta.total_seconds())

	def datetime_to_string(self, seconds):
		if seconds > 3600:
			hours = seconds // 3600
			minutes = (seconds // 60) % 60
			return "{h} hours and {m} minutes".format(h=floor(hours), m=floor(minutes))
		elif seconds > 60:
			minutes = seconds // 60
			seconds = seconds - (minutes * 60)
			return "{m} minutes and {s} seconds".format(m=floor(minutes), s=floor(seconds))
		else:
			return "{} seconds".format(round(seconds))

	def print_stats(self):
		print("Script ran in {}".format(self.run_time))
		print("Script made {} API calls".format(self.api_call_count))

		if config.get("mode") == "search" or (config.get("mode") == "scroll"):
			print("Search returned {} results".format(self.search_result_count))
		elif config.get("mode") == "list":
			print("Source list contained {} records".format(self.list_count))
		print("Harvesting ran in {}".format(self.harvest_time))

		print("Queried {} extension records".format(self.extension_records_count))
		print("Getting extra records took {}".format(self.extrarecords_time))

		print("Processing records took {}".format(self.processing_time))

		for label in self.file_write_counts.keys():
			print("Wrote {n} records to the {l} file".format(n=self.file_write_counts.get(label), l=label))

class ProgressBar():
	def __init__(self, length=1):
		self.length = length
		self.width = 50
		print("[", " " * self.width, "]", sep="", end="", flush=True)

	def update(self, count):
		progress_percentage = floor((count / self.length) * 100)

		if progress_percentage % 1 == 0:
			left = self.width * progress_percentage // 100
			right = self.width - left

			tags = "#" * left
			spaces = " " * right
			percents = "{:.0f}%".format(progress_percentage)

			print("\r[", tags, spaces, "] ", percents, sep="", end="", flush=True)

		if progress_percentage == 100:
			print("")

stats = AppStats()