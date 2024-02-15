from datetime import datetime
from math import floor
from src.setup.Settings import read_config


class ApplicationStats():
    def __init__(self):
        self.app_start = None
        self.app_end = None
        self.harvest_start = None
        self.harvest_end = None
        self.extension_records_start = None
        self.extension_records_end = None
        self.processing_start = None
        self.processing_end = None
        self.writing_start = None
        self.writing_end = None

        self.run_time = None
        self.harvest_time = None
        self.extension_time = None
        self.processing_time = None
        self.writing_time = None

        self.api_call_count = 0
        self.initial_record_count = 0
        self.source_list_count = 0
        self.extension_records_count = 0

        self.file_write_counts = {}
        self.export_filenames = []

        self.quality_score_lower = None
        self.quality_score_upper = None

    def mark_time(self, task):
        timestamp = datetime.now()
        match task:
            case "start":
                self.app_start = timestamp
            case "end":
                self.app_end = timestamp
            case "harvest start":
                self.harvest_start = timestamp
            case "harvest end":
                self.harvest_end = timestamp
            case "extension start":
                self.extension_records_start = timestamp
            case "extension end":
                self.extension_records_end = timestamp
            case "processing start":
                self.processing_start = timestamp
            case "processing end":
                self.processing_end = timestamp

    def report(self):
        # Record how long script took to run in total
        delta = self.app_end - self.app_start
        self.run_time = datetime_to_string(delta.total_seconds())

        # Record how long script took to perform initial harvest
        delta = self.harvest_end - self.harvest_start
        self.harvest_time = datetime_to_string(delta.total_seconds())

        # Record how long script took to perform extra queries
        delta = self.extension_records_end - self.extension_records_start
        self.extension_time = datetime_to_string(delta.total_seconds())

        # Record how long script took to perform processing
        delta = self.processing_end - self.processing_start
        self.processing_time = datetime_to_string(delta.total_seconds())

        self.print_stats()

    def print_stats(self):
        print("Script ran in {}".format(self.run_time))
        print("Script made {} API calls".format(self.api_call_count))

        if read_config("mode") != "list":
            print("Search returned {} results".format(self.initial_record_count))
        else:
            print("Source list contained {} records".format(self.source_list_count))
        print("Harvesting ran in {}".format(self.harvest_time))

        print("Queried {} extension records".format(self.extension_records_count))
        print("Getting extra records took {}".format(self.extension_time))

        print("Processing records took {}".format(self.processing_time))

        for label in self.file_write_counts.keys():
            print("Wrote {n} records to the {l} file".format(n=self.file_write_counts.get(label), l=label))


def datetime_to_string(seconds):
    if seconds > 3600:
        hours = seconds // 3600
        minutes = (seconds // 60) % 60
        return "{h} hours and {m} minutes".format(h=floor(hours), m=floor(minutes))
    elif seconds > 60:
        minutes = seconds // 60
        seconds = seconds - (minutes * 60)
        return "{m} minutes and {s} seconds".format(m=floor(minutes), s=floor(seconds))
    else:
        return "{} seconds".format(round(seconds))


stats = ApplicationStats()
