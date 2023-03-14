# -*- coding: utf-8 -*-

from blastochor.settings.Settings import config, stats
import blastochor.util.Processor as processor
from blastochor.util.Records import records
from blastochor.util import Writer

class Output():
    def __init__(self, label=None, endpoint=None, reference_column=None, explode_on=None, reduce_on=None, fieldnames=None, rules=None):
        self.label = label
        self.endpoint = endpoint
        self.reference_column = reference_column
        self.explode_on = explode_on
        self.reduce_on = reduce_on
        self.fieldnames = fieldnames
        self.rules = rules

        self.rows = []

        if not config.get("quiet"):
            print("{} output object created".format(self.label))

    def write_to_csv(self):
        csv = Writer.OutputCSV(self.label)

        header_row = [i for i in self.fieldnames]
        if self.reference_column:
            header_row.insert(0, self.reference_column)
        csv.write_header_row(header_row)

        self.create_rows()

        csv.write_records(self.rows, self.fieldnames)

    def create_rows(self):
        # Processes each included record to get printable values
        # Appends to self.rows list before writing all records
        output_records = []
        for record in records.records:
            if record.structure.get(self.label).get("write") == True:
                output_records.append(record)

        if not config.get("quiet"):
            print("Writing {} records to file".format(len(list(output_records))))

        for record in output_records:
            if self.reduce_on:
                reduce_path = self.reduce_on.split(".")
                data = processor.step_to_field(record.data, reduce_path)
            else:
                data = record.data
            
            pointers = record.structure.get(self.label).get("pointers")

            if not config.get("quiet"):
                print("{r} has pointers: {p}".format(r=record.pid, p=pointers))

            if len(pointers) > 0:
                for pointer in pointers:
                    self.check_explode(data=data, pointer=pointer, parent_pid=record.pid)
            else:
                self.check_explode(data=data, pointer=None, parent_pid=record.pid)

    def check_explode(self, data, pointer, parent_pid):
        if self.explode_on:
            if self.reduce_on == self.explode_on:
                explode_size = len(data)
                if explode_size > 1:
                    for i in range(0, explode_size-1):
                        this_data = data[i]
                        self.rows.append(OutputRow(data=this_data, pointer=pointer, explode_ordinal=i, rules=self.rules, parent_pid=parent_pid))
                        stats.file_write_counts[self.label] += 1
                else:
                    this_data = data[0]
                    self.rows.append(OutputRow(data=this_data, pointer=pointer, explode_ordinal=0, rules=self.rules, parent_pid=parent_pid))
                    stats.file_write_counts[self.label] += 1
            else:
                explode_data = processor.step_to_field(data, self.explode_on)
                if explode_data:
                    explode_size = len(explode_data)
                    if explode_size > 1:
                        for i in range(0, explode_size-1):
                            self.rows.append(OutputRow(data=data, pointer=pointer, explode_on=self.explode_on, explode_ordinal=i, rules=self.rules, parent_pid=parent_pid))
                            stats.file_write_counts[self.label] += 1
                    else:
                         self.rows.append(OutputRow(data=data, pointer=pointer, explode_on=self.explode_on, explode_ordinal=0, rules=self.rules, parent_pid=parent_pid))
                         stats.file_write_counts[self.label] += 1
        else:
            self.rows.append(OutputRow(data=data, pointer=pointer, rules=self.rules, parent_pid=parent_pid))
            stats.file_write_counts[self.label] += 1

class OutputRow():
    def __init__(self, data=None, pointer=None, explode_on=None, explode_ordinal=None, rules=None, parent_pid=None):
        self.data = data
        self.pointer = pointer
        self.parent_pid = parent_pid
        self.explode_on = explode_on
        self.explode_ordinal = explode_ordinal
        self.values = {}

        self.rules = rules

        self.populate_values()

    def populate_values(self):
        for rule in self.rules:
            key = rule.output_fieldname
            value = processor.FieldProcessor(data=self.data, rule=rule, explode_on=self.explode_on, explode_ordinal=self.explode_ordinal, parent_pid=self.parent_pid).value
            self.values.update({key: value})