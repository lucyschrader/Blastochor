# -*- coding: utf-8 -*-

import os
import yaml
from Blastochor import app

class Settings():
    def __init__(self):
        self.config = self.read_config()
        self.api_key = None
        self.mapping_file = None
        self.corefile = None
        self.input_dir = "input_files"
        self.output_dir = "output_files"
        self.use_skiplist = False
        self.skipfile = None
        self.skiplist = None

        self.mode = None
        self.quiet = False

        self.update_settings()

        self.api = ApiSettings(self.config)
        self.list = ListSettings(self.config)
        self.search = SearchSettings(self.config)
        self.filters = FilterSettings(self.config)

    def read_config(self):
        config_path = "../Config.yml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def update_settings(self):
        # Return error if no API key
        if self.config.get("api_key_env") is not None:
            self.api_key = os.environ.get(self.config.get("api_key_env"))

        if self.config.get("mapping_file") is not None:
            self.mapping = self.config.get("mapping_file")
        else:
        	self.mapping = "defaultmap.yaml"

        if self.config.get("corefile") is not None:
        	self.corefile = self.config.get("corefile")

        if self.config.get("input_dir") is not None:
            self.input_dir = self.config.get("input_dir")
        
        if self.config.get("output_dir") is not None:
            self.output_dir = self.config.get("output_dir")

        if self.config.get("use_skiplist") == True:
            self.use_skiplist = True

        if self.config.get("skipfile") is not None:
            self.skipfile = self.config.get("skipfile")

        if self.use_skiplist == True:
            self.skiplist = self.populate_skiplist()

        # TODO: Return error if no mode selected
        if self.config.get("mode") is not None:
            self.mode = self.config.get("mode")

        if self.config.get("quiet") is not False:
            self.quiet = self.config.get("quiet")

    def populate_skiplist(self):
        with open(self.skipfile, 'r', encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:                        
            self.skiplist.append(int(line.strip()))

        if self.quiet == False:
            print("Skiplist populated")


class ApiSettings():
    def _init__(self, config):
        self.api_config = config.get("api")
        self.base_url = "https://data.tepapa.govt.nz/collection/"
        self.endpoint = "object"
        self.max_records = -1
        self.size = 500

        self.update_settings()

    def update_settings(self):
        if self.api_config.get("base_url") is not None:
            self.base_url = self.api_config.get("base_url")

        if self.api_config.get("endpoint") is not None:
            self.endpoint = self.api_config.get("endpoint")

        if self.api_config.get("max_records") is not None:
            self.max_records = self.api_config.get("max_records")

        if self.api_config.get("size") is not None:
            self.size = self.api_config.get("size")

class ListSettings():
    def __init__(self, config):
        self.list_config = config.get("list")
        self.list_source = None

        self.update_settings()

    def update_settings(self):
        if self.list_config.get("source") is not None:
            self.list_source = self.list_config.get("source")

class SearchSettings():
    def __init__(self, config):
        self.search_config = config.get("search")
        self.query = "*"
        self.sort = {}

        self.update_settings()

    def update_settings(self):
        if self.search_config.get("query") is not None:
            self.query = self.search_config.get("query")

        if self.search_config.get("sort_field") is not None:
            self.sort = {self.search_config.get("sort_field"): self.search_config.get("sort_value")}

class FilterSettings():
    def __init__(self, config):
        self.filter_config = config.get("filters")
        self.collection = None
        self.allows_download = None
        self.min_image_size = None
        self.filters = []

        self.collections = ["Archaeozoology", "Art", "Birds", "CollectedArchives", "Crustacea", "Fish", "FossilVertebrates", "Geology", "History", "Insects", "LandMammals", "MarineInvertebrates", "MarineMammals", "Molluscs", "MuseumArchives", "PacificCultures", "Philatelic", "Photography", "Plants", "RareBooks", "ReptilesAndAmphibians", "TaongaMāori"]
        self.sciences = ["Archaeozoology", "Birds", "Crustacea", "Fish", "FossilVertebrates", "Geology", "Insects", "LandMammals", "MarineInvertebrates", "MarineMammals", "Molluscs", "Plants", "ReptilesAndAmphibians"]
        self.humanities = ["Art", "CollectedArchives", "History", "MuseumArchives", "PacificCultures", "Philatelic", "Photography", "RareBooks", "TaongaMāori"]

        self.update_settings()

    def update_settings(self):
        user_collection = self.filter_config.get("collection")
        if user_collection is not None:
            if user_collection in self.collections:
                self.collection = user_collection
                self.filters.append({"field": "collection", "value": user_collection})

                if user_collection in self.sciences:
                    self.filters.append({"field": "type", "value": "Specimen"})
                elif user_collection in self.humanities:
                    self.filters.append({"field": "Type", "value": "Object"})
                    self.filters.append({"field": "additionalType", "keyword": "PhysicalObject"})

        self.allows_download = self.filter_config.get("allows_download")
        if self.allows_download == True:
            self.filters.append = {"field": "hasRepresentation.rights.allowsDownload", "value": "True"}
        elif self.allows_download == False:
            self.filters.append = {"field": "hasRepresentation.rights.allowsDownload", "value": "False"}

        if self.filter_config.get("min_image_size") is not None:
            self.min_image_size = self.filter_config.get("min_image_size")

        kw_fields = self.filter_config.get("keyword_fields")
        kw_values = self.filter_config.get("keyword_values")

        for i in range(0, len(kw_fields)):
            self.filters.append({"field": kw_fields[i], "value": kw_values[i]})

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
                    if DataExporter.skip_check(this_irn) == True
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