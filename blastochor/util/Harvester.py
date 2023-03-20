# -*- coding: utf-8 -*-

import os
import json
import math
import time

from blastochor.api.askCO import Search, Scroll, Resource
from blastochor.settings.Settings import config, stats
from blastochor.util.ApiRecord import ApiRecord
from blastochor.util.Mapper import mapping
import blastochor.util.Processor as processor
from blastochor.util.Records import records

class Harvester():

    # Harvest from the Collections Online API

    def __init__(self, sleep=1):
        self.sleep = sleep

    def complete_harvest(self, mode):
        # Gather search/scroll parameters and turn returned records into ApiRecord objects
        endpoint = config.get("endpoint")
        query = config.get("query")
        sort = config.get("sort")
        filters = config.get("filters")
        start = 0
        size = config.get("size")

        if mode == "search":
            count_call = Search(query=query, sort=sort, filters=filters, start=start, size=1)
            stats.search_result_count = count_call.results.result_count
            if not config.get("quiet"):
                print("Search record count: {}".format(record_count))

            if config.get("max_records") != -1:
                record_limit = config.get("max_records")
            else:
                record_limit = count_call.results.result_count

            page_count = math.ceil(record_count/size)

            for i in range(0, page_count):
                search = Search(query=query, sort=sort, filters=filters, start=start, size=size)

                # TODO: Work out a fix for pagination so I don't have to check for duplicates
                if not search.results.error_code:
                    for record in search.results.records:
                        if records.find_record(endpoint=endpoint, irn=record.get("id")) == None:
                            new_record = ApiRecord(data=record, endpoint=endpoint)
                            records.append(new_record)
                            self.check_for_triggers(new_record)
                        else:
                            if not config.get("quiet"):
                                print("Duplicate record: {}".format(record.get("pid")))

                start += size
                time.sleep(self.sleep)

        elif mode == "scroll":
            scroll = Scroll(query=query, sort=sort, size=size, filters=filters, duration=1)
            scroll.post_scroll()
            scroll.get_scroll()

            stats.search_result_count = scroll.results.result_count

            if not scroll.results.error_code:
                for record in scroll.results.records:
                    new_record = ApiRecord(data=record, endpoint=endpoint)
                    records.append(new_record)
                    self.check_for_triggers(new_record)

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
        resource = Resource(endpoint=endpoint, irn=irn)
        if not resource.error_code:
            new_record = ApiRecord(data=resource.data, endpoint=endpoint)
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
                        if extension_record:
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
                    if extension_record:
                        stats.extension_records_count += 1
                        if trigger.label:
                            extension_record.relate_record(label=trigger.label, related_record_pid=record.pid)
                else:
                    if trigger.label:
                        this_record.relate_record(label=trigger.label, related_record_pid=record.pid)


harvester = Harvester()