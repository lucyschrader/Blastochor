# -*- coding: utf-8 -*-

import os
import json
from math import ceil
import time
from askCO import Search, Scroll, Resource

from blastochor.settings.Settings import config
from blastochor.settings.Stats import stats, ProgressBar
from blastochor.util.ApiRecord import ApiRecord
from blastochor.util.Mapper import mapping
import blastochor.util.Processor as processor
from blastochor.util.Records import records

class Harvester():

    # Harvest from the Collections Online API

    def __init__(self, sleep=0.1):
        self.quiet = config.get("quiet")
        self.sleep = sleep
        self.api_key = config.get("api_key")
        self.timeout = config.get("timeout")
        self.attempts = config.get("attempts")
        self.max_records = config.get("max_records")
        self.reharvest_list = []

    def complete_harvest(self, mode):
        # Gather search/scroll parameters and turn returned records into ApiRecord objects
        # TODO: Fail gracefully if search returns no results
        # Consider running fallback searches, eg changing endpoint to object
        endpoint = config.get("endpoint")
        query = config.get("query")
        sort = config.get("sort")
        filters = config.get("filters")
        start = 0
        size = config.get("size")

        if mode == "search":
            count_search = Search(
                quiet=self.quiet,
                sleep=self.sleep,
                api_key=self.api_key,
                timeout=self.timeout,
                attempts=self.attempts,
                endpoint=endpoint,
                query=query,
                sort=sort,
                filters=filters,
                start=start,
                size=1)

            # Get result count to work out how many pages to request
            count_search.send_query()
            stats.api_call_count += 1
            
            stats.search_result_count = count_search.record_count
            
            if not config.get("quiet"):
                print("Search record count: {}".format(stats.search_result_count))

            if config.get("max_records") != -1:
                record_limit = config.get("max_records")
            else:
                record_limit = stats.search_result_count

            page_count = ceil(record_limit/size)

            # Request each page of results
            for i in range(0, page_count):
                search_page = Search(
                    quiet=self.quiet,
                    sleep=self.sleep,
                    api_key=self.api_key,
                    timeout=self.timeout,
                    attempts=self.attempts,
                    endpoint=endpoint,
                    query=query,
                    sort=sort,
                    filters=filters,
                    start=start,
                    size=size)

                search_page.send_query()
                stats.api_call_count += 1

                # TODO: Work out a fix for pagination so I don't have to check for duplicates
                if len(search_page.records) > 0:
                    for record in search_page.records:
                        this_record = records.find_record(endpoint=endpoint, irn=record.get("id"))
                        if not this_record:
                            new_record = ApiRecord(data=record, endpoint=endpoint)
                            records.append(new_record)
                            self.check_for_triggers(new_record)

                start += size
                if config.get("rate_limited"):
                    time.sleep(self.sleep)

        elif mode == "scroll":
            scroll = Scroll(
                quiet=self.quiet,
                sleep=self.sleep,
                api_key=self.api_key,
                timeout=self.timeout,
                attempts=self.attempts,
                endpoint=endpoint,
                query=query,
                sort=sort,
                size=size,
                filters=filters,
                duration=1,
                max_records=self.max_records)

            scroll.send_query()
            print("Scroll complete")
            
            stats.search_result_count = scroll.record_count

            stats.api_call_count += ceil(scroll.record_count / size) + 1

            if scroll.record_count > 0:
                for record in scroll.records:
                    this_record = records.find_record(endpoint=endpoint, irn=record.get("id"))
                    if not this_record:
                        new_record = ApiRecord(data=record, endpoint=endpoint)
                        records.append(new_record)
                        self.check_for_triggers(new_record)

        stats.end_harvest()

        if len(self.reharvest_list) > 0:
            self.run_reharvests()

        stats.end_extrarecords()

        print("All records saved")

    def harvest_from_list(self, endpoint=None):
        # Tell AskCO which records to query
        # Get records into Records object
        irn_list = config.get("irn_list")
        stats.list_count = len(irn_list)

        if endpoint == None:
            endpoint = config.get("endpoint")

        print("Retrieving records from list")
        progress = ProgressBar(stats.list_count)
        progress_counter = 0

        irn_batch = HarvestBatch(endpoint=endpoint)

        # Segment list into batches of 250 and run a search for each batch
        for irn_object in irn_list:
            irn_formatted = "(id:{})".format(irn_object.irn)
            if irn_formatted not in irn_batch.irns:
                irn_batch.irns.append(irn_formatted)

            if len(irn_batch.irns) == 250:
                batch_records = self.batch_search(irn_batch.irns, endpoint)

                if len(batch_records.records) > 0:
                    for record in batch_records.records:
                        new_record = ApiRecord(data=record, endpoint=endpoint)
                        records.append(new_record)
                        self.check_for_triggers(new_record)

                irn_batch.irns = []

            progress_counter += 1
            progress.update(progress_counter)

        # Search for any remaining IRNs
        if len(irn_batch.irns) > 0:
            batch_records = self.batch_search(irn_batch=irn_batch.irns, endpoint=endpoint)

            if len(batch_records.records) > 0:
                for record in batch_records.records:
                    new_record = ApiRecord(data=record, endpoint=endpoint)
                    records.append(new_record)
                    self.check_for_triggers(new_record)

        stats.end_harvest()

        if len(self.reharvest_list) > 0:
            self.run_reharvests()

        stats.end_extrarecords()

        print("All records in list saved")

    def batch_search(self, irn_batch, endpoint):
        query = " OR ".join(irn_batch)

        search_batch = Search(
            quiet=self.quiet,
            sleep=self.sleep,
            api_key=self.api_key,
            timeout=self.timeout,
            attempts=self.attempts,
            endpoint=endpoint,
            query=query,
            size=250)
        search_batch.send_query()
        stats.api_call_count += 1

        return search_batch

    def create_single_record(self, endpoint=None, irn=None):
        # Look up a single record and turn it into an ApiRecord object
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

        # Split up records by endpoint to allow searching just by IRN
        queries_by_endpoint = []

        # Set up buckets for each endpoint
        for e in ["agent", "fieldcollection", "object", "place", "taxon"]:
            queries_by_endpoint.append(HarvestBatch(endpoint=e))
        
        # Run through the list of needed records
        for record_trigger in self.reharvest_list:
            endpoint = record_trigger["endpoint"]
            irn = record_trigger["irn"]
            label = record_trigger["label"]
            related_record_pid = record_trigger["related_record_pid"]
            this_record = records.find_record(endpoint=endpoint, irn=irn)
            if not this_record:
                # Format a segment of the search query and store it to run a batch search
                this_endpoint_queries = next(filter(lambda queries: queries.endpoint == endpoint, queries_by_endpoint), None)

                irn_formatted = "(id:{})".format(irn)

                if irn_formatted not in this_endpoint_queries.irns:
                    this_endpoint_queries.irns.append(irn_formatted)
                
                # Run whenever there's 250 IRNs saved for an endpoint
                if len(this_endpoint_queries.irns) == 250:
                    reharvest_batch = self.batch_search(irn_batch=this_endpoint_queries.irns, endpoint=endpoint)
                    self.save_reharvest_records(reharvest_results=reharvest_batch.records, reharvest_endpoint=endpoint)
                    this_endpoint_queries.irns = []

            else:
                if label:
                    this_record.relate_record(label=label, related_record_pid=related_record_pid)

            progress_counter += 1
            progress.update(progress_counter)

        # Run searches for remaining records
        for this_endpoint_queries in queries_by_endpoint:
            if len(this_endpoint_queries.irns) > 0:
                reharvest_batch = self.batch_search(irn_batch=this_endpoint_queries.irns, endpoint=this_endpoint_queries.endpoint)
                self.save_reharvest_records(reharvest_results=reharvest_batch.records, reharvest_endpoint=this_endpoint_queries.endpoint)

    def save_reharvest_records(self, reharvest_results, reharvest_endpoint):
        for record in reharvest_results:
            record_trigger = next(filter(lambda record_trigger: (record_trigger.get("irn") == record.get("id")) and (record_trigger.get("endpoint") == reharvest_endpoint), self.reharvest_list), None)

            # Get the extra details of the trigger to allow saving the record and any extra labels
            if record_trigger:
                endpoint = record_trigger["endpoint"]
                irn = record_trigger["irn"]
                label = record_trigger["label"]
                related_record_pid = record_trigger["related_record_pid"]

                this_record = records.find_record(endpoint=endpoint, irn=irn)
                if not this_record:
                    extension_record = ApiRecord(data=record, endpoint=endpoint)
                    records.append(extension_record)

                    stats.extension_records_count += 1

                    if label:
                        extension_record.relate_record(label=label, related_record_pid=related_record_pid)

class HarvestBatch():
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.irns = []

harvester = Harvester()