# -*- coding: utf-8 -*-

from blastochor.settings.Settings import config

class Records():
    def __init__(self):
        self.records = []

    def append(self, record):
    	self.records.append(record)

    def find_record(self, endpoint, irn):
        # Find record with this endpoint, irn and return it
        this_record = next(filter(lambda record: record.endpoint == endpoint and record.irn == irn, self.records), None)
        if this_record is not None:
            if not config.get("quiet"):
                print("Record found: {e}, {i}".format(e=endpoint, i=irn))
            return this_record

        return None

records = Records()