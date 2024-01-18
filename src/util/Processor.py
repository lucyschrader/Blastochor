from src.setup.Settings import read_config
from src.util.ProcessingFunctions import ValueContainer, literal


class RowProcessor():
    def __init__(self, rules, output_row, requires):
        self.rules = rules
        self.output_row = output_row

        if requires:
            if not self.check_requirements(requires):
                self.output_row.write_out = False

        if self.output_row.write_out:
            self.run_field_processing()

    def check_requirements(self, requires):
        for requirement in requires:
            requirement_value = requirement["condition"]
            row_value = literal(data=self.output_row.data,
                                path=requirement["path"].split("."),
                                ordinal=self.output_row.explode.get("explode_ordinal"))
            if isinstance(requirement_value, bool):
                if requirement_value:
                    if not row_value:
                        return False
                elif not requirement_value:
                    if row_value:
                        return False

            elif row_value != requirement_value:
                return False

        return True

    def run_field_processing(self):
        for rule in self.rules:
            value = None
            fieldname = rule.output_fieldname
            if read_config("group_rows"):
                if self.check_for_inclusion(fieldname):
                    value = ValueContainer(rule=rule, output_row=self.output_row).current_value
            else:
                value = ValueContainer(rule=rule, output_row=self.output_row).current_value

            if not value and (value != 0):
                value = ""

            self.output_row.values.update({fieldname: value})

    def check_for_inclusion(self, fieldname):
        # If grouping exploded rows, check if specific fields should be included/excluded
        row_role = self.output_row.group_role
        match row_role:
            case "child":
                fields = "child_fields"
            case "parent":
                fields = "parent_fields"
            case _:
                fields = "ungrouped_fields"

        if include_field(fieldname, read_config(fields)):
            return True


def include_field(fieldname, fields):
    include = fields.get("include")
    column_names = fields.get("fields").split(", ")

    if include:
        if fieldname in column_names:
            return True
    elif not include:
        if fieldname not in column_names:
            return True
