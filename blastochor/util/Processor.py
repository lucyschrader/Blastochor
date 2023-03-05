# -*- coding: utf-8 -*-

import requests
import time

from blastochor.settings.Settings import config
from blastochor.util.Records import records

def handle_iterator_in_path(path=None, ordinal=None):
    # Replace the list indicator 'i' in a path with a specified ordinal to create a navigable path
    # If no ordinal provided, defaults to first item in the list
    if not config.get("quiet"):
        print("Path: {}".format(path))

    if "i" in path:
        if not ordinal:
            ordinal = 0

        path = ["ord:{}".format(str(ordinal)) if item == "i" else item for item in path]

        if not config.get("quiet"):
            print("Revised path: {}".format(path))

    return path

def step_to_field(data=None, path=None):
    # Step through a record to provide a subsection or value
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

    for i in range(0, len(parent_data)):
        value = literal(data, path=path, ordinal=i)
        values.append(value)

    return values

def concatenate_list(data):
    # Join a list using "|" as specified in Darwin Core
    value = data.join(" | ")
    return value

def conditional_inclusion(data, value_path, check_path, check_value):
    # Return a value if another field matches a specified value
    # Both paths must be in the same section of the record
    # For example, find related.i.contentUrl if related.i.title == "ORCID"
    if "i" in check_path:
        check_list = collate_list(data, path=check_path)
        ordinal = check_list.index(check_value)
        value = literal(data, path=value_path, ordinal=ordinal)
        return value

    else:
        check = literal(data, path=check_path)
        if check == check_value:
            value = literal(data, path=value_path)
            return value

    return None

def country_code(data, params):
    # Find a country name in a record and return an ISO 2-character country code if match is found
    pass

def fixed_vocab(data, params):
    # Return a value if it matches a specified list
    pass

def format_string(data, params):
    # Find a value and incorporate it into a specified string
    string = params[0]
    path = params[1].split(".")
    try:
        ordinal == params[2]
    except:
        ordinal = None
    path = handle_iterator_in_path(path=path, ordinal=ordinal)
    value = step_to_field(data, path)
    return string.format(value)

def hardcode_value(params):
    # Return a specified string
    value = params[0]
    return value

def literal(data, **kwargs):
    # Find a given path in a record and return the literal value
    path = handle_iterator_in_path(path=kwargs.get("path"), ordinal=kwargs.get("ordinal"))
    value = step_to_field(data=data, path=path)
    return value

def lookup_record(data, **kwargs):
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

def related(data, path):
    # Make a fresh query to the special /related endpoint for the current record
    # Collate values from the path specified
    values = []
    
    auth_key = "x-api-key"
    auth_value = config.get("api_key")
    headers = {auth_key: auth_value, "Content-Type": "application/json", "Accept": "application/json;profiles=tepapa.collections.api.v1"}
    related_url = "{}/related".format(data.get("href"))
    response = json.loads(requests.get(related_url, headers=headers).text)

    for record in response:
        if "i" in path:
            record_values = collate_list(data=record, path=path)
            for value in record_values:
                values.append(value)
        else:
            record_value = literal(data=record, path=path)
            values.append(record_value)
    
    time.sleep(0.1)

    return values

def value_extend(data, params):
    # Extend a value to a specified length using a provided string
    pass
    
def value_truncate(data, params):
    # Truncate a value to a specified length
    # Optionally provide a truncation indicator at the end, eg "..."
    pass

class FieldProcessor():
    def __init__(self, data, rule, explode_ordinal):
        self.data = data
        self.functions = rule.mapping_functions
        self.explode_ordinal = explode_ordinal

        self.reprocess_value = False

        self.value = None

        self.run_processing()

    def run_processing(self):
        reprocess_value = False
        for f in self.functions:
            function = list(f.keys())[0]
            params = f.get(function)

            if reprocess_value == True:
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
                check_path = check_param[0]
                check_value = check_param[1]
                return conditional_inclusion(data, value_path=value_path, check_path=check_path, check_value=check_value)

            case "country_code":
                return country_code(data, params)

            case "fixed_vocab":
                return fixed_vocab(data, params)
            
            case "format_string":
                return format_string(data, params)

            case "hardcoded":
                return hardcode_value(params)

            case "literal":
                path = params[0].split(".")
                try:
                    ordinal = params[1]
                except:
                    ordinal = None
                return literal(data, path=path, ordinal=ordinal)

            case "lookup":
                endpoint = params[0]
                path = params[1].split(".")
                try:
                    ordinal = params[2]
                except:
                    ordinal = None

                record = lookup_record(data, endpoint=endpoint, path=path, ordinal=ordinal)
                if record:
                    return record.data

            case "measurement_conversion":
                return measurement_conversion(data, params)

            case "points_to":
                return points_to(data, params)

            case "related":
                path = params[0].split(".")
                return get_related(data, path)