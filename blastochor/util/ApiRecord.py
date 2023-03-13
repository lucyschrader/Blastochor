# -*- coding: utf-8 -*-

import json
from blastochor.settings.Settings import config
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

        # TODO: If a record points back to itself (eg identification to main object record) add a pointer to structure
        self.make_writable()

        if not config.get("quiet"):
            print("Record created: {e}, {i}".format(e=self.endpoint, i=self.irn))

    def make_writable(self):
        for output in mapping.outputs:
            label = output.label
            if output.endpoint == self.endpoint:
                self.structure.update({label: {"write": True, "pointers": []}})

                if not config.get("quiet"):
                    print("Record {p} will write to {o}".format(p=self.pid, o=label))

            else:
                self.structure.update({label: {"write": False, "pointers": None}})

    def relate_record(self, label, related_record_pid):
        # Associates this record with another ApiRecord using its pid
        self.structure.get(label).get("pointers").append(related_record_pid)

        if not config.get("quiet"):
            print("Record {p} will point to record {r}".format(p=self.pid, r=related_record_pid))