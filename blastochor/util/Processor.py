# -*- coding: utf-8 -*-

import requests
import time
import json

from blastochor.settings.Settings import config
from blastochor.util.Records import records

with open("blastochor/resources/iso_countrycodes.json") as f:
    countrycodes = json.load(f)

def handle_iterator_in_path(path=None, ordinal=None):
    # Replace the list indicator 'i' in a path with a specified ordinal to create a navigable path
    # If no ordinal provided, defaults to first item in the list
    if not config.get("quiet"):
        print("Path: {}".format(path))

    if isinstance(path, list):    
        if "i" in path:
            if not ordinal:
                ordinal = 0

            path = ["ord:{}".format(str(ordinal)) if item == "i" else item for item in path]

            if not config.get("quiet"):
                print("Revised path: {}".format(path))

    return path

def step_to_field(data=None, path=None):
    # Step through a record to provide a subsection or value
    if isinstance(path, str):
        return data.get(path)
    else:
        step = data
        for field in path:
            if field.startswith("ord:"):
                ordinal = int(field.split(":")[1])
                try:
                    step = step[ordinal]
                except:
                    return None
            else:
                try:
                    step = step.get(field)
                except:
                    return None
        if step is not None:
            return step
        else:
            return None

def clean_html(data, **kwargs):
    # Remove unwanted html markup from a value
    dirty_value = literal(data, **kwargs)
    #TODO: Add cleaning function
    value = dirty_value
    return value

def collate_list(data, path):
    # Look through each child path of a list and collate all values of child fields with the same name
    # Currently only works for one level of list
    values = []

    parent_path = []
    for field in path:
        if field == "i":
            break
        else:
            parent_path.append(field)
    parent_data = step_to_field(data, parent_path)
    if not parent_data:
        return None

    # Put a limit on the number of list items returned
    # Long lists (eg people referenced by a lot of narratives) can break the CSV cell limit
    iterator_limit = len(parent_data)
    app_limit = config.get("max_list_size")
    if app_limit > 0 and app_limit < iterator_limit:
        iterator_limit = app_limit

    for i in range(0, iterator_limit):
        value = literal(data, path=path, ordinal=i)
        values.append(value)

    return values

def concatenate_list(data):
    # Join a list using "|" as specified in Darwin Core
    if isinstance(data, list):
        data = [str(i) for i in data if i is not None]
        if len(data) == 1:
            value = data[0]
        elif len(data) > 1:
            value = " | ".join(data)
        else:
            value = None
        return value
    else:
        return data

def conditional_inclusion(data, value_path, check_path, check_value):
    # Return a value if another field matches a specified value
    # Both paths must be in the same section of the record
    # For example, find related.i.contentUrl if related.i.title == "ORCID"
    if "i" in check_path:
        check_list = collate_list(data, path=check_path)
        if not check_list:
            return None
        else:
            try:
                ordinal = check_list.index(check_value)
                return literal(data, path=value_path, ordinal=ordinal)
            except:
                return None

    else:
        check = literal(data, path=check_path)
        if not check:
            return None
        else:
            if check == check_value:
                return literal(data, path=value_path)

    return None

def country_code(data, path):
    country = literal(data, path=path)
    if not country:
        return None
    else:
        country_lookup = next(filter(lambda country_dict: country_dict.get("Name") == country, countrycodes), None)
        if country_lookup:
            return country_lookup.get("Code")
        else:
            return None

def fixed_vocab(data, params):
    # Return a value if it matches a specified list
    pass

def format_string(data, string, inserts, explode_ordinal):
    # Find a value and incorporate it into a specified string
    path_list = inserts.split(", ")
    values = []
    for path in path_list:
        if path == "explode_ordinal":
            values.append(explode_ordinal)
        else:
            path = path.split(".")
            value = literal(data, path=path)
            if not value:
                value = ""
            values.append(value)

    return string.format(*values)

def hardcode_value(value):
    # Return a specified string
    return value

def literal(data, **kwargs):
    # Find a given path in a record and return the literal value
    path = handle_iterator_in_path(path=kwargs.get("path"), ordinal=kwargs.get("ordinal"))
    value = step_to_field(data=data, path=path)
    return value

def lookup_record(data, irn, endpoint):
    # Find an IRN in the provided record and return the associated record
    path = kwargs.get("path")
    endpoint = kwargs.get("endpoint")
    ordinal = kwargs.get("ordinal")

    irn = literal(data, path=path, ordinal=ordinal)

    if irn:
        return records.find_record(endpoint=endpoint, irn=irn)
    
    return None

def measurement_conversion(data, params):
    pass

def prioritised_inclusion(data, params):
    # Try multiple paths in order and return the value of the first available one
    value = None
    paths = params[0].split(", ")
    try:
        ordinal == params[1]
    except:
        ordinal = None
    for path in paths:
        path = path.split(".")
        path = handle_iterator_in_path(path=path, ordinal=ordinal)
        if value:
            return value
        else:
            value = step_to_field(data, path)

    return value

def process_quality_score():
    pass

def related(data, size, types):
    # Make a fresh query to the special /related endpoint for the current record
    # Collate values from the path specified
    values = []
    
    auth_key = "x-api-key"
    auth_value = config.get("api_key")
    headers = {auth_key: auth_value, "Content-Type": "application/json", "Accept": "application/json;profiles=tepapa.collections.api.v1"}
    related_url = "{}/related".format(data.get("href"))

    if size or types:
        related_url += "?"
    if size:
        related_url += "size={}".format(size)
    if size and types:
        related_url += "&"
    if types:
        related_url += "types={}".format(types)

    if not config.get("quiet"):
        print("Requesting {}".format(related_url))

    results = json.loads(requests.get(related_url, headers=headers).text).get("results")
    
    time.sleep(0.1)

    return results

def value_extend(data, params):
    # Extend a value to a specified length using a provided string
    pass
    
def value_truncate(data, params):
    # Truncate a value to a specified length
    # Optionally provide a truncation indicator at the end, eg "..."
    pass

class FieldProcessor():
    def __init__(self, data, rule, explode_on, explode_ordinal):
        self.data = data
        self.functions = rule.mapping_functions
        self.explode_on = explode_on
        self.explode_ordinal = explode_ordinal

        self.reprocess_value = False

        self.value = None
        self.holding_value = []

        if not config.get("quiet"):
            print("Processing column {}".format(rule.output_fieldname))

        self.run_processing()

    def run_processing(self):
        reprocess_value = False
        for f in self.functions:
            function = list(f.keys())[0]
            params = f.get(function)

            if reprocess_value == True:
                if function == "for_each":
                    if isinstance(self.value, list):
                        for subfunction in params:
                            print(self.value)
                            subfunction_name = list(subfunction.keys())[0]
                            subfunction_params = subfunction.get(subfunction_name)
                            subfunction_index = 0
                            for value in self.value:
                                self.value[subfunction_index] = self.select_function(subfunction_name, value, subfunction_params)
                                subfunction_index += 1
                    else:
                        # TODO: raise an error and fall back in some handy way
                        pass
                else:
                    self.value = self.select_function(function, self.value, params)
            else:
                self.value = self.select_function(function, self.data, params)

            if not config.get("quiet"):
                print("Function: {}".format(function))
                print("Value: {}".format(self.value))

            # If rule has subsequent functions, they'll reuse the previous function's value
            reprocess_value = True

    def select_function(self, function, data, params):
        match function:

            case "clean_html":
                path = params[0].split(".")
                try:
                    ordinal = params[1]
                except:
                    ordinal = None
                return clean_html(data, path=path, ordinal=ordinal)

            case "collate_list":
                path = params[0].split(".")
                return collate_list(data, path=path)
            
            case "concatenate":
                return concatenate_list(data)

            case "conditional":
                value_path = params[0].split(".")
                check_param = params[1].split("=")
                check_path = check_param[0].split(".")
                check_value = check_param[1]
                return conditional_inclusion(data, value_path=value_path, check_path=check_path, check_value=check_value)

            case "country_code":
                path = params[0].split(".")
                return country_code(data, path)

            case "fixed_vocab":
                return fixed_vocab(data, params)
            
            case "format_string":
                string = params[0]
                inserts = params[1]
                return format_string(data, string, inserts, self.explode_ordinal)

            case "hardcoded":
                value = params[0]
                return hardcode_value(value)

            case "literal":
                path = params[0].split(".")
                if self.explode_on in path:
                    ordinal = self.explode_ordinal
                else:
                    try:
                        ordinal = params[1]
                    except:
                        ordinal = None
                return literal(data, path=path, ordinal=ordinal)

            case "lookup":
                endpoint = params[0]
                irn = data

                if not irn:
                    return None
                else:
                    return records.find_record(endpoint=endpoint, irn=irn).data

            case "measurement_conversion":
                return measurement_conversion(data, params)

            case "points_to":
                return points_to(data, params)

            case "related":
                size = params[0]
                types = params[1]
                return related(data, size=size, types=types)