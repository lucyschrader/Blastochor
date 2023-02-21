# -*- coding: utf-8 -*-

import json
from Blastochor import app

class Output():
    def __init__(self, label=None, explode=False, explode_path=None):
        self.label = label
        self.fieldnames = app.mapping.ordered_fieldnames.get(self.label)
        self.rules = app.mapping.mapping_rules.get(self.label)
        self.explode = explode
        self.explode_path = explode_path
        self.rows = []

        self.write_to_csv()

    def write_to_csv(self):
        csv = app.writer.OutputCSV(self.label)

        csv.write_header_row(self.fieldnames)

        self.create_rows()

        csv.write_records(self.rows, self.fieldnames)

    def create_rows(self):
        # Processes each included record to get printable values
        # Appends to self.rows list before writing all records
        records = filter(lambda record: self.label is in record.structure.keys(), app.records)
        for record in records:
            pointers = record.structure.get(self.label).get("pointers")
            if len(pointers) > 0:
                for pointer in pointers:
                    if self.explode == True:
                        explode_size = len(app.processor.step_to_field(record.data, self.explode_path))
                        for i in explode_size:
                            self.rows.append(OutputRow(data=record.data, pointer=pointer, explode_ordinal=i))
            else:
                if self.explode == True:
            for i in pointers:
                self.populate_row()
            if self.explode == True:
                explode_size = len(app.processor.step_to_field(record.data, self.explode_path))
                for i in explode_size:
                    self.rows.append(populate_row(record, i))
            else:
                self.rows.append(populate_row(record))

class Records():
    def __init__(self):
        self.records = []

    def find_record(self, endpoint, irn):
        # Find record with this endpoint, irn and return it
        this_record = filter(lambda record: record.endpoint == endpoint and record.irn = irn, self.records)[0]
        if this_record is not None:
            return this_record

        return None

class ApiRecord():
    def __init__(self, data, endpoint):
        self.data = data
        self.endpoint = endpoint
        self.structure = {}
        self.pid = self.data.get("pid")
        self.irn = self.data.get("id")

        for output in app.mapping.outputs:
            self.structure.update({output: {"write": False, "pointers": []}})

    def make_writable(self, label, bool):
        self.structure.get(label).update({"write": bool})

    def relate_record(self, label, related_record_pid)
        # Associates this record with another ApiRecord using its pid
        self.structure.get(label).get("pointers").append[related_record_pid]

class OutputRow():
    def __init__(self, data, pointer, explode_ordinal):
        self.data = data
        self.pointer = pointer
        self.explode_ordinal = explode_ordinal
        self.values = {}

        self.rules = app.mapping.mapping_rules.get(self.label)

        self.populate_values()

    def populate_values(self):
        for rule in self.rules:
            key = rule.output_fieldname
            value = app.processor.run_processing(record, rule, explode_ordinal)
            self.values.update({key: value})