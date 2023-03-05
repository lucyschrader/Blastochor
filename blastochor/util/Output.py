# -*- coding: utf-8 -*-

from blastochor.settings.Settings import config
import blastochor.util.Processor as processor
from blastochor.util.Records import records
from blastochor.util import Writer

class Output():
    def __init__(self, label=None, explode_on=None, reduce_on=None, fieldnames=None, rules=None):
        self.label = label
        self.explode_on = explode_on
        self.reduce_on = reduce_on
        self.fieldnames = fieldnames
        self.rules = rules

        self.rows = []

        if not config.get("quiet"):
            print("{} output object created".format(self.label))

    def write_to_csv(self):
        csv = Writer.OutputCSV(self.label)

        csv.write_header_row(self.fieldnames)

        self.create_rows()

        csv.write_records(self.rows, self.fieldnames)

    def create_rows(self):
        # Processes each included record to get printable values
        # Appends to self.rows list before writing all records
#        output_records = filter(lambda record: record.structure.get(self.label).get("write") == True, records.records)
        output_records = []
        for record in records.records:
            if record.structure.get(self.label).get("write") == True:
                output_records.append(record)
#        output_records = records.records
        if not config.get("quiet"):
            print("Writing {} records to file".format(len(list(output_records))))
        for record in output_records:
            if self.reduce_on:
                reduce_path = self.reduce_on.split(".")
                data = processor.step_to_field(record.data, reduce_path)
            else:
                data = record.data
            
            pointers = record.structure.get(self.label).get("pointers")
            
            if len(pointers) > 0:
                for pointer in pointers:
                    if self.explode_on:
                        explode_size = len(processor.step_to_field(data, self.explode_on))
                        for i in explode_size:
                            self.rows.append(OutputRow(data=data, pointer=pointer, explode_ordinal=i, rules=self.rules))
                    else:
                        self.rows.append(OutputRow(data=data, pointer=pointer, rules=self.rules))
            else:
                if self.explode_on:
                    explode_size = len(processor.step_to_field(data, self.explode_on))
                    for i in explode_size:
                        self.rows.append(OutputRow(data=data, explode_ordinal=i, rules=self.rules))
                else:
                    self.rows.append(OutputRow(data=data, rules=self.rules))

class OutputRow():
    def __init__(self, data=None, pointer=None, explode_ordinal=None, rules=None):
        self.data = data
        self.pointer = pointer
        self.explode_ordinal = explode_ordinal
        self.values = {}

        self.rules = rules

        self.populate_values()

    def populate_values(self):
        for rule in self.rules:
            key = rule.output_fieldname
            value = processor.FieldProcessor(data=self.data, rule=rule, explode_ordinal=self.explode_ordinal).value
            self.values.update({key: value})