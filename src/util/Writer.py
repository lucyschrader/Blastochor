import csv
from src.setup.Settings import read_config
from src.monitoring.Stats import stats


class WriteFile():
    def __init__(self, label):
        self.label = label
        self.filename = self.generate_filename()

        self.file = open(self.filename, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file, delimiter=",")

    def generate_filename(self):
        output_dir = read_config("output_dir")
        export_dir = read_config("export_filename")
        write_filename = "{}-export.csv".format(self.label)
        stats.export_filenames.append(write_filename)
        write_location = "{d}/{e}/{f}".format(d=output_dir,
                                              e=export_dir,
                                              f=write_filename)
        return write_location

    def write_header_row(self, fieldnames):
        self.writer.writerow(fieldnames)

    def write_rows(self, output_rows, fieldnames):
        for row in output_rows:
            if row.write_out:
                self.write_this_row(row, fieldnames)

    def write_this_row(self, row, fieldnames):
        write_values = []
        if row.write_pointer:
            write_values.append(row.pointer)
        for field in fieldnames:
            value = row.values.get(field)
            # If a value is still a list after processing, turn it into a string
            if isinstance(value, list):
                value = [str(i) for i in value if i is not None]
                if len(value) == 0:
                    value = None
                elif len(value) == 1:
                    value = value[0]
                elif len(value) > 1:
                    value = " | ".join(value)
                else:
                    value = None
            # If a value is None, turn it into a blank string
            if not value and (value != 0):
                value = ""

            # If removing newlines is turned on, check if value is a string and replace them with spaces
            if read_config("clean_newlines"):
                if isinstance(value, str):
                    value = value.replace("\n", " ")

            write_values.append(value)

        self.writer.writerow(write_values)
        stats.file_write_counts[self.label] += 1
