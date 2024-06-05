import yaml


class ConfigValidator():
    def __init__(self, config):
        self.config = config
        self.validation = load_validation("config")
        self.quiet = self.config.get("quiet")
        self.fail = False
        self.report = ["Validation report for config"]

        self.validate_keys()

        print_report("config", self.report, self.fail, self.quiet)

    def validate_keys(self):
        for key in self.validation["required"]:
            self.validate_key(key, "config", required=True)
        for key in self.validation["optional"]:
            self.validate_key(key, "optional")
        if self.config["group_rows"]:
            for key in self.validation["group"]:
                self.validate_key(key, "group", required=True)
        for key in self.validation["mode"][self.config["mode"]]:
            self.validate_key(key["key"], "mode", required=key["required"])
        for key in self.validation["filter"]:
            self.validate_key(key, "filter", parent="filter")

    def validate_key(self, key, key_type, required=False, parent=None):
        # Check if the config's required keys are present
        # Note this does not check the values of those keys
        if parent:
            check_list = self.config[parent]
        else:
            check_list = list(self.config.keys())
        present = False
        if key in check_list:
            present = True
        self.save_validation(key, key_type, required, present)

    def save_validation(self, key, key_type, required, present):
        message = None
        if present:
            if required:
                message = "Required {kt} key found: {k}".format(kt=key_type, k=key)
            else:
                message = "{kt} key found: {k}".format(kt=key_type.capitalize(), k=key)
        else:
            if required:
                self.fail = True
                message = "Missing required {kt} key: {k} not in config".format(kt=key_type, k=key)
            else:
                message = "Missing {kt} key: {k} not in config".format(kt=key_type.capitalize(), k=key)
        if message:
            self.report.append(message)


class MapValidator():
    def __init__(self, map_data, quiet, country_codes):
        self.map_data = map_data
        self.label = None
        self.validation = load_validation("map")
        self.functions = load_validation("functions")
        self.quiet = quiet
        self.country_codes = country_codes
        self.fail = False
        self.report = []

        self.validate_map()

        print_report("map", self.report, self.fail, self.quiet, self.label)

    def validate_map(self):
        if self.map_data.get("label"):
            self.label = self.map_data["label"]
            self.report.append("Validation report for map {}".format(self.map_data["label"]))
        else:
            self.fail = True
            self.report.append("Error: No label for this map.")

        for key in self.validation["required"]:
            self.validate_key(key, "map", required=True)
        for key in self.validation["optional"]:
            self.validate_key(key, "map")
        for key in self.validation["extension_keys"]:
            if self.map_data.get("extend"):
                for extension in self.map_data["extend"]:
                    self.validate_key(key, "extension", required=True, parent=extension)
        for key in self.validation["requires_keys"]:
            if self.map_data.get("requires"):
                for requirement in self.map_data["requires"]:
                    self.validate_key(key, "requires", required=True, parent=requirement)

        self.validate_fields()

    def validate_key(self, key, key_type, required=False, parent=None):
        # Check if the config's required keys are present
        # Note this does not check the values of those keys
        if parent:
            check_list = list(parent.keys())
        else:
            check_list = list(self.map_data.keys())
        present = False
        if key in check_list:
            present = True
        self.save_validation(key, key_type, required, present)

    def save_validation(self, key, key_type, required, present):
        message = None
        if present:
            if required:
                message = "Required {kt} key found: {k}".format(kt=key_type, k=key)
            else:
                message = "{kt} key found: {k}".format(kt=key_type.capitalize(), k=key)
        else:
            if required:
                self.fail = True
                message = "Missing required {kt} key: {k} not in map".format(kt=key_type, k=key)
            else:
                message = "Missing {kt} key: {k} not in map".format(kt=key_type.capitalize(), k=key)
        if message:
            self.report.append(message)

    def validate_fields(self):
        # Check each field against validation
        field_index = 1
        for field in self.map_data["fields"]:
            field_name = list(field.keys())[0]
            for function in field[field_name]:
                self.validate_function(field_name, field_index, function)
            field_index += 1

    def validate_function(self, field_name, field_index, function):
        function_name = list(function.keys())[0]
        # Check that the field's functions are valid and has suitable parameters
        if function_name == "for_each":
            message = "Field {i} ({n}): Function for_each contains subfunctions".format(i=field_index,
                                                                                        n=field_name)
            self.report.append(message)
            for subfunction in function[function_name]:
                self.validate_function(field_name, field_index, subfunction)
        elif function_name == "fallback":
            message = "Field {i} ({n}): Function fallback contains fallback functions".format(i=field_index,
                                                                                              n=field_name)
            self.report.append(message)
            for fallback_function in function[function_name]:
                self.validate_function(field_name, field_index, fallback_function)
        else:
            if function_name in self.functions:
                # Country code function requires file to be loaded
                if function_name == "country_code":
                    if not self.country_codes:
                        self.fail = True
                        message = "Field {i} ({n}): Required country codes have not been loaded".format(i=field_index,
                                                                                                        n=field_name)
                        self.report.append(message)

                valid_params = self.functions[function_name]["parameters"]
                if function.get(function_name):
                    field_params = list(function[function_name].keys())
                    for param_key in field_params:
                        self.validate_parameter(field_name,
                                                field_index,
                                                function_name,
                                                valid_params,
                                                param_key)
                    if valid_params:
                        for valid_param in valid_params:
                            if valid_param.get("required"):
                                self.check_for_required_params(field_name,
                                                               field_index,
                                                               function_name,
                                                               valid_param,
                                                               field_params)
                else:
                    self.report.append("Field {i} ({n}): Function has no parameters".format(i=field_index,
                                                                                            n=field_name))

            else:
                self.fail = True
                self.report.append("Field {i} ({n}): Function {f} is not a valid function".format(i=field_index,
                                                                                                  n=field_name,
                                                                                                  f=function_name))

    def validate_parameter(self, field_name, field_index, function_name, valid_params, param_key):
        if valid_params:
            if param_key in [i["parameter"] for i in valid_params]:
                # Decide whether to check if the parameter value itself is valid
                pass
            else:
                self.fail = True
                message = "Field {i} ({n}): {p} is not a valid parameter for function {f}".format(i=field_index,
                                                                                                  n=field_name,
                                                                                                  p=param_key,
                                                                                                  f=function_name)
                self.report.append(message)

    def check_for_required_params(self, field_name, field_index, function_name, valid_param, field_params):
        valid_parameter_key = valid_param["parameter"]
        if valid_parameter_key in field_params:
            pass
        else:
            self.fail = True
            message = "Field {i} ({n}): function {f} is missing required parameter {p}".format(i=field_index,
                                                                                               n=field_name,
                                                                                               f=function_name,
                                                                                               p=valid_parameter_key)
            self.report.append(message)


def load_validation(validation_type):
    validation_file = "src/resources/validation/{}-validation.yaml".format(validation_type)
    try:
        with open(validation_file, "r", encoding="utf-8") as f:
            validation = yaml.safe_load(f)

            return validation
    except FileNotFoundError:
        raise FileNotFoundError("No validation yaml found")


def print_report(report_type, report, fail, quiet, label=None):
    if not label:
        label = ""
    if fail:
        print("{} NOT VALID - REVIEW AND TRY AGAIN".format(report_type.upper()))
        report_filename = report_type + label + "validationreport.txt"
        with open(report_filename, "w+", encoding="utf-8") as f:
            f.write("\n".join(report))

    if not quiet:
        for line in report:
            print(line)
