from math import floor
import random
import nh3
from askCO import Resource
from src.setup.Settings import read_config
from src.monitoring.Stats import stats
from src.datastore.RecordStore import records


class ValueContainer():
    def __init__(self, output_row, rule):
        self.output_row = output_row
        self.rule = rule
        self.current_value = None
        self.reprocess = False
        self.complete = False

        self.run_functions()

    def run_functions(self):
        for function in self.rule.mapping_functions:
            if not self.complete:
                container = FunctionContainer(self.output_row,
                                              self.current_value,
                                              self.reprocess,
                                              function,
                                              None)
                self.current_value = container.current_value
                self.reprocess = container.reprocess
                self.complete = container.complete

        self.complete = True


class FunctionContainer():
    def __init__(self, output_row=None, current_value=None, reprocess=None, function=None, value_index=None):
        self.output_row = output_row
        self.current_value = current_value
        self.reprocess = reprocess
        self.function = function
        self.value_index = value_index
        self.complete = False

        self.unpack_function()

    def unpack_function(self):
        function_name = list(self.function.keys())[0]
        params = self.function[function_name]

        if not read_config("quiet"):
            print("Running function: {}".format(function_name))

        processed_function = FunctionProcessor(function_name,
                                               params,
                                               self.output_row,
                                               self.current_value,
                                               self.reprocess,
                                               self.value_index)

        self.current_value = processed_function.output_value
        self.reprocess = processed_function.reprocess
        self.complete = processed_function.complete


class FunctionProcessor:
    def __init__(self, function=None, params=None, output_row=None, input_value=None, reprocess=False, value_index=None):
        self.function = function
        self.params = params
        self.output_row = output_row
        self.data = self.output_row.data

        if not reprocess:
            self.input_value = self.data
        else:
            self.input_value = input_value

        self.output_value = None
        self.reprocess = True
        self.complete = False

        self.value_index = value_index

        self.select_function()

    def select_function(self):
        match self.function:
            case "continue_if":
                if literal(data=self.input_value, path=self.params["path"]) != self.params["condition"]:
                    self.complete = True
                self.reprocess = False

            case "for_each":
                if isinstance(self.input_value, list):
                    self.output_value = []
                    value = None
                    value_index = 0
                    for value in self.input_value:
                        subfunction_reprocess = True
                        for subfunction in self.params:
                            subfunction_container = FunctionContainer(self.output_row,
                                                                      value,
                                                                      subfunction_reprocess,
                                                                      subfunction,
                                                                      value_index)
                            value = subfunction_container.current_value
                            subfunction_reprocess = subfunction_container.reprocess
                            subfunction_complete = subfunction_container.complete

                            if isinstance(value, list):
                                value = concatenate(value)

                        self.output_value.append(value)
                        value_index += 1

            case "fallback":
                if self.input_value is not None or (self.input_value == 0):
                    self.output_value = self.input_value
                else:
                    subfunction_reprocess = False
                    value = None
                    for subfunction in self.params:
                        subfunction_container = FunctionContainer(self.output_row,
                                                                  value,
                                                                  subfunction_reprocess,
                                                                  subfunction,
                                                                  None)
                        value = subfunction_container.current_value
                        subfunction_reprocess = subfunction_container.reprocess
                        subfunction_complete = subfunction_container.complete

                    self.output_value = value

            case "clean_html":
                self.output_value = clean_html(data=self.input_value)

            case "collate_list":
                path_param = self.params["path"]
                if "," in path_param:
                    self.output_value = []
                    paths = path_param.split(", ")
                    for path in paths:
                        path_values = collate_list(data=self.input_value,
                                                   path=path)
                        if path_values:
                            self.output_value.extend(path_values)
                else:
                    self.output_value = collate_list(data=self.input_value,
                                                     path=path_param)

            case "concatenate":
                self.output_value = concatenate(data=self.input_value)

            case "conditional":
                value_path = self.params["path"].split(".")
                condition_path = self.params["condition_path"].split(".")
                condition_values = self.params["match"].split("|")
                fallback_values = self.params.get("fallback_match")
                self.output_value = conditional_inclusion(data=self.input_value,
                                                          value_path=value_path,
                                                          condition_path=condition_path,
                                                          condition_values=condition_values,
                                                          fallback_values=fallback_values)

            case "country_code":
                path = self.params["path"]
                self.output_value = country_code(data=self.input_value,
                                                 path=path)

            case "create_filename":
                suffix = self.params["suffix"]
                self.output_value = create_filename(data=self.input_value,
                                                    suffix=suffix)

            case "first_match":
                paths = self.params["path"].split(", ")
                self.output_value = first_match(data=self.input_value,
                                                paths=paths)

            case "format_string":
                string = self.params["string"]
                paths = self.params["path"].split(", ")
                required = self.params.get("required")
                strip = self.params.get("strip")
                ordinal = self.output_row.explode.get("explode_ordinal")
                record_pid = self.output_row.pid
                self.output_value = format_string(data=self.input_value,
                                                  string=string,
                                                  paths=paths,
                                                  required=required,
                                                  strip=strip,
                                                  ordinal=ordinal,
                                                  record_pid=record_pid)

            case "hardcoded":
                value = self.params["value"]
                if value == "ordinal":
                    modifier = self.params.get("ordinal_modifier")
                    if self.output_row.explode.get("explode_ordinal"):
                        value = int(self.output_row.explode.get("explode_ordinal"))
                    else:
                        value = 0
                    if modifier:
                        value += modifier
                self.output_value = hardcode_value(value)

            case "identification_qualifier":
                taxon_path = self.params["taxon_path"]
                qualifier_path = self.params["qualifier_path"]
                ordinal = self.params.get("ordinal")
                if not ordinal and (ordinal != 0):
                    ordinal = self.output_row.explode.get("explode_ordinal")
                self.output_value = format_identification_qualifier(data=self.input_value,
                                                                    taxon_path=taxon_path,
                                                                    qualifier_path=qualifier_path,
                                                                    ordinal=ordinal)

            case "literal":
                path = self.params["path"].split(".")
                if self.output_row.explode.get("explode_on") in path:
                    ordinal = self.output_row.explode.get("explode_ordinal")
                elif self.value_index is not None or (self.value_index == 0):
                    ordinal = self.value_index
                else:
                    ordinal = self.params.get("ordinal")
                self.output_value = literal(data=self.input_value,
                                            path=path,
                                            ordinal=ordinal)

            case "lookup":
                endpoint = self.params["endpoint"]
                lookup_record = records.find_record(irn=self.input_value,
                                                    endpoint=endpoint)
                if lookup_record:
                    self.output_value = lookup_record.data
                else:
                    self.output_value = None

            case "map_value":
                self.output_value = map_from_value(data=self.input_value,
                                                   mappings=self.params)

            case "must_match":
                authorities = [str(term).lower() for term in self.params["terms"].split(", ")]
                self.output_value = must_match(data=self.input_value,
                                               authorities=authorities)

            case "related":
                size = self.params["size"]
                types = self.params["types"]
                self.output_value = get_related(data=self.input_value,
                                                size=size,
                                                types=types)

            case "set_priority":
                self.output_value = process_quality_score(data=self.input_value)

            case "truncate":
                length = self.params["length"]
                suffix = self.params.get("suffix")
                self.output_value = truncate_value(data=self.input_value,
                                                   length=length,
                                                   suffix=suffix)

            case "use_config":
                key = self.params["key"]
                self.output_value = read_config(key)

            case "use_group_labels":
                label = None
                if self.output_row.group_role == "parent":
                    label = self.params["parent"]
                elif self.output_row.group_role == "child":
                    label = self.params["child"]
                elif not self.output_row.group_role:
                    label = self.params["other"]
                self.output_value = label


def split_path(path):
    # Ensure paths are lists that can be iterated through
    if not isinstance(path, list):
        path = path.split(".")
    return path


def handle_iterator_in_path(path=None, ordinal=None):
    # Replace the list indicator 'i' in a path with a specified ordinal to create a navigable path
    # If no ordinal provided, defaults to first item in the list
    if isinstance(path, list):
        if "i" in path:
            if not ordinal:
                ordinal = 0

            path = [ordinal if item == "i" else item for item in path]

    return path


def step_to_field(data=None, path=None):
    # Step through a record to provide a subsection or value
    if data:
        if isinstance(path, str):
            return data.get(path)
        else:
            step = data
            for field in path:
                try:
                    step = step[field]
                except (KeyError, IndexError):
                    return None
            return step
    else:
        return None


def clean_html(data=None):
    if data:
        value = nh3.clean(data)
    else:
        value = None

    return value


def collate_list(data=None, path=None):
    # Look through each child path of a list and collate all values of child fields with the same name
    # Currently only works for one level of list
    path = split_path(path)
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
    app_limit = read_config("max_list_size")
    if app_limit:
        if 0 < app_limit < iterator_limit:
            iterator_limit = app_limit

    for i in range(0, iterator_limit):
        value = literal(data, path=path, ordinal=i)
        values.append(value)

    if len(values) == 0:
        values = None

    return values


def concatenate(data=None):
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


def conditional_inclusion(data, value_path, condition_path, condition_values, fallback_values):
    # Return a value if another field matches a specified value
    # Both paths must be in the same section of the record
    # For example, find related.i.contentUrl if related.i.title is "ORCID"
    if "i" in condition_path:
        list_to_check = collate_list(data, path=condition_path)
        if not list_to_check:
            return None
        else:
            found_values = []
            returned_value_index = 0
            for returned_value in list_to_check:
                if returned_value in condition_values:
                    found_values.append(literal(data, path=value_path, ordinal=returned_value_index))
                returned_value_index += 1
            if len(found_values) == 0:
                if fallback_values:
                    fallback_values = fallback_values.split("|")
                    returned_value_index = 0
                    for returned_value in list_to_check:
                        if returned_value in fallback_values:
                            found_values.append(literal(data, path=value_path, ordinal=returned_value_index))
                        returned_value_index += 1
    else:
        returned_value = literal(data, path=condition_path)
        if not returned_value:
            return None
        else:
            found_values = []
            if returned_value in condition_values:
                found_values.append(literal(data, path=value_path))
            if len(found_values) == 0:
                if fallback_values:
                    fallback_values = fallback_values.split("|")
                    if returned_value in fallback_values:
                        found_values.append(literal(data, path=value_path))

    # Return a single value if there is only one match, a list if there are multiple, None if there aren't any
    if len(found_values) == 0:
        return None
    elif len(found_values) == 1:
        return found_values[0]
    else:
        return found_values


def country_code(data, path):
    country = literal(data, path)
    if country:
        country_lookup = next(filter(lambda country_dict: country_dict.get("Name") == country,
                                     read_config("country_codes")), None)
        if country_lookup:
            return country_lookup.get("Code")

    return None


def create_filename(data, suffix):
    # Remove unsafe characters from a string to form a usable filename
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


def extend_value(data, length, string):
    # Extend a value to a specified length using a provided string
    if len(data) < length:
        return data + string


def first_match(data, paths):
    value = None
    for path in paths:
        path = split_path(path)
        if "i" in path:
            value = collate_list(data, path)
        else:
            value = literal(data, path)
        if value:
            return value

    return None


def format_identification_qualifier(data, taxon_path, qualifier_path, ordinal):
    # Special formatter for GBIF export (identificationQualifier field)
    taxon_id = literal(data, path=taxon_path, ordinal=ordinal)
    if taxon_id:
        taxon_record = records.find_record(endpoint="taxon", irn=taxon_id)
        if taxon_record:
            fields = ["subspecies", "species", "genus"]
            name = None
            for field in fields:
                if taxon_record.data.get(field):
                    name = taxon_record.data.get(field)
                    break

            if name:
                qualifier = literal(data, path=qualifier_path, ordinal=ordinal)
                if qualifier:
                    if qualifier in ["?", "s.l.", "s.s.", "pro. hyb.", "pro. sp.", "cv.", "sp. nov.", "sp. nov.?",
                                     "prob."]:
                        return "{n} {q}".format(n=name, q=qualifier)
                    elif qualifier in ["aff.", "cf."]:
                        return "{q} {n}".format(q=qualifier, n=name)
        else:
            if not read_config("quiet"):
                print("No record found for taxon record {}".format(taxon_id))

    return None


def format_string(data, string=None, paths=None, required=False, strip=None, ordinal=None, record_pid=None):
    # Find a value and incorporate it into a specified string
    values = []
    for path in paths:
        if path == "parent_id":
            if record_pid:
                record_id = record_pid.split("/")[-1]
                values.append(record_id)
            else:
                values.append("")
        elif path == "explode_ordinal":
            # Used for Google Arts orderid (index starts at 1)
            values.append(ordinal + 1)
        else:
            value = literal(data=data, path=path, ordinal=ordinal)
            if not value:
                if required:
                    continue
                else:
                    value = ""
            values.append(value)

    if required:
        spaces = string.count("{}")
        if len(values) != spaces:
            return None

    if strip:
        values = [value.replace(strip, "") for value in values]

    return string.format(*values)


def get_related(data, size, types):
    # Make a fresh query to the special /related endpoint for the current record
    endpoint = data.get("href").split("/")[-2]
    irn = data.get("id")

    query = Resource(
        quiet=read_config("quiet"),
        api_key=read_config("api_key"),
        timeout=read_config("timeout"),
        attempts=read_config("attempts"),
        sleep=0.1,
        endpoint=endpoint,
        irn=irn,
        related=True,
        size=size,
        types=types)

    query.send_query()
    stats.api_call_count += 1

    return query.records


def hardcode_value(value):
    # Return a specified string
    return value


def literal(data, path, ordinal=None):
    # Find a given path in a record and return the literal value
    path = split_path(path)
    path = handle_iterator_in_path(path=path, ordinal=ordinal)
    value = step_to_field(data=data, path=path)
    return value


def map_from_value(data, mappings):
    # If a specified value is present, map to a provided string
    if isinstance(data, list):
        mapped_value = []
        for value in data:
            mapped_value.append(mappings.get(value))
    else:
        mapped_value = mappings.get(data)

    return mapped_value


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
    # Turns a record's qualityScore into an integer from 1-500
    # Used to assign priority in Google Arts & Culture
    priority = None

    if stats.quality_score_lower and stats.quality_score_upper:
        try:
            quality_score = data["_meta"]["qualityScore"]
            score = quality_score - stats.quality_score_lower
            upper = stats.quality_score_upper - stats.quality_score_lower

            score_percentage = score / upper * 100
            score_percentage = 100 - score_percentage

            priority = floor(score_percentage * 3)
            modifier = random.randint(-15, 15)
            priority = priority + modifier

            if priority <= 0:
                priority = random.randint(1, 200)

        except KeyError:
            pass

    return priority


def truncate_value(data, length, suffix):
    # Truncate a value to a specified length, with an optional suffix (eg "...")
    if isinstance(data, str):
        if len(data) > length:
            if suffix:
                suffix_length = len(suffix)
                string_length = length - suffix_length
                value = data[:string_length]
                value += suffix
            else:
                value = data[:length]

            return value

        else:
            return data

    else:
        return None
