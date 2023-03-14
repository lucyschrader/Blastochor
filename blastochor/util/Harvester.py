# -*- coding: utf-8 -*-

import os
import json
import math
import time

from blastochor.api import askCO
from blastochor.settings.Settings import config, stats
from blastochor.util.ApiRecord import ApiRecord
from blastochor.util.Mapper import mapping
import blastochor.util.Processor as processor
from blastochor.util.Records import records

class Harvester():

    # Harvest from the Collections Online API

    def __init__(self, sleep=1):
        self.sleep = sleep
        self.API = askCO.CoApi()

    def harvest_from_search(self):
        # Tell AskCO which searches to run
        # Get records into Records object
        endpoint = config.get("endpoint")
        q = config.get("query")
        sort = config.get("sort")
        filters = config.get("filters")
        start = 0
        size = config.get("size")

        count_call = self.API.search(q=q, sort=sort, filters=filters, start=start, size=1)
        stats.search_result_count = count_call.result_count

        if config.get("max_records") != -1:
            record_count = config.get("max_records")
        else:
            record_count = count_call.result_count
        if not config.get("quiet"):
            print("Search record count: {}".format(record_count))

        page_count = math.ceil(record_count/size)

        for i in range(0, page_count):
            # TODO: Check that response is as expected
            response = self.API.search(q=q, sort=sort, filters=filters, start=start, size=size)

            if not config.get("quiet"):
                if response:
                    print("Search results page {i} received".format(i=i+1))

            # TODO: Work out a fix for pagination/scrolling so I don't have to check for duplicates
            for record in response.records:
                if records.find_record(endpoint=endpoint, irn=record.get("id")) == None:
                    new_record = ApiRecord(data=record, endpoint=endpoint)
                    records.append(new_record)
                    self.check_for_triggers(new_record)
                else:
                    if not config.get("quiet"):
                        print("Duplicate record: {}".format(record.get("pid")))

            start += size
            time.sleep(self.sleep)

    def harvest_from_list(self, irn_list=None, endpoint=None):
        # Tell AskCO which records to query
        # Get records into Records object
        stats.list_count = len(irn_list)

        if endpoint == None:
            endpoint = config.get("endpoint")

        for irn in irn_list:
            self.create_single_record(self, endpoint=endpoint, irn=irn)

            time.sleep(self.sleep)

    def create_single_record(self, endpoint, irn):
        response = self.API.view_resource(endpoint=endpoint, irn=irn)
        if response.errors == None:
            new_record = ApiRecord(data=response.data, endpoint=endpoint)
            records.append(new_record)
            # TODO: run triggers in a batch after harvest
            self.check_for_triggers(new_record)

            return new_record
        return None

    def check_for_triggers(self, new_record):
        # Review a harvested record against mapping to see what extra records need to be grabbed
        for trigger in mapping.harvest_triggers:
            if trigger.parent_endpoint == new_record.endpoint:
                self.run_harvest_trigger(record=new_record, trigger=trigger)

    def run_harvest_trigger(self, record, trigger):
        # Find all endpoints/irns for extension records, harvest, and add to records
        # Applies a label if the new record should be written out
        # Label is None if the new record is just for a lookup function
        trigger_path = trigger.harvest_path.split(".")
        if "i" in trigger_path:
            extension_irns = processor.collate_list(record.data, path=trigger_path)
            if extension_irns:
                extension_irns = [i for i in extension_irns if i is not None]
                for irn in extension_irns:
                    this_record = records.find_record(endpoint=trigger.harvest_endpoint, irn=irn)
                    if not this_record:
                        if not config.get("quiet"):
                            print("Reharvest triggered...")

                        extension_record = self.create_single_record(endpoint=trigger.harvest_endpoint, irn=irn)
                        stats.extension_records_count += 1
                        if trigger.label:
                            extension_record.relate_record(label=trigger.label, related_record_pid=record.pid)
                    else:
                        if trigger.label:
                            extension_record.relate_record(label=trigger.label, related_record_pid=record.pid)
        else:
            extension_irn = processor.literal(record.data, path=trigger_path)
            if extension_irn:
                this_record = records.find_record(endpoint=trigger.harvest_endpoint, irn=extension_irn)
                if not this_record:
                    if not config.get("quiet"):
                        print("Reharvest triggered...")
                            
                    extension_record = self.create_single_record(endpoint=trigger.harvest_endpoint, irn=extension_irn)
                    stats.extension_records_count += 1
                    if trigger.label:
                        extension_record.relate_record(label=trigger.label, related_record_pid=record.pid)
                else:
                    if trigger.label:
                        this_record.relate_record(label=trigger.label, related_record_pid=record.pid)


harvester = Harvester()