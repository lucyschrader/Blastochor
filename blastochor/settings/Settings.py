# -*- coding: utf-8 -*-

import os
import csv
import yaml

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

    config["record_memo"] = {}

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

# Memo functions
def format_pid(endpoint=None, irn=None):
    if irn:
        return "tepapa:collection/{e}/{i}".format(e=endpoint, i=irn)
    else:
        return None

def check_memo_for_pid(pid):
    record_memo = config["record_memo"].get(pid)
    return record_memo

def add_to_record_memo(status=None, irn=None, endpoint=None, label=None, extension=None, extends=None):
    pid = format_pid(endpoint=endpoint, irn=irn)

    if status == None:
        status = "pending"
    if extension == None:
        extension = False

    config["record_memo"][pid] = {
        "status": status,
        "irn": irn,
        "endpoint": endpoint,
        "pid": pid,
        "write_to": [],
        "structure": {},
        "is_extension": extension,
        "media_irns": []
    }

    if label:
        config["record_memo"][pid]["write_to"].append(label)
        config["record_memo"][pid]["structure"].update({label: {"write": True, "extends": []}})

    return pid

class InputList():
    def __init__(self, source_file):
        source_data = None
        irn_list = []

        endpoint = config.get("endpoint")
        label = config.get("corefile")

        if source_file.endswith(".csv"):
            with open(source_file, newline="", encoding="utf-8") as f:
                source_data = csv.DictReader(f, delimiter=",")

                for row in source_data:
                    this_irn = int(row.get("record_irn"))
                    this_media_irn = int(row.get("media_irn"))
                    if config.get("use_skipfile") == True:
                        if self.skip_check(this_irn) == True:
                            break

                    this_pid = "tepapa:collection/{e}/{i}".format(e=endpoint, i=this_irn)
                    if not config["record_memo"].get(this_pid):
                        add_to_record_memo(status="pending", irn=this_irn, endpoint=endpoint, label=label)

                    if this_media_irn:
                        memo_record = config["record_memo"][this_pid]
                        if this_media_irn not in memo_record["media_irns"]:
                            memo_record["media_irns"].append(this_media_irn)

        elif source_file.endswith(".txt"):
            with open(source_file, "r", encoding="utf-8") as f:
                source_data = f.readlines()

                for row in source_data:
                    this_irn = int(row.strip())
                    if config.get("use_skipfile") == True:
                        if self.skip_check(this_irn) == True:
                            break

                    this_pid = "tepapa:collection/{e}/{i}".format(e=endpoint, i=this_irn)
                    if not config["record_memo"].get(this_pid):
                        add_to_record_memo(status="pending", irn=this_irn, endpoint=endpoint, label=label)
        
    def skip_check(self, irn):
        if irn in config.get("skiplist"):
            return True
        
        return False

config = read_config()
update_settings()
set_filters()

if config.get("quiet") == False:
    print("Settings updated...")