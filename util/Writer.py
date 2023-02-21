-# -*- coding: utf-8 -*-

import csv
from Blastochor import app

class OutputCSV():
	def __init__(self, label):
		self.label = label
		self.filename = self.generate_filename()

		self.file = open(self.filename, "w", newline="", encoding="utf-8")
		self.writer = csv.writer(self.file, delimiter=",")

	def generate_filename(self):
		pass

	def write_header_row(self, fieldnames):
		self.writer.writerow(fieldnames)

	def write_records(self, output_records, fieldnames):
		for record in output_records:
			row = []
			if record.points_to is not None:
				row.append(record.points_to)
			for field in fieldnames:
				value = record.values.get(field)
				# If a value is still a list after processing, turn it into a string
				if isinstance(value, list):
					value = " | ".join(value)
				if value == None:
					value = ""
				row.append(value)

			self.writer.writerow(row)