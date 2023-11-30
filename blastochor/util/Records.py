# -*- coding: utf-8 -*-

from blastochor.settings.Settings import read_config


class Records():
    def __init__(self):
        self.records = {}

    def append(self, record):
        this_pid = record.pid
        self.records.update({this_pid: record})

    def find_record(self, endpoint, irn):
        this_pid = "tepapa:collection/{e}/{i}".format(e=endpoint, i=irn)
        return self.records.get(this_pid)

    def find_record_list(self, endpoint, irn):
        # Find record with this endpoint, irn and return it
        this_record = next(filter(lambda record: record.endpoint == endpoint and record.irn == irn, self.records), None)
        if this_record is not None:
            if not read_config("quiet"):
                print("Record found: {e}, {i}".format(e=endpoint, i=irn))
            return this_record

        return None

records = Records()
