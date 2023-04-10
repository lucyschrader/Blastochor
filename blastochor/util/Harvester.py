# -*- coding: utf-8 -*-

import os
import json
import math
import time

from blastochor.api.askCO import Search, Scroll, Resource
from blastochor.settings.Settings import config, stats, ProgressBar
from blastochor.util.ApiRecord import ApiRecord
from blastochor.util.Mapper import mapping
import blastochor.util.Processor as processor
from blastochor.util.Records import records

class Harvester():

    # Harvest from the Collections Online API

    def __init__(self, sleep=0.1):
        self.sleep = sleep
        self.reharvest_list = []

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
                print("Search record count: {}".format(stats.search_result_count))

            if config.get("max_records") != -1:
                record_limit = config.get("max_records")
            else:
                record_limit = count_call.results.result_count

            page_count = math.ceil(record_limit/size)

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
            scroll = Scroll(query=query, sort=sort, size=size, filters=filters, duration=1, sleep=self.sleep)
            scroll.post_scroll()
            scroll.get_scroll()

            print("Scroll complete")
            stats.search_result_count = scroll.results.result_count

            if not scroll.results.error_code:
                for record in scroll.results.records:
                    new_record = ApiRecord(data=record, endpoint=endpoint)
                    records.append(new_record)
                    self.check_for_triggers(new_record)

        if len(self.reharvest_list) > 0:
            self.run_reharvests()

        print("All records saved")

    def harvest_from_list(self, irn_list=None, endpoint=None):
        # Tell AskCO which records to query
        # Get records into Records object
        stats.list_count = len(irn_list)

        if endpoint == None:
            endpoint = config.get("endpoint")

        for irn in irn_list:
            new_record = self.create_single_record(self, endpoint=endpoint, irn=irn)
            self.check_for_triggers(new_record)

            time.sleep(self.sleep)

    def create_single_record(self, endpoint=None, irn=None):
        resource = Resource(endpoint=endpoint, irn=irn)
        if not resource.error_code:
            new_record = ApiRecord(data=resource.data, endpoint=endpoint)
            records.append(new_record)

            return new_record
        return None

    def check_for_triggers(self, new_record):
        # Review a harvested record against mapping to see what extra records need to be grabbed
        for trigger in mapping.reharvest_triggers:
            if trigger.parent_endpoint == new_record.endpoint:
                self.run_reharvest_trigger(record=new_record, trigger=trigger)

    def run_reharvest_trigger(self, record, trigger):
        # Find all endpoints/irns for extension records, pull from saved scrolls, and add to records
        # Applies a label if the new record should be written out
        # Label is None if the new record is just for a lookup function
        trigger_path = trigger.harvest_path.split(".")
        if "i" in trigger_path:
            extension_irns = processor.collate_list(record.data, path=trigger_path)
            if extension_irns:
                extension_irns = [i for i in extension_irns if i is not None]
                for irn in extension_irns:
                    self.reharvest_list.append({"irn": irn, "endpoint": trigger.harvest_endpoint, "label": trigger.label, "related_record_pid": record.pid})
        else:
            extension_irn = processor.literal(record.data, path=trigger_path)
            if extension_irn:
                self.reharvest_list.append({"irn": extension_irn, "endpoint": trigger.harvest_endpoint, "label": trigger.label, "related_record_pid": record.pid})

    def run_reharvests(self):
        # Work through list of triggered queries to pull down extra records
        print("Running extra queries")
        progress = ProgressBar(length=len(self.reharvest_list))
        progress_counter = 0
        for query in self.reharvest_list:
            irn = query["irn"]
            endpoint = query["endpoint"]
            label = query["label"]
            related_record_pid = query["related_record_pid"]
            this_record = records.find_record(endpoint=endpoint, irn=irn)
            if not this_record:
                extension_record = self.create_single_record(endpoint=endpoint, irn=irn)
                if extension_record:
                    stats.extension_records_count += 1
                    if label:
                        extension_record.relate_record(label=label, related_record_pid=related_record_pid)
            else:
                if label:
                    this_record.relate_record(label=label, related_record_pid=related_record_pid)
            progress_counter += 1
            progress.update(progress_counter)
            time.sleep(self.sleep)

harvester = Harvester()