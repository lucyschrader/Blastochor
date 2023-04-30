# -*- coding: utf-8 -*-

import os
import csv
import yaml
from datetime import datetime
from math import floor

collections = ["Archaeozoology", "Art", "Birds", "CollectedArchives", "Crustacea", "Fish", "FossilVertebrates", "Geology", "History", "Insects", "LandMammals", "MarineInvertebrates", "MarineMammals", "Molluscs", "MuseumArchives", "PacificCultures", "Philatelic", "Photography", "Plants", "RareBooks", "ReptilesAndAmphibians", "TaongaMāori"]
sciences = ["Archaeozoology", "Birds", "Crustacea", "Fish", "FossilVertebrates", "Geology", "Insects", "LandMammals", "MarineInvertebrates", "MarineMammals", "Molluscs", "Plants", "ReptilesAndAmphibians"]
humanities = ["Art", "CollectedArchives", "History", "MuseumArchives", "PacificCultures", "Philatelic", "Photography", "RareBooks", "TaongaMāori"]

def read_config():
    config_path = "./Config.yml"
    with open(config_path, "r", encoding="utf-8") as f:
        print("Reading config file...")
        return yaml.safe_load(f)

def update_settings():
    # Return error if no API key
    if config.get("api_key_env"):
        try:
            config["api_key"] = os.environ.get(config.get("api_key_env"))
        except:
            config["api_key"] = None
            print("No API key found in environment")

    if not config.get("mapping_file"):
    	config["mapping_file"] = "defaultmap.yaml"

    if not config.get("corefile"):
        config["corefile"] = "default"
    
    if not config.get("output_dir"):
        print("Output directory needed to write files")

    if config.get("use_skiplist") == True:
        populate_skiplist()

    # TODO: Return error if no mode selected
    if not config.get("mode"):
        print("No mode selected - should be search, scroll or list")

    if not config.get("endpoint"):
        print("No endpoint provided. Setting to object")
        config["endpoint"] = "object"

    if not config.get("timeout"):
        config["timeout"] = 5

    if not config.get("attempts"):
        config["attempts"] = 3

    if config.get("list_source"):
        config["list_source"] = "./{d}/{f}".format(d=config.get("input_dir"), f=config.get("list_source"))

    if not config.get("query"):
        config["query"] == "*"

def populate_skiplist():
    config["skiplist"] = []
    with open(config.get("skipfile"), 'r', encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:                        
        config["skiplist"].append(int(line.strip()))

    if not config.get("quiet"):
        print("Skiplist populated")

def set_filters():
    config["filters"] = []

    user_collection = config.get("filter").get("collection")
    if user_collection:
        if user_collection in collections:
            config["filters"].append({"field": "collection", "keyword": user_collection})
        if user_collection in sciences:
            config["filters"].append({"field": "type", "keyword": "Specimen"})
        elif user_collection in humanities:
            config["filters"].append({"field": "type", "keyword": "Object"})
            config["filters"].append({"field": "additionalType", "keyword": "PhysicalObject"})

    if config.get("filter").get("allows_download") == True:
        config["filters"].append({"field": "hasRepresentation.rights.allowsDownload", "keyword": "True"})
    elif config.get("filter").get("allows_download") == False:
        config["filters"].append({"field": "hasRepresentation.rights.allowsDownload", "keyword": "False"})

    kw_fields = config.get("filter").get("keyword_fields")
    kw_values = config.get("filter").get("keyword_values")

    if kw_fields:
        kw_fields = kw_fields.split(", ")
        kw_values = kw_values.split(", ")
        for i in range(0, len(kw_fields)):
            config["filters"].append({"field": kw_fields[i], "keyword": kw_values[i]})

class InputList():
    def __init__(self, source_file):
        source_data = None
        irn_list = []

        if source_file.endswith(".csv"):
            with open(source_file, newline="", encoding="utf-8") as f:
                source_data = csv.DictReader(f, delimiter=",")

                for row in source_data:
                    this_irn = row.get("record_irn")
                    this_media_irn = row.get("media_irn")
                    if config.get("use_skipfile") == True:
                        if self.skip_check(this_irn) == True:
                            break

                    this_irn_object = next(filter(lambda input_irn: input_irn.irn == this_irn, irn_list), None)
                    if not this_irn_object:
                        this_irn_object = InputIRN(irn=this_irn)
                        if this_media_irn:
                            this_irn_object.media.append(this_media_irn)
                            this_irn_object.harvest_all = False
                        irn_list.append(this_irn_object)
                    else:
                        if this_media_irn:
                            this_irn_object.media.append(this_media_irn)

        elif source_file.endswith(".txt"):
            with open(source_file, "r", encoding="utf-8") as f:
                source_data = f.readlines()

                for row in source_data:
                    this_irn = int(row.strip())
                    if config.get("use_skipfile") == True:
                        if self.skip_check(this_irn) == True:
                            break
                    this_irn_object = InputIRN(irn=irn)
                    irn_list.append(this_irn_object)

        config["irn_list"] = irn_list
        
    def skip_check(self, irn):
        if irn in config.get("skiplist"):
            return True
        
        return False

class InputIRN():
    def __init__(self, irn=None):
        self.irn = irn
        self.harvest_all = True
        self.media = []

class AppStats():
    def __init__(self):
        self.start_time = None
        self.end_harvest_time = None
        self.end_extrarecords_time = None
        self.harvest_time = None
        self.extrarecords_time = None
        self.processing_time = None
        self.run_time = None
        self.api_call_count = 0
        self.search_result_count = 0
        self.list_count = 0
        self.extension_records_count = 0
        self.file_write_counts = {}
        self.quality_score_lower = None
        self.quality_score_upper = None

    def start(self):
        self.start_time = datetime.now()

    def end_harvest(self):
        self.end_harvest_time = datetime.now()

    def end_extrarecords(self):
        self.end_extrarecords_time = datetime.now()

    def end(self):
        end_time = datetime.now()

        # Record how long script took to run in total
        delta = end_time - self.start_time
        self.run_time = self.datetime_to_string(delta.total_seconds())

        # Record how long script took to perform initial harvest
        delta = self.end_harvest_time - self.start_time
        self.harvest_time = self.datetime_to_string(delta.total_seconds())

        # Record how long script took to perform extra queries
        delta = self.end_extrarecords_time - self.end_harvest_time
        self.extrarecords_time = self.datetime_to_string(delta.total_seconds())

        # Record how long script took to perform processing
        delta = end_time - self.end_extrarecords_time
        self.processing_time = self.datetime_to_string(delta.total_seconds())

    def datetime_to_string(self, seconds):
        if seconds > 3600:
            hours = seconds // 3600
            minutes = (seconds // 60) % 60
            return "{h} hours and {m} minutes".format(h=hours, m=minutes)
        elif seconds > 60:
            minutes = seconds // 60
            seconds = seconds - (minutes * 60)
            return "{m} minutes and {s} seconds".format(m=minutes, s=seconds)
        else:
            return "{} seconds".format(round(seconds))

    def print_stats(self):
        print("Script ran in {}".format(self.run_time))
        print("Script made {} API calls".format(self.api_call_count))

        if config.get("mode") == "search" or (config.get("mode") == "scroll"):
            print("Search returned {} results".format(self.search_result_count))
        elif config.get("mode") == "list":
            print("Source list contained {} records".format(self.list_count))
        print("Harvesting ran in {}".format(self.harvest_time))

        print("Queried {} extension records".format(self.extension_records_count))
        print("Getting extra records took {}".format(self.extrarecords_time))

        print("Processing records took {}".format(self.processing_time))

        for label in self.file_write_counts.keys():
            print("Wrote {n} records to the {l} file".format(n=self.file_write_counts.get(label), l=label))

class ProgressBar():
    def __init__(self, length=1):
        self.length = length
        self.width = 50
        print("[", " " * self.width, "]", sep="", end="", flush=True)

    def update(self, count):
        progress_percentage = floor((count / self.length) * 100)

        if progress_percentage % 2 == 0:
            left = self.width * progress_percentage // 100
            right = self.width - left

            tags = "#" * left
            spaces = " " * right
            percents = "{:.0f}%".format(progress_percentage)

            print("\r[", tags, spaces, "]", percents, sep="", end="", flush=True)

        if progress_percentage == 100:
            print("")

config = read_config()
update_settings()
set_filters()

if config.get("quiet") == False:
    print("Settings updated...")

stats = AppStats()