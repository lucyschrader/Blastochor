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
            # Checks if the record's rows need to point to another record
            pointers = record.structure.get(self.label).get("pointers")

            if not config.get("quiet"):
                print("{r} has pointers: {p}".format(r=record.pid, p=pointers))

            if len(pointers) > 0:
                for pointer in pointers:
                    self.chop_up_record(record, pointer)
            else:
                self.chop_up_record(record)
                
            stats.file_write_counts[self.label] += 1
            
        for output_row in self.rows:
            processor.FieldProcessor(self.rules, output_row)

    def chop_up_record(self, record=None, pointer=None):
        kwargs = {}
        kwargs["data"] = None
        kwargs["pointer"] = pointer
        kwargs["rules"] = self.rules
        kwargs["record_pid"] = record.pid
        kwargs["explode_ordinal"] = None
        kwargs["group_role"] = None

        # Cuts down the record to a subset if needed
        if self.reduce_on:
            reduce_path = self.reduce_on.split(".")
            data = processor.step_to_field(record.data, reduce_path)
        else:
            data = record.data

        # Checks if the record explodes at the same level it's reduced to
        explode_reduce = False
        if self.reduce_on == self.explode_on:
            explode_reduce = True

        # Runs if the record should be checked for multiple rows
        if self.explode_on:
            # Works out how many rows should be written
            if explode_reduce == False:
                explode_data = processor.step_to_field(data, self.explode_on)
                if explode_data:
                    explode_size = len(explode_data)
                else:
                    return None
            else:
                explode_size = len(data)

            # Runs if there are multiple rows to write out
            if explode_size > 1:
                # Runs if multiple rows should be grouped with a parent row
                if config.get("group_rows"):
                    if explode_reduce == True:
                        kwargs["data"] = data[0]
                    else:
                        kwargs["data"] = data
                    kwargs["group_role"] = "parent"
                    kwargs["explode_ordinal"] = 0
                    # Writes parent row
                    self.rows.append(OutputRow(**kwargs))
                    for i in range(0, explode_size):
                        if explode_reduce == True:
                            kwargs["data"] = data[i]
                        else:
                            kwargs["data"] = data
                        kwargs["group_role"] = "child"
                        kwargs["explode_ordinal"] = i
                        # Writes each child row
                        self.rows.append(OutputRow(**kwargs))
                # Runs if multiple rows don't need to be grouped
                else:
                    for i in range(0, explode_size):
                        if explode_reduce == True:
                            kwargs["data"] = data[i]
                        else:
                            kwargs["data"] = data
                        kwargs["group_role"] = None
                        kwargs["explode_ordinal"] = i
                        self.rows.append(OutputRow(**kwargs))
            # Runs if there is only one row needed
            else:
                kwargs["data"] = data
                kwargs["group_role"] = None
                kwargs["explode_ordinal"] = None
                self.rows.append(OutputRow(**kwargs))
        # Runs if the record isn't being exploded
        else:
            kwargs["data"] = data
            kwargs["group_role"] = None
            kwargs["explode_ordinal"] = None
            self.rows.append(OutputRow(**kwargs))

class OutputRow():
    def __init__(self, data=None, pointer=None, explode_on=None, explode_ordinal=None, explode_parent_value=None, group_role=None, explode_child_fields=None, explode_parent_fields=None, rules=None, record_pid=None):
        self.data = data
        self.pointer = pointer
        self.explode_on = explode_on
        self.explode_ordinal = explode_ordinal
        self.explode_parent_value = explode_parent_value
        self.group_role = group_role
        self.explode_child_fields = explode_child_fields
        self.explode_parent_fields = explode_parent_fields
        self.rules = rules
        self.record_pid = record_pid

        self.values = {}