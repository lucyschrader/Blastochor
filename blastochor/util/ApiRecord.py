# -*- coding: utf-8 -*-

import json
from blastochor.settings.Settings import config
from blastochor.settings.Stats import stats
from blastochor.util.Mapper import mapping
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

        if not config.get("quiet"):
            print("Record created: {e}, {i}".format(e=self.endpoint, i=self.irn))

    def check_quality_score(self):
        # If part of the primary harvest, save the upper and lower bounds of qualityScores for the result set
        if self.endpoint == config.get("endpoint"):
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
        for output in mapping.outputs:
            label = output.label
            if output.endpoint == self.endpoint:
                config["record_memo"][self.pid]["structure"].update({label: {"write": True, "extension_of": []}})

                if not config.get("quiet"):
                    print("Record {p} will write to {l}".format(p=self.pid, l=label))

            else:
                config["record_memo"][self.pid]["structure"].update({label: {"write": False, "extension_of": None}})

    def relate_record(self, label, related_record_pid):
        # Associates this record with another ApiRecord using its pid
        self.structure.get(label).get("pointers").append(related_record_pid)

        if not config.get("quiet"):
            print("Record {p} will point to record {r}".format(p=self.pid, r=related_record_pid))