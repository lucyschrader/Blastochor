# -*- coding: utf-8 -*-

import yaml
from blastochor.settings.Settings import config
from blastochor.util.Output import Output

class Mapping():
    def __init__(self):
        self.mapping_file = config.get("mapping_file")
        self.mapping_rules = {}
        self.outputs = []
        self.ordered_fieldnames = {}
        self.harvest_triggers = []

        self.load_map()

    def load_map(self):
        # Read mapping from provided yaml document

        if not config.get("quiet"):
            print("Reading mapping file...")

        map = None
        with open(self.mapping_file, "r", encoding="utf-8") as f:
            map = yaml.safe_load(f)

        for output_map in map:
            label = output_map.get("label")
            endpoint = output_map.get("primary_endpoint")
            explode_on = output_map.get("explode")
            reduce_on = output_map.get("reduce")
            output_rules = output_map.get("fields")

            fieldnames = []
            rules = []

            for rule in output_rules:
                output_fieldname = list(rule.keys())[0]
                functions = rule.get(output_fieldname)
                new_rule = MappingRule(endpoint=endpoint, fieldname=output_fieldname, functions=functions)

                fieldnames.append(output_fieldname)
                rules.append(new_rule)

            output = Output(label=label, explode_on=explode_on, reduce_on=reduce_on, fieldnames=fieldnames, rules=rules)

            self.outputs.append(output)

            if output_map.get("extend"):
                self.create_triggers(output_map, endpoint)

    def create_triggers(self, output_map, endpoint):
        for trigger in output_map.get("extend"):
            harvest_path = trigger.get("path")
            harvest_endpoint = trigger.get("endpoint")
            label = trigger.get("for_label")

            new_trigger = ReharvestTrigger(parent_endpoint=endpoint, harvest_path=harvest_path, harvest_endpoint=harvest_endpoint, label=label)

            self.harvest_triggers.append(new_trigger)

    def load_rule(self, output_label, fieldname):
        file_rules = self.mapping_rules.get(output_label)
        rule = next(filter(lambda x: x.output_fieldname == fieldname, file_rules), None)

        return rule

class MappingRule():
    def __init__(self, endpoint=None, fieldname=None, functions=[]):
        self.endpoint = endpoint
        self.output_fieldname = fieldname
        self.mapping_functions = functions

        if self.endpoint == None:
            self.endpoint = config.get("endpoint")

        if not config.get("quiet"):
            print("New mapping rule created for {e}, {o}".format(e=self.endpoint, o=self.output_fieldname))

class ReharvestTrigger():
    def __init__(self, parent_endpoint=None, harvest_path=None, harvest_endpoint=None, label=None):
        self.parent_endpoint = parent_endpoint
        self.harvest_path = harvest_path
        self.harvest_endpoint = harvest_endpoint
        self.label = label

        if not config.get("quiet"):
            print("New reharvest trigger created for {e}, {p}".format(e=self.harvest_endpoint, p=self.harvest_path))

mapping = Mapping()