
class RelationshipOutput(Output):
    def __init__(self, label=None, fieldnames=None, rules=None):
        super().__init__(label, fieldnames, rules)

        self.object = rules.object
        self.subject = rules.subject
        self.operator = rules.operator

        self.sets = {}

    def create_sets(self):
        object_records = self.find_objects()
        for object_record in object_records:
            relationship_set = []
            object_comparator_value = self.prepare_value_for_comparison(object_record, self.object)
            relationship_set.extend([record.data.get("pid") for record in object_records if
                                     self.check_subjects_for_inclusion(record, object_comparator_value) == True])
            if len(relationship_set) > 0:
                object_pid = object_record.data.get("pid")
                memo[object_pid]["relationship_found"] = True
                self.sets.update({object_pid: relationship_set})

    def find_objects(self):
        return [i for i in memo if self.label in memo[i]["write_to"]]

    def prepare_value_for_comparison(self, record, rule):
        comparator_value = literal(record.data, rule.get("path"))
        if comparator_value:
            comparator_modified = self.modify_comparator_value(rule, comparator_value)

            if read_config("strip_relationship_values"):
                return comparator_modified.strip()

    def modify_comparator_value(self, comparator_rule, comparator_value):
        modifier = comparator_rule.get("modifier")

        match modifier:
            case "trim":
                modifier_value = comparator_rule.get("modifier_value")
                try:
                    int(modifier_value)
                except TypeError:
                    print("Modifier value must be integer")
                    return None
                if modifier_value > 0:
                    return comparator_value[modifier_value, -1]
                elif modifier_value < 0:
                    return comparator_value[0, modifier_value]

            case "capitalise":
                return comparator_value.capitalize()

            case "equals":
                modifier_value = comparator_rule.get("modifier_value")
                if comparator_value == modifier_value:
                    return True
                else:
                    return False

            case _:
                return comparator_value

    def check_subjects_for_inclusion(self, subject_record, object_comparator_value):
        subject_pid = subject_record.data.get("pid")
        if not memo[subject_pid].get("relationship_found"):
            subject_comparator_value = self.prepare_value_for_comparison(subject_record, self.subject)

            match self.operator:
                case "equals":
                    if subject_comparator_value == object_comparator_value:
                        memo[subject_pid]["relationship_found"] = True
                        return True

    def create_rows_from_sets(self):
        for object_pid in list(self.sets.keys()):
            object_record = records.find_record(pid=object_pid)
            for subject_pid in self.sets[object_pid]:
                subject_record = records.find_record(pid=subject_record)
                self.create_relationship_row(object_record, subject_record)

    def create_relationship_row(self, object_record, subject_record):
        relationship_row = OutputRow(**kwargs)
        self.rows.append(relationship_row.values)

'''
- resourceRelationship:
    output_type: relationship
    relationship:
        object:
            label: object
            path: identifier
            modifier: trim
            modifier_value: -2
        subject:
            label: subject
            path: identifier
            modifier: trim
            modifier_value: -2
        operator: equals
    fields:
      - resourceRelationshipID:
          - format_string:
              string: tepapa:collection/relationship/{}/{}/{}
              path: object.id, subject.id, ordinal
      - resourceID:
          - literal:
              path: object.pid
      - relationshipOfResourceID:
          - hardcoded:
              value: "[URL FOR THIS REL]"
      - relatedResourceID:
          - literal:
              path: subject.pid
      - relationshipofResource:
          - hardcoded:
              value: Same specimen.
      - relationshipAccordingTo:
          - literal:
              path: object.identification.i.identifiedBy.title
      - relationshipEstablishedDate:
          - literal:
              path: object.identification.i.dateIdentified
      - relationshipRemarks:
          - hardcoded:
              value: null

'''