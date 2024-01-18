import yaml

from src.setup.Settings import read_config, write_config
from src.setup.Validator import MapValidator
from src.util.Output import Output


# Read the mapfile to generate outputs and populate them
# with fieldnames and rules for reharvests and processing
class Mapping():
    def __init__(self):
        self.mapping_file = read_config("mapping_file")
        self.outputs = []
        self.ordered_fieldnames = {}
        self.reharvest_triggers = []

        self.load_map()

    def load_map(self):
        # Read mapping from provided yaml document
        if not read_config("quiet"):
            print("Reading mapping file {}".format(self.mapping_file))

        map_data = None
        with open(self.mapping_file, "r", encoding="utf-8") as f:
            map_data = yaml.safe_load(f)

        for output_map in map_data:
            # Validate the map to ensure it contains required keys
            # And all fields have workable functions and parameters
            map_validator = MapValidator(output_map, read_config("quiet"), read_config("country_codes"))
            if map_validator.fail:
                exit("Map validation failed")

            # If all's well, create the output object for each map
            self.create_output_from_map(output_map)

    def create_output_from_map(self, output_map):
        # Set the label of the first output as the corefile
        label = output_map.get("label")
        if not read_config("corefile"):
            write_config("corefile", label)

        # Read output variables from map
        reference_column = output_map.get("reference_column")
        endpoint = output_map.get("primary_endpoint")
        explode_on = output_map.get("explode")
        reduce_on = output_map.get("reduce")
        requires = output_map.get("requires")
        output_rules = output_map.get("fields")

        fieldnames = []
        rules = []

        # For each field, read and save the rules for processing it
        for rule in output_rules:
            output_fieldname = list(rule.keys())[0]
            functions = rule.get(output_fieldname)
            new_rule = MappingRule(endpoint=endpoint, fieldname=output_fieldname, functions=functions)

            fieldnames.append(output_fieldname)
            rules.append(new_rule)

        # Create the Output object for this part of the map
        output = Output(label=label,
                        endpoint=endpoint,
                        reference_column=reference_column,
                        explode_on=explode_on,
                        reduce_on=reduce_on,
                        requires=requires,
                        fieldnames=fieldnames,
                        rules=rules)

        self.outputs.append(output)

        if output_map.get("extend"):
            self.create_triggers(output_map, endpoint)

# Use extension rules from the map to set up triggers that
# will fire when an applicable record is harvested
    def create_triggers(self, output_map, endpoint):
        for trigger in output_map.get("extend"):
            harvest_path = trigger.get("path")
            harvest_endpoint = trigger.get("endpoint")
            labels = trigger.get("for_label")
            if labels:
                labels = labels.split(", ")
            else:
                labels = [None]
            for label in labels:
                new_trigger = ReharvestTrigger(parent_endpoint=endpoint,
                                               harvest_path=harvest_path,
                                               harvest_endpoint=harvest_endpoint,
                                               label=label)

                self.reharvest_triggers.append(new_trigger)


class MappingRule():
    def __init__(self, endpoint=None, fieldname=None, functions=[]):
        self.endpoint = endpoint
        self.output_fieldname = fieldname
        self.mapping_functions = functions

        if not self.endpoint:
            self.endpoint = read_config("endpoint")

        # To add: validation of functions, do they have the parameters they should have

        if not read_config("quiet"):
            print("New mapping rule created for {e}, {o}".format(e=self.endpoint, o=self.output_fieldname))


class ReharvestTrigger():
    def __init__(self, parent_endpoint=None, harvest_path=None, harvest_endpoint=None, label=None):
        self.parent_endpoint = parent_endpoint
        self.harvest_path = harvest_path
        self.harvest_endpoint = harvest_endpoint
        self.label = label

        if not read_config("quiet"):
            print("New reharvest trigger created for {e}, {p}".format(e=self.harvest_endpoint, p=self.harvest_path))
