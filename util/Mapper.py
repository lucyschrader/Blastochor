# -*- coding: utf-8 -*-

from Blastochor import app

class Mapping():
    def __init__(self):
        self.mapping_file = app.settings.mapping_file
        self.mapping_rules = {}
        self.outputs = []
        self.ordered_fieldnames = {}
        self.harvest_triggers = []

        self.load_map()

    def load_mapping():
        # Read mapping from provided yaml document
        pass

    def load_map(self):
        with open(self.mapping_file, "r", encoding="utf-8") as f:
            for line in f.readlines():
                if line.startswith("#"):
                    output_label = line[2,-1]
                    self.mapping_rules.update({output_label: []})
                    self.outputs.append(output_label)
                    self.ordered_fieldnames.update({output_label: []})
                elif line.startswith("/"):
                    endpoint = line.replace("/", "")
                elif len(line) == 0:
                    pass
                elif line.startswith("harvest:"):
                    line.split(", "):
                    harvest_endpoint = line[0]
                    harvest_path = line[1]
                    label = None
                    try:
                        label = line[2]
                    new_trigger = ReharvestTrigger(parent_endpoint=endpoint, harvest_path=harvest_path, harvest_endpoint=harvest_endpoint, label=label)
                    self.harvest_triggers.append(new_trigger)
                else:
                    rule = line.split(" = ")
                    fieldname = rule[0]
                    functions = rule[1].split(" | ")
                    new_rule = MappingRule(endpoint=endpoint, fieldname=fieldname, functions=functions)

                    self.mapping_rules.get(output_label).append(new_rule)
                    self.ordered_fieldnames.get(output_label).append(fieldname)

    def load_rule(self, output_label, fieldname):
        file_rules = self.mapping_rules.get(output_label)
        rule = filter(lambda x: x.output_fieldname == fieldname, file_rules)[0]

        return rule

class MappingRule():
    def __init__(self, endpoint=None, fieldname=None, functions=[]):
        self.endpoint = endpoint
        self.output_fieldname = fieldname
        self.mapping_functions = functions

        if self.endpoint == None:
            self.endpoint = app.settings.api.endpoint

class ReharvestTrigger():
    def __init__(self, parent_endpoint=None, harvest_path=None, harvest_endpoint=None, label=None):
        self.parent_endpoint = parent_endpoint
        self.harvest_path = harvest_path
        self.harvest_endpoint = harvest_endpoint
        self.label = label