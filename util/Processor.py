# -*- coding: utf-8 -*-

from Blastochor import app

class ValueProcessor():
    def __init__(self):
        pass

    def run_processing(self, data, rule):
        value = None
        holding_value = None

        for f in rule.mapping_functions:
            function = f.split(":")[0]
            params = f.split(":")[1]

            if function == "for_each":



        return value

    def select_function(self, function, data, params):
        match function:
            case "points_to":
                value = self.points_to(data, params)

            case "lookup":
                value = self.lookup(data, params)

            case "literal":
                value = self.literal(data, params)

            case "hardcoded":
                value = self.hardcode_value(params)

            case "collate_list":
                value = self.collate_list(data, params)

            case "concatenate":
                value = self.concatenate_list(data)

            case "conditional":
                value = self.conditional_inclusion(data, params)

            case "country_code":
                value = self.country_code(data, params)

    def lookup(self, data, params):
        p = params.split(", ")
        endpoint = p[0]
        path = p[1].split(".")
        lookup_irn = self.step_to_field(data, path)
        value = app.records.find_record(endpoint, irn)
        return value

    def literal(self, data, path):
        path = path.split(".")
        value = self.step_to_field(data, path)
        return value

    def hardcode_value(self, value):
        return value

    def format_string(self, data, params):
        p = params.split(", ")
        string = p[0]
        if string == "url":
            string == "https://data.tepapa.govt.nz/collection/object/{}"
        field = p[1]
        value = data.get(field)
        return string.format(value)

    def collate_list(self, data, params):
        p = params.split(", ")
        path = p[0].split(".")
        ordinal = None
        if len(p) == 2:
            ordinal = p[1]

        parent_path = []
        child_path = []
        parent_flag = True
        for field in path:
            if field == "i":
                parent_flag = False
                continue
            if parent_flag == True:
                parent_path.append(field)
            elif parent_flag == False:
                child_path.append(field)
        parent_data = step_to_field(data, parent_path)

        values = []
        if ordinal:
            iterator_path = [ordinal] + child_path
            values.append(step_to_field(parent_data, iterator_path))
        else:
            for i in len(parent_data):
                iterator_path = [i] + child_path
                values.append(step_to_field(parent_data, iterator_path))

        return values

    def concatenate_list(self, data):
        value = data.join(" | ")
        return value

    def change_title_length(self):
        pass

    def clean_description(self):
        pass

    def process_quality_score(self):
        pass

    def measurements_inch_to_mm(self):
        pass

    def fixed_vocab(self, data, params):
        pass

    def country_code(self, data, params):
        pass

    def conditional_inclusion(self, data, params):
        p = params.split[", "]
        value = data.get(p[0])
        check = p[1].split("=")
        check_field = check[0]
        check_value = check[1]
        if data.get(check_field) == check_value:
            return value
        return None

    def prioritised_inclusion(self, data, params):
        value = None
        fields = params.split(", ")
        for field in fields:
            field = field.split(".")
            if value is not None:
                return value
                value = self.step_to_field(data, field)

        return value

    def step_to_field(self, step, path):
        for i in path:
            if isinstance(i, int):
                try:
                    child = step[i]:
                except:
                    return None
            elif isinstance(i, str):
                child = step.get(i)
        if step is not None:
            return step
        else:
            return None