# -*- coding: utf-8 -*-

import json
from blastochor.settings.Settings import read_config, write_config
from blastochor.util.Memo import memo, add_to_record_memo, format_pid
from blastochor.settings.Stats import stats
from blastochor.util.Records import records
from blastochor.util import Writer

class ApiRecord():
    def __init__(self, data, endpoint):
        self.data = data
        self.endpoint = endpoint
        self.structure = {}
        self.pid = self.data.get("pid")
        self.irn = self.data.get("id")

        self.check_quality_score()

#        self.make_writable()

        if read_config("restrict_locality"):
            self.check_locality_restriction()

        if not read_config("quiet"):
            print("Record created: {e}, {i}".format(e=self.endpoint, i=self.irn))

    def check_quality_score(self):
        # If part of the primary harvest, save the upper and lower bounds of qualityScores for the result set
        if self.endpoint == read_config("endpoint"):
            quality_score = self.data.get("_meta").get("qualityScore")
            if quality_score:
                if not stats.quality_score_lower:
                    stats.quality_score_lower = quality_score
                else:
                    if quality_score < stats.quality_score_lower:
                        stats.quality_score_lower = quality_score
                if not stats.quality_score_upper:
                    stats.quality_score_upper = quality_score
                else:
                    if quality_score > stats.quality_score_upper:
                        stats.quality_score_upper = quality_score

    def make_writable(self):
        mapping = read_config("mapping")
        for output in mapping.outputs:
            label = output.label
            if output.endpoint == self.endpoint:
                memo[self.pid]["structure"].update({label: {"write": True, "extension_of": []}})

                if not config.get("quiet"):
                    print("Record {p} will write to {l}".format(p=self.pid, l=label))

            else:
                memo[self.pid]["structure"].update({label: {"write": False, "extension_of": None}})

    def relate_record(self, label, related_record_pid):
        # Associates this record with another ApiRecord using its pid
        self.structure.get(label).get("pointers").append(related_record_pid)

        if not read_config("quiet"):
            print("Record {p} will point to record {r}".format(p=self.pid, r=related_record_pid))

    def check_locality_restriction(self):
        # If restrict_locality is on, find event records that need to be redacted
        if self.endpoint == "object":
            try:
                event_id = self.data["evidenceFor"]["atEvent"]["id"]
            except KeyError:
                event_id = None

            if event_id:
                if self.data.get("restrictLocalityData"):
                    event_pid = add_to_record_memo(status=None, irn=event_id, endpoint="fieldcollection", label=None, extension=True, extends=None)
                    memo[event_pid]["restrict_locality"] = True

                event_pid = format_pid(endpoint="fieldcollection", irn=event_id)
                memo[self.pid]["associated_event"] = event_pid