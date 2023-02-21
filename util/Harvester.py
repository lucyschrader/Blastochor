# -*- coding: utf-8 -*-

import os
import json
import math
import time
import askCO

from Blastochor import app
from DataCollator import ApiRecord

class Harvester():

    # Harvest from the Collections Online API

    def __init__(self, sleep=1):
        self.sleep = sleep

        self.API = askCO.CoApi()

    def harvest_from_search(self):
        # Tell AskCO which searches to run
        # Get records into Records object
        endpoint = app.settings.api.endpoint
        q = app.settings.search.query
        sort = app.settings.search.sort
        filters = app.settings.filters.filters
        start = 0
        size = app.settings.api.size

        count_call = self.API.search(q=q, sort=sort, filters=filters, start=start, size=1)
        record_count = count_call.result_count

        page_count = math.ceil(record_count/size)

        for i in range(0, page_count):
            # TODO: Check that response is as expected
            response = self.API.search(endpoint=endpoint, q=q, sort=sort, filters=filters, start=start, size=size)
            for record in response.records:
                new_record = ApiRecord(data=record, endpoint=endpoint)
                new_record.make_writeable(label=app.settings.corefile, bool=True)
                app.records.append(new_record)
                check_for_triggers(new_record)

            start += size
            time.sleep(self.sleep)

    def harvest_from_list(self, irn_list=irn_list, endpoint=None):
        # Tell AskCO which records to query
        # Get records into Records object
        if endpoint == None:
            endpoint = app.settings.api.endpoint

        for irn in irn_list:
            self.create_single_record(self, endpoint=endpoint, irn=irn, label=self.settings.corefile)

            time.sleep(self.sleep)

    def create_single_record(self, endpoint, irn, label):
        response = self.API.view_resource(endpoint=endpoint, irn=irn)
        if response.errors == None:
            new_record = ApiRecord(data=response.data, endpoint=endpoint)
            if label is not None:
                new_record.make_writeable(label=label, bool=True)
            app.records.append(new_record)
            check_for_triggers(new_record)

    def check_for_triggers(self, new_record):
        # Review a harvested record against mapping to see what extra records need to be grabbed
        for trigger in app.mapping.harvest_triggers:
            if trigger.parent_endpoint == new_record.endpoint:
                self.run_harvest_trigger(record=new_record, trigger=trigger)

    def run_harvest_trigger(self, record, trigger):
        # Find all endpoints/irns for extension records, harvest, and add to app.records
        # Applies a label if the new record should be written out
        # Label is None if the new record is just for a lookup function
        if "i" in trigger.harvest_path.split("."):
            extension_irns = app.processor.collate_list(self.data, trigger.harvest_path)
            for irn in extension_irns:
                if app.records.find_record(endpoint=trigger.harvest_endpoint, irn=irn) == None:
                    extension_record = app.harvester.create_single_record(endpoint=trigger.harvest_endpoint, irn=irn, label=trigger.label)
                    extension_record.relate_record(label=trigger.label, record=record.pid)
        else:
            extension_irn = app.processor.literal(self.data, trigger.harvest_path)
            if app.records.find_record(endpoint=trigger.harvest_endpoint, irn=extension_irn) == None:
                extension_record = app.harvester.create_single_record(endpoint=trigger.harvest_endpoint, irn=extension_irn, label=trigger.label)
                extension_record.relate_record(label=trigger.label, record=record.pid)

