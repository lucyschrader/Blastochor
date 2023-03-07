# -*- coding: utf-8 -*-

import csv
#from datetime import datetime
from blastochor.settings.Settings import config

class OutputCSV():
	def __init__(self, label):
		self.label = label
		self.filename = self.generate_filename()

		self.file = open(self.filename, "w", newline="", encoding="utf-8")
		self.writer = csv.writer(self.file, delimiter=",")

	def generate_filename(self):
		#current_time = datetime.now.strftime("%d-%m-%Y_%H-%M")
		#name = "{t}-{l}-export.csv".format(t=current_time, l=self.label)
		name = "{}-export.csv".format(self.label)
		path = "{}/".format(config.get("output_dir"))
		return path + name

	def write_header_row(self, fieldnames):
		self.writer.writerow(fieldnames)

	def write_records(self, output_records, fieldnames):
		for record in output_records:
			row = []
			if record.pointer:
				row.append(record.pointer)
			for field in fieldnames:
				value = record.values.get(field)
				# If a value is still a list after processing, turn it into a string
				if isinstance(value, list):
					value = [str(i) for i in value if i is not None]
					if len(value) == 1:
						value = value[0]
					elif len(value) > 1:
						value = " | ".join(value)
					else:
						value = None
				if value == None:
					value = ""
				row.append(value)

			self.writer.writerow(row)