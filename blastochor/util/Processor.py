# -*- coding: utf-8 -*-

import requests
import time
import json
from math import floor
import random
import re

from blastochor.settings.Settings import config, stats
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

def clean_html(data):
    # Remove unwanted html markup from a value
    clean = re.compile("<.*?>")
    value = re.sub(clean, "", data)
    value.replace("&nbsp;", "")
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

    if len(values) == 0:
        values = None

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
            if check_value in check_list:
                ordinal = check_list.index(check_value)
                return literal(data, path=value_path, ordinal=ordinal)
            else:
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
    # Find the name of a country and map it to an ISO-3166 two letter code
    country = literal(data, path=path)
    if not country:
        return None
    else:
        country_lookup = next(filter(lambda country_dict: country_dict.get("Name") == country, countrycodes), None)
        if country_lookup:
            return country_lookup.get("Code")
        else:
            return None

def create_filename(data, suffix):
    data = data.replace(" ", "_")
    data = data.replace("?", "")
    data = data.replace("\"", "")
    data = data.replace(":", "")
    data = data.replace(";", "")
    data = data.replace(".", "")
    data = data.replace(",", "")
    data = data.replace("#", "")
    data = data.replace("*", "")
    data = data.replace("\'", "")
    data = data.replace("\\", "")
    data = data.replace("/", "")

    return "{d}.{s}".format(d=data, s=suffix)

def first_match(data, paths):
    # Try multiple paths in order and return the value of the first available one
    value = None
    for path in paths:
        path = path.split(".")
        if "i" in path:
            value = collate_list(data, path)
        else:
            value = literal(data, path)
        if value:
            return value

    return value

def format_string(data, **kwargs):
    # Find a value and incorporate it into a specified string
    string = kwargs.get("string")
    inserts = kwargs.get("inserts")
    required = kwargs.get("required")
    explode_ordinal = kwargs.get("explode_ordinal")
    record_pid = kwargs.get("record_pid")

    values = []
    for path in inserts:
        if path == "explode_ordinal":
            if explode_ordinal is not None or (explode_ordinal == 0):
                values.append(str(explode_ordinal))
            else:
                values.append("")
        elif path == "parent_id":
            if record_pid:
                record_id = record_pid.split("/")[-1]
                values.append(record_id)
            else:
                values.append("")
        else:
            path = path.split(".")
            value = literal(data, path=path, ordinal=explode_ordinal)
            if not value:
                if required == True:
                    continue
                else:
                    value = ""
            values.append(value)

    if required:
        spaces = string.count("{}")
        if len(values) != spaces:
            return None

    return string.format(*values)

def hardcode_value(value):
    # Return a specified string
    return value

def literal(data, **kwargs):
    # Find a given path in a record and return the literal value
    path = handle_iterator_in_path(path=kwargs.get("path"), ordinal=kwargs.get("ordinal"))
    value = step_to_field(data=data, path=path)
    return value

def map_from_value(data, params):
    # If a specified value is present, map to a provided string
    if isinstance(data, list):
        mapped_value = []
        for value in data:
            mapped_value.append(params.get(value))
    else:
        mapped_value = params.get(data)

    return mapped_value

def measurement_conversion(data, params):
    pass

# TODO: Fix, currently not working
def must_match(data, authorities):
    # Include value if it also appears in a provided list of terms
    matching = None
    if isinstance(data, list):
        matching = [term for term in data if str(term).lower() in authorities]
    else:
        if str(data).lower() in authorities:
            matching = data
    return matching

def process_quality_score(data):
    # Turns a record's qualityScore into a integer from 1-500
    # Used to assign priority in Google Arts & Culture
    quality_score = data.get("_meta").get("qualityScore")
    if quality_score:
        score = quality_score - stats.quality_score_lower
        upper = stats.quality_score_upper - stats.quality_score_lower

        score_percentage = score / upper * 100
        score_percentage = 100 - score_percentage

        priority = floor(score_percentage * 3)
        modifier = random.randint(-15, 15)
        priority = priority + modifier

        if priority <= 0:
            priority = random.randint(1, 200)

    return priority

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
    stats.api_call_count +=1
    
    time.sleep(0.1)

    return results

def use_config(key):
    return config.get(key)

def value_extend(data, params):
    # Extend a value to a specified length using a provided string
    pass
    
def value_truncate(data, params):
    # Truncate a value to a specified length
    # Optionally provide a truncation indicator at the end, eg "..."
    pass

class FieldProcessor():
    def __init__(self, rules, output_row):
        self.rules = rules
        self.output_row = output_row

        self.this_value = None

        self.populate_values()

    def populate_values(self):
        for rule in self.rules:
            self.this_value = None
            key = rule.output_fieldname
            # If grouping exploded rows, check if specific fields should be included/excluded
            if config.get("group_rows"):
                if self.output_row.group_role == "child":
                    if self.include_field(key, config.get("child_fields")):
                        self.run_processing(rule=rule)
                    else:
                        self.this_value = ""
                elif self.output_row.group_role == "parent":
                    if self.include_field(key, config.get("parent_fields")):
                        self.run_processing(rule=rule)
                    else:
                        self.this_value = ""
                else:
                    if self.include_field(key, config.get("ungrouped_fields")):
                        self.run_processing(rule=rule)
                    else:
                        self.this_value = ""
            # Otherwise just run everything
            else:
                self.run_processing(rule=rule)
            
            self.output_row.values.update({key: self.this_value})

    def include_field(self, key, fields):
        include = fields.get("include")
        column_names = fields.get("fields").split(", ")

        if include == True:
            if key in column_names:
                return True
            else:
                return False
        elif include == False:
            if key in column_names:
                return False
            else:
                return True

    def run_processing(self, rule):
        data = self.output_row.data
        for function in rule.mapping_functions:
            self.unpack_function(function, data)
            data = self.this_value

    def unpack_function(self, function=None, data=None, value_index=None):
        f = list(function.keys())[0]
        params = function.get(f)

        if not config.get("quiet"):
            print("Function: {}".format(f))

        if value_index is not None or (value_index == 0):
            self.this_value[value_index] = self.select_function(data, f, params)
        else:
            self.this_value = self.select_function(data, f, params)
        
        if not config.get("quiet"):
            print("Value: {}".format(self.this_value))

    def select_function(self, data, f, params):
        match f:
            case "for_each":
                if isinstance(data, list):
                    for sub_f in params:
                        value_index = 0
                        for value in data:
                            self.unpack_function(sub_f, value, value_index)
                            value_index += 1
                return self.this_value

            case "fallback":
                if data == None:
                    data = self.output_row.data
                    for sub_f in params:
                        self.unpack_function(sub_f, data)
                return self.this_value

            case "clean_html":
                return clean_html(data)

            case "collate_list":
                values = []
                if "," in params:
                    p = params[0].split[", "]
                    paths = [path.split(".") for path in p]
                    for path in paths:
                        values.extend(collate_list(data, path=path))
                else:
                    path = params[0].split(".")
                    values = collate_list(data, path=path)
                return values
            
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

            case "create_filename":
                suffix = params[0]
                return create_filename(data, suffix)

            case "first_match":
                paths = params[0].split(", ")
                return first_match(data, paths)
            
            case "format_string":
                string = params[0]
                inserts = params[1]
                required = False
                try:
                    if params[2] == "required":
                            required = True
                except IndexError:
                    pass
                inserts = inserts.split(", ")
                return format_string(data, string=string, inserts=inserts, required=required, explode_ordinal=self.output_row.explode_ordinal, record_pid=self.output_row.record_pid)

            case "hardcoded":
                value = params[0]
                if "explode_ordinal" in value:
                    modifer = None
                    if "+" in value:
                        modifier = int(value.split("+")[1])
                    if self.output_row.explode_ordinal:
                        value = int(self.output_row.explode_ordinal)
                    else:
                        value = 0
                    if modifier:
                        value += modifier
                return hardcode_value(value)

            case "literal":
                path = params[0].split(".")
                if self.output_row.explode_on in path:
                    ordinal = self.output_row.explode_ordinal
                else:
                    try:
                        ordinal = params[1]
                    except:
                        ordinal = None
                return literal(data, path=path, ordinal=ordinal)

            case "lookup":
                endpoint = params[0]
                irn = data

                if irn:
                    record = records.find_record(endpoint=endpoint, irn=int(irn))
                    if record:
                        return record.data

                return None

            case "map_value":
                return map_from_value(data, params)

            case "measurement_conversion":
                return measurement_conversion(data, params)

            case "must_match":
                authorities = [str(term).lower() for term in params[0].split(", ")]
                return must_match(data, authorities)

            case "set_priority":
                return process_quality_score(data)

            case "related":
                size = params[0]
                types = params[1]
                return related(data, size=size, types=types)

            case "use_config":
                # Special cases where part of the output file's metadata need to be called
                key = params[0]
                return use_config(key)

            case "use_group_labels":
                label = None
                if self.output_row.group_role == "parent":
                    label = params[0]
                elif self.output_row.group_role == "child":
                    label = params[1]
                elif not self.output_row.group_role:
                    label = params[2]
                return label