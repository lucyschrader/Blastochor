# -*- coding: utf-8 -*-

import os
import yaml
from datetime import datetime

collections = ["Archaeozoology", "Art", "Birds", "CollectedArchives", "Crustacea", "Fish", "FossilVertebrates", "Geology", "History", "Insects", "LandMammals", "MarineInvertebrates", "MarineMammals", "Molluscs", "MuseumArchives", "PacificCultures", "Philatelic", "Photography", "Plants", "RareBooks", "ReptilesAndAmphibians", "TaongaMāori"]
sciences = ["Archaeozoology", "Birds", "Crustacea", "Fish", "FossilVertebrates", "Geology", "Insects", "LandMammals", "MarineInvertebrates", "MarineMammals", "Molluscs", "Plants", "ReptilesAndAmphibians"]
humanities = ["Art", "CollectedArchives", "History", "MuseumArchives", "PacificCultures", "Philatelic", "Photography", "RareBooks", "TaongaMāori"]

def read_config():
    config_path = "./Config.yml"
    with open(config_path, "r") as f:
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
        self.source_data = None
        self.irn_list = []

    def build_list(self):
        if self.source_file.endswith(".csv"):
            with open(self.source_file, newline="", encoding="utf-8") as f:
                self.source_data = csv.DictReader(f, delimiter=",")

            for row in self.source_data:
                this_irn = row.get("record_irn")
                if DataExporter.settings.use_skipfile == True:
                    if DataExporter.skip_check(this_irn) == True:
                        break
                self.irn_list.append(this_irn)

        elif self.source_file.endswith(".txt"):
            with open(self.source, "r", encoding="utf-8") as f:
                self.source_data = f.readlines()

            for row in self.source_data:
                this_irn = int(row.strip())
                if self.settings.use_skipfile == True:
                    if self.skip_check(this_irn) == True:
                        break
                self.irn_list.append(this_irn)
        
    def skip_check(self, irn):
        if irn in self.skiplist:
            return True
        
        return False

class AppStats():
    def __init__(self):
        self.start_time = None
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

    def end(self):
        end_time = datetime.now()
        delta = end_time - self.start_time
        self.run_time = delta.total_seconds()

    def print_stats(self):
        print("Script ran in {} seconds".format(self.run_time))
        print("Script made {} API calls".format(self.api_call_count))

        if config.get("mode") == "search" or "scroll":
            print("Script found {} search results".format(self.search_result_count))
        elif config.get("mode") == "list":
            print("Script queried {} records from source list".format(self.list_count))

        print("Script queried {} extension records".format(self.extension_records_count))

        for label in self.file_write_counts.keys():
            print("Script wrote {n} records to the {l} file".format(n=self.file_write_counts.get(label), l=label))

config = read_config()
update_settings()
set_filters()

if config.get("quiet") == False:
    print("Settings updated...")

stats = AppStats()