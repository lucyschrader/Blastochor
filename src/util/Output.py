from src.setup.Settings import read_config, write_config
from src.monitoring.Stats import stats
from src.datastore.RecordStore import records
from src.datastore.Memo import memo
from src.util.Processor import RowProcessor
from src.util.ProcessingFunctions import collate_list, literal, step_to_field
from src.util.Writer import WriteFile
from tqdm import tqdm


class Output():
    def __init__(self, label=None, endpoint=None, fieldnames=None, reference_column=None,
                 rules=None, explode_on=None, reduce_on=None, requires=None):
        self.label = label
        self.endpoint = endpoint
        self.fieldnames = fieldnames
        self.reference_column = reference_column
        self.rules = rules
        self.explode_on = explode_on
        self.reduce_on = reduce_on
        self.requires = requires
        self.check_requirements = False

        stats.file_write_counts.update({label: 0})

        self.rows = []

        self.output_file = None

        if not read_config("quiet"):
            print("Prepping output for {} file".format(self.label))

    def write_output(self):
        self.output_file = self.create_output_file()
        self.prepare_header_row()
        self.prepare_output()
        self.output_file.write_rows(self.rows, self.fieldnames)

    def create_output_file(self):
        print("Writing {} file".format(self.label))
        return WriteFile(self.label)

    def prepare_header_row(self):
        header_row = [i for i in self.fieldnames]
        if self.reference_column:
            header_row.insert(0, self.reference_column)
        self.output_file.write_header_row(header_row)

    def prepare_output(self):
        if read_config("restrict_locality") and self.endpoint == "object":
            remove_restricted_localities()

        self.process_records_to_rows()

    def process_records_to_rows(self):
        # Processes each included record to get printable values
        # Appends to self.rows list before writing all records
        output_record_pids = [i for i in memo if self.label in memo[i]["write_to"]]

        if not read_config("quiet"):
            print("Writing {} records to file".format(len(list(output_record_pids))))

        for record_pid in output_record_pids:
            record = records.records.get(record_pid)
            if record:
                # Check if the record's rows need to point to another record
                pointers = memo[record_pid]["structure"][self.label]["extends"]
                if len(pointers) > 0:
                    if not read_config("quiet"):
                        print("{r} has pointers: {p}".format(r=record_pid, p=pointers))

                    for pointer in pointers:
                        self.chop_up_record(record=record, pointer=pointer)
                else:
                    self.chop_up_record(record=record)
            else:
                if not read_config("quiet"):
                    print("No record with pid {} found in saved records".format(record_pid))

        print("Processing values")

        for output_row in tqdm(self.rows, desc="Working: "):
            RowProcessor(self.rules, output_row, self.requires)

    def chop_up_record(self, record=None, pointer=None):
        kwargs = {"data": None,
                  "pointer": pointer,
                  "rules": self.rules,
                  "record_pid": record.pid,
                  "explode_on": self.explode_on,
                  "explode_ordinal": None,
                  "requires": self.requires,
                  "group_role": None}

        if self.reference_column:
            kwargs["write_pointer"] = True

        if read_config("mode") == "list":
            record = remove_nonwriting_images(record)

        # Cuts down the record to a subset if needed
        if self.reduce_on:
            reduce_path = self.reduce_on.split(".")
            data = step_to_field(record.data, reduce_path)
        else:
            data = record.data

        # Checks if the record explodes at the same level it's reduced to
        explode_reduce = False
        if self.reduce_on == self.explode_on:
            explode_reduce = True

        if data:
            # Runs if the record should be checked for multiple rows
            if self.explode_on:
                # Works out how many rows should be written
                if not explode_reduce:
                    explode_data = step_to_field(data, self.explode_on)
                    if explode_data:
                        explode_size = len(explode_data)
                    else:
                        return None
                else:
                    explode_size = len(data)

                # Runs if there are multiple rows to write out
                if explode_size > 1:
                    # Runs if multiple rows should be grouped with a parent row
                    if read_config("group_rows"):
                        if explode_reduce:
                            kwargs["data"] = data[0]
                        else:
                            kwargs["data"] = data
                        kwargs["group_role"] = "parent"
                        kwargs["explode_ordinal"] = 0
                        # Writes parent row
                        self.rows.append(OutputRow(**kwargs))
                        for i in range(0, explode_size):
                            if explode_reduce:
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
                            if explode_reduce:
                                kwargs["data"] = data[i]
                            else:
                                kwargs["data"] = data
                            kwargs["group_role"] = None
                            kwargs["explode_ordinal"] = i
                            self.rows.append(OutputRow(**kwargs))
                # Runs if there is only one row needed
                else:
                    if explode_reduce:
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
            if not read_config("quiet"):
                print("Record {p} has no data for {l} output".format(p=record.pid, l=self.label))

    def check_if_row_required(self, record_data):
        for requirement in self.requires:
            req_path = requirement["path"]
            req_value = requirement["value"]
            record_value = literal(data=record_data, path=req_path)
            if isinstance(req_value, bool):
                if req_value is True:
                    if not record_value:
                        return False
                elif req_value is False:
                    if record_value:
                        return False
            elif record_value != req_value:
                return False

        return True


class OutputRow():
    def __init__(self, **kwargs):
        self.data = kwargs.get("data")
        self.pointer = kwargs.get("pointer")
        self.write_pointer = kwargs.get("write_pointer")
        self.pid = kwargs.get("record_pid")
        self.explode = {"explode_on": kwargs.get("explode_on"),
                        "explode_ordinal": kwargs.get("explode_ordinal"),
                        "explode_parent_value": kwargs.get("explode_parent_value")}
        self.group_role = kwargs.get("group_role")

        self.rules = kwargs.get("rules")
        self.write_out = True

        self.values = {}


# Static output functions
def remove_restricted_localities():
    # Get list of all event records with restricted locality
    if not read_config("localities_removed"):
        restricted_events = [i for i in memo if memo[i].get("restrict_locality")]
        for event_pid in restricted_events:
            remove_event_coordinates(event_pid)

            restricted_objects = list_restricted_objects(event_pid)
            if restricted_objects:
                remove_object_locality(restricted_objects)
                remove_object_images(restricted_objects)

        if not read_config("quiet"):
            print("Locality information removed from restricted specimens")
        write_config("localities_removed", True)


def remove_event_coordinates(event_pid):
    # Remove decimal latitude, longitude, and datum from mappingDetails
    loc_data = records.records[event_pid].data.get("atLocation")
    mapping_data = None
    if loc_data:
        try:
            mapping_data = loc_data["mappingDetails"][0]
        except (KeyError, IndexError):
            pass

    if mapping_data:
        if not read_config("quiet"):
            print("Removing locality information from {}".format(event_pid))
        records.records[event_pid].data["atLocation"]["mappingDetails"][0]["decimalLatitude"] = None
        records.records[event_pid].data["atLocation"]["mappingDetails"][0]["decimalLongitude"] = None
        records.records[event_pid].data["atLocation"]["mappingDetails"][0]["geodeticDatum"] = None


def list_restricted_objects(event_pid):
    # Create list of restricted objects from memo to allow redactions
    object_records = [i for i in memo if memo[i].get("associated_event") == event_pid]
    if len(object_records) > 0:
        return object_records
    else:
        return None


def remove_object_locality(restricted_objects):
    # Remove locality from objects associated with restricted events
    for record_pid in restricted_objects:
        if not read_config("quiet"):
            print("Removing locality information from related record {}".format(record_pid))
        records.records[record_pid].data["evidenceFor"]["atEvent"]["atLocation"]["locality"] = None
        records.records[record_pid].data["restrictLocalityData"] = True


def remove_object_images(restricted_objects):
    # Remove images from objects associated with restricted events
    # Keep images if they're of types
    for record_pid in restricted_objects:
        type_status = [i for i in collate_list(records.records[record_pid].data,
                                               ["identification", "i", "typeStatus"]) if i]
        if len(type_status) == 0:
            if not read_config("quiet"):
                print("Removing images from related record {}".format(record_pid))
            records.records[record_pid].data["hasRepresentation"] = None


def remove_nonwriting_images(record):
    # Removes images not being written out if only some selected
    memo_record = memo.get(record.pid)
    if memo_record:
        if len(memo_record["media_irns"]) > 0:
            if len(memo_record["media_irns"]) < len(record.data.get("hasRepresentation")):
                has_rep_section = record.data.get("hasRepresentation")
                new_has_rep_section = [sec for sec in has_rep_section if sec.get("id") in memo_record["media_irns"]]
                record.data["hasRepresentation"] = new_has_rep_section

    return record
