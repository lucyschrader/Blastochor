# -*- coding: utf-8 -*-

from tqdm import tqdm

from blastochor.settings.Settings import config
from blastochor.settings.Stats import stats
import blastochor.util.Processor as processor
from blastochor.util.Records import records
from blastochor.util import Writer

class RelationshipOutput():
	def __init__(self, label=None, fieldnames=None):
		self.label = label
		self.fieldnames = fieldnames
		self.relationship_sets = []

		if not config.get("quiet"):
			print("Relationship output created")

	def write_to_csv(self):
		print("Writing relationship file")
		csv = Writer.OutputCSV(self.label)

		csv.write_header_row(self.fieldnames)

		for r_set in self.relationship_sets:
			csv.write_records(r_set.rows, self.fieldnames)

class RelationshipSet():
	def __init__(self, object_label=None, subject_label=None, relationship_rule=None, rules=None):
		self.object_label = object_label
		self.subject_label = subject_label
		self.relationship_rule = relationship_rule
		self.rules = rules
		self.rows = []

	def create_relationship_function(self):
		object_rule = self.relationship_rule["object"]
		object_field = object_rule["field"]
		object_modifier = object_rule.get("trim") # Or other?
		operator = self.relationship_rule["operator"]
		subject_rule = self.relationship_rule["subject"]
		subject_field = subject_rule["field"]
		subject_modifier = subject_rule.get("trim")

	def find_related_items(self):
		object_records = []
		for record in records.records:
			if record.structure.get(self.object_label).get("write") == True:
				object_records.append(record)

		for record in object_records:
			if self.operator == "equals":
				related_records = [related_record for related_record in records.records if (self.modify_value(value=related_record.get(subject_field), modifier=self.subject_modifier) == self.modify_value(value=record.get(object_field), modifier=self.object_modifier)) and (related_record.structure.get(self.subject_label).get("write") == True)]
				for rel_record in related_records:
					ordinal = 0
					if rel_record["id"] == record["id"]:
						pass
					else:
						self.rows.append(RelationshipRow(object_data=record, subject_data=rel_record, rules=self.rules, ordinal=ordinal))
						ordinal += 1

	def modify_value(self, value, modifier):
		if modifier:
			# Assumes modifier is trim
			trim_end = lambda modifier: str(modifier)[0] == '-' and len(str(modifier)) > 1
			if trim_end == True:
				return value[:modifier]
			else:
				return value[modifier:-1]
		else:
			return value

class RelationshipRow():
	def __init__(self, object_data, subject_data, rules, ordinal):
		self.object_data = object_data
		self.object_pid = self.object_data["pid"]
		self.subject_data = subject_data
		self.subject_pid = self.subject_data["pid"]
		self.rules = rules
		self.ordinal = ordinal

		self.values = {}