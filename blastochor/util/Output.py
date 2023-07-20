# -*- coding: utf-8 -*-

from tqdm import tqdm

from blastochor.settings.Settings import config
from blastochor.settings.Stats import stats
import blastochor.util.Processor as processor
from blastochor.util.Records import records
from blastochor.util import Writer

class Output():
    def __init__(self, label=None, endpoint=None, reference_column=None, explode_on=None, reduce_on=None, requires=None, fieldnames=None, rules=None):
        self.label = label
        self.endpoint = endpoint
        self.reference_column = reference_column
        self.explode_on = explode_on
        self.reduce_on = reduce_on
        self.requires = requires
        self.fieldnames = fieldnames
        self.rules = rules

        self.rows = []

        if not config.get("quiet"):
            print("{} output object created".format(self.label))

    def write_to_csv(self):
        print("Writing {} file".format(self.label))
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
        output_record_pids = [i for i in config["record_memo"] if self.label in config["record_memo"][i]["write_to"]]

        if not config.get("quiet"):
            print("Writing {} records to file".format(len(list(output_record_pids))))

        for record_pid in output_record_pids:
            record = records.records[record_pid]
            # Checks if the record's rows need to point to another record
            pointers = config["record_memo"][record_pid]["structure"][self.label]["extends"]

            if len(pointers) > 0:
                if not config.get("quiet"):
                    print("{r} has pointers: {p}".format(r=record_pid, p=pointers))

                for pointer in pointers:
                    self.chop_up_record(record, pointer)
            else:
                self.chop_up_record(record)

        print("Processing values")

        for output_row in tqdm(self.rows, desc="Working: "):
            processor.RowProcessor(self.rules, output_row)

    def chop_up_record(self, record=None, pointer=None):
        kwargs = {}
        kwargs["data"] = None
        kwargs["pointer"] = pointer
        kwargs["rules"] = self.rules
        kwargs["record_pid"] = record.pid
        kwargs["explode_on"] = self.explode_on
        kwargs["explode_ordinal"] = None
        kwargs["requires"] = self.requires
        kwargs["group_role"] = None

        # Removes images not being written out if only some selected
        if config.get("mode") == "list":
            memo_record = config["record_memo"][record.pid]
            if memo_record:
                # TODO: Check if record has no images and raise error if not
                if len(memo_record.media_irns) < len(record.data.get("hasRepresentation")):
                    record.data = self.remove_nonwriting_images(memo_record, record.data)

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

        # Checks if the record (or reduced record) includes any data
        if data:

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
                    if explode_reduce == True:
                        kwargs["data"] = data[0]
                    else:
                        kwargs["data"] = data
                    kwargs["group_role"] = None
                    kwargs["explode_ordinal"] = 0
                    self.rows.append(OutputRow(**kwargs))

            # Runs if the record isn't being exploded
            else:
                kwargs["data"] = data
                kwargs["group_role"] = None
                kwargs["explode_ordinal"] = None
                self.rows.append(OutputRow(**kwargs))

        else:
            if not config.get("quiet"):
                print("Record {p} has no data for {l} output".format(p=record.pid, l=self.label))

    def remove_nonwriting_images(self, memo_record, record_data):
        # When only writing out specific images, remove any other images from the source data
        has_rep_section = record_data.get("hasRepresentation")

        new_has_rep_section = [sec for sec in has_rep_section if sec.get("id") in memo_record.media_irns]

        record_data["hasRepresentation"] = new_has_rep_section

        return record_data

class OutputRow():
    def __init__(self, data=None, pointer=None, explode_on=None, explode_ordinal=None, explode_parent_value=None, group_role=None, explode_child_fields=None, explode_parent_fields=None, requires=None, rules=None, record_pid=None):
        self.data = data
        self.pointer = pointer
        self.explode_on = explode_on
        self.explode_ordinal = explode_ordinal
        self.explode_parent_value = explode_parent_value
        self.group_role = group_role
        self.explode_child_fields = explode_child_fields
        self.explode_parent_fields = explode_parent_fields
        self.requires = requires
        self.rules = rules
        self.record_pid = record_pid

        self.meets_requirement = None

        self.values = {}