# -*- coding: utf-8 -*-

import requests
import time
import json
from math import floor
import random
import re
import htmllaundry

from blastochor.settings.Settings import config
from blastochor.settings.Stats import stats
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
    if data:
        value = htmllaundry.sanitize(data)
    else: value = None

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

def conditional_inclusion(data, value_path, check_path, check_values):
    # Return a value if another field matches a specified value
    # Both paths must be in the same section of the record
    # For example, find related.i.contentUrl if related.i.title == "ORCID"
    if "i" in check_path:
        check_list = collate_list(data, path=check_path)
        if not check_list:
            return None
        else:
            conditional_values = []
            for check_value in check_values:
                if check_value in check_list:
                    ordinal = check_list.index(check_value)
                    conditional_values.append(literal(data, path=value_path, ordinal=ordinal))

    else:
        check = literal(data, path=check_path)
        if not check:
            return None
        else:
            conditional_values = []
            for check_value in check_values:
                if check == check_value:
                    conditional_values.append(literal(data, path=value_path))

    # Return a list if there are multiple matches, otherwise just a single value
    if len(conditional_values) == 1:
        return conditional_values[0]
    else:
        return conditional_values

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
        if path.startswith("explode_ordinal"):
            if "+" in path:
                modifier = int(path.split("+")[1])
                explode_ordinal += modifier
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
    
    if config.get("rate_limited"):
        time.sleep(0.1)

    return results

def use_config(key):
    return config.get(key)

def truncate_value(data, string_length, suffix):
    # Truncate a value to a specified length, with an optional suffix (eg "...")
    if isinstance(data, str):
        if len(data) > string_length:
            if suffix:
                suffix_length = len(suffix)
                string_length = string_length - suffix_length
                value = data[:string_length]
                value += suffix
            else:
                value = data[:string_length]

            return value
        
        else:
            return data

    else:
        return None

def value_extend(data, params):
    # Extend a value to a specified length using a provided string
    pass

class RowProcessor():
    def __init__(self, rules, output_row):
        self.rules = rules
        self.output_row = output_row

        self.this_value = None

        if output_row.requires:
            self.check_requirements(output_row)

        if output_row.meets_requirement == False:
            pass
        else:
            self.populate_values()

    def check_requirements(self, output_row):
        for requirement in output_row.requires.keys():
            requirement_value = output_row.requires[requirement]
            requirement_path = requirement.split(".")
            row_value = literal(data=output_row.data, path=requirement_path, ordinal=output_row.explode_ordinal)
            if row_value != requirement_value:
                output_row.meets_requirement = False

    def populate_values(self):
        for rule in self.rules:
            self.this_value = None
            key = rule.output_fieldname
            # If grouping exploded rows, check if specific fields should be included/excluded
            if config.get("group_rows"):
                if self.output_row.group_role == "child":
                    if self.include_field(key, config.get("child_fields")):
                        self.this_value = ValueProcessor(rule=rule, output_row=self.output_row).this_value
                    else:
                        self.this_value = ""
                elif self.output_row.group_role == "parent":
                    if self.include_field(key, config.get("parent_fields")):
                        self.this_value = ValueProcessor(rule=rule, output_row=self.output_row).this_value
                    else:
                        self.this_value = ""
                else:
                    if self.include_field(key, config.get("ungrouped_fields")):
                        self.this_value = ValueProcessor(rule=rule, output_row=self.output_row).this_value
                    else:
                        self.this_value = ""
            # Otherwise just run everything
            else:
                self.this_value = ValueProcessor(rule=rule, output_row=self.output_row).this_value
            
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

class ValueProcessor():
    def __init__(self, rule=None, output_row=None):
        self.rule = rule
        self.output_row = output_row
        self.this_value = None
        self.reprocess = False

        for function in self.rule.mapping_functions:
            processed_function = self.unpack_function(function=function)
            self.this_value = processed_function.output_value
            self.reprocess = processed_function.reprocess

    def unpack_function(self, function=None):
        function_name = list(function.keys())[0]
        params = function.get(function_name)
        
        if not config.get("quiet"):
            print("Running function: {}".format(function_name))

        return FunctionProcessor(function=function_name, params=params, input_value=self.this_value, output_row=self.output_row, reprocess=self.reprocess)

class FunctionProcessor():
    def __init__(self, function=None, params=None, input_value=None, output_row=None, reprocess=False, value_index=None):
        self.function = function
        self.params = params
        self.output_row = output_row
        self.data = self.output_row.data

        if reprocess == False:
            self.input_value = self.data
        else:
            self.input_value = input_value

        self.output_value = None
        self.reprocess = True

        self.value_index = value_index

        self.select_function()

    def select_function(self):
        match self.function:

            case "for_each":
                if isinstance(self.input_value, list):
                    self.output_value = []
                    value_index = 0
                    for value in self.input_value:
                        sub_f_reprocess = True
                        for sub_f in self.params:
                            processed_sub_f = self.unpack_function(function=sub_f, input_value=value, output_row=self.output_row, reprocess=sub_f_reprocess, value_index=value_index)
                            value = processed_sub_f.output_value
                            sub_f_reprocess = processed_sub_f.reprocess

                        self.output_value.append(value)
                        value_index += 1

                        #print("Post-subfunction value: {}".format(self.output_value))

            case "fallback":
                if self.input_value is not None or (self.input_value == 0):
                    self.output_value = self.input_value
                else:
                    sub_f_reprocess = False
                    for sub_f in self.params:
                        processed_sub_f = self.unpack_function(function=sub_f, input_value=None, output_row=self.output_row, reprocess=sub_f_reprocess, value_index=self.value_index)
                        self.output_value = processed_sub_f.output_value
                        sub_f_reprocess = processed_sub_f.reprocess

                #print("Post-fallback value: {}".format(self.output_value))

            case "clean_html":
                self.output_value = clean_html(self.input_value)

            case "collate_list":
                if "," in self.params[0]:
                    self.output_value = []
                    p = self.params[0].split(", ")
                    paths = [path.split(".") for path in p]
                    for path in paths:
                        path_list = collate_list(self.input_value, path=path)
                        if path_list:
                            self.output_value.extend(path_list)
                else:
                    path = self.params[0].split(".")
                    self.output_value = collate_list(self.input_value, path=path)
            
            case "concatenate":
                self.output_value = concatenate_list(self.input_value)

            case "conditional":
                value_path = self.params[0].split(".")
                check_param = self.params[1].split("=")
                check_path = check_param[0].split(".")
                check_values = check_param[1].split("|")
                self.output_value = conditional_inclusion(self.input_value, value_path=value_path, check_path=check_path, check_values=check_values)

            case "country_code":
                path = self.params[0].split(".")
                self.output_value = country_code(self.input_value, path)

            case "create_filename":
                suffix = self.params[0]
                self.output_value = create_filename(self.input_value, suffix)

            case "first_match":
                paths = self.params[0].split(", ")
                self.output_value = first_match(self.input_value, paths)
            
            case "format_string":
                string = self.params[0]
                inserts = self.params[1]
                required = False
                try:
                    if self.params[2] == "required":
                            required = True
                except IndexError:
                    pass
                inserts = inserts.split(", ")

                self.output_value = format_string(self.input_value, string=string, inserts=inserts, required=required, explode_ordinal=self.output_row.explode_ordinal, record_pid=self.output_row.record_pid)

            case "hardcoded":
                value = self.params[0]
                if "explode_ordinal" in value:
                    modifier = None
                    if "+" in value:
                        modifier = int(value.split("+")[1])
                    if self.output_row.explode_ordinal:
                        value = int(self.output_row.explode_ordinal)
                    else:
                        value = 0
                    if modifier:
                        value += modifier
                self.output_value = hardcode_value(value)

            case "literal":
                path = self.params[0].split(".")
                if self.output_row.explode_on in path:
                    ordinal = self.output_row.explode_ordinal
                elif self.value_index is not None or (self.value_index == 0):
                    ordinal = self.value_index
                else:
                    try:
                        ordinal = self.params[1]
                    except IndexError:
                        ordinal = None
                self.output_value = literal(self.input_value, path=path, ordinal=ordinal)

            case "lookup":
                endpoint = self.params[0]

                if self.input_value:
                    record = records.find_record(endpoint=endpoint, irn=int(self.input_value))
                    if record:
                        self.output_value = record.data

            case "map_value":
                self.output_value = map_from_value(self.input_value, self.params)

            case "measurement_conversion":
                self.output_value = measurement_conversion(self.input_value, self.params)

            case "must_match":
                authorities = [str(term).lower() for term in self.params[0].split(", ")]
                self.output_value = must_match(self.input_value, authorities)

            case "set_priority":
                self.output_value = process_quality_score(self.input_value)

            case "related":
                size = self.params[0]
                types = self.params[1]
                self.output_value = related(self.input_value, size=size, types=types)

            case "truncate":
                string_length = self.params[0]
                try:
                    suffix = self.params[1]
                except IndexError:
                    suffix = None

                self.output_value = truncate_value(self.input_value, string_length=string_length, suffix=suffix)

            case "use_config":
                # Special cases where part of the output file's metadata need to be called
                key = params[0]
                self.output_value = use_config(key)

            case "use_group_labels":
                label = None
                if self.output_row.group_role == "parent":
                    label = self.params[0]
                elif self.output_row.group_role == "child":
                    label = self.params[1]
                elif not self.output_row.group_role:
                    label = self.params[2]
                self.output_value = label

    def unpack_function(self, function=None, input_value=None, output_row=None, reprocess=False, value_index=None):
        function_name = list(function.keys())[0]
        params = function.get(function_name)
    
        if not config.get("quiet"):
            print("Running function: {}".format(function_name))

        return FunctionProcessor(function=function_name, params=params, input_value=input_value, output_row=output_row, reprocess=reprocess, value_index=value_index)