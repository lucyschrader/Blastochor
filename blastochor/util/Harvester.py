# -*- coding: utf-8 -*-

import os
import json
from math import ceil
import time
from tqdm import tqdm
from askCO import Search, Scroll, Resource

from blastochor.settings.Settings import config, add_to_record_memo
from blastochor.settings.Stats import stats
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
                print("Saving scrolled records")
                for record in tqdm(scroll.records, desc="Working: "):
                    self.save_record(record=record, endpoint=endpoint, label=config["corefile"])

        stats.end_harvest()

        extension_list = [config["record_memo"][i] for i in config["record_memo"] if config["record_memo"][i]["is_extension"] == True]

        if len(extension_list) > 0:
            self.run_extension_harvest(extension_list)

        stats.end_extrarecords()

        print("All records saved")

    def save_record(self, record, endpoint, label):
        if self.update_memo_from_harvest(record=record, endpoint=endpoint, label=label):
            new_record = ApiRecord(data=record, endpoint=endpoint)
            records.append(new_record)
            if label == config["corefile"]:
                self.check_for_triggers(new_record)

    # Check if record is already in memo/saved and update as needed
    def update_memo_from_harvest(self, record, endpoint, label):
        pid = record.get("pid")
        if pid in config["record_memo"]:
            current_status = config["record_memo"][pid]["status"]
            if current_status == "received":
                return False
            elif current_status == "pending":
                config["record_memo"][pid]["status"] = "received"
                return True
        else:
            add_to_record_memo(status="received", irn=record.get("id"), endpoint=endpoint, label=label)
            return True

    def harvest_from_list(self, endpoint=None):
        # Tell AskCO which records to query
        # Get records into Records object
        stats.list_count = len(config.get("record_memo"))

        if endpoint == None:
            endpoint = config.get("endpoint")

        print("Retrieving records from list")

        irn_batch = HarvestBatch(endpoint=endpoint)

        # Segment list into batches of 250 and run a search for each batch
        for pid in tqdm(config.get("record_memo").keys(), desc="Working: "):
            memo_record = config.get("record_memo").get(pid)
            
            irn_formatted = "(id:{})".format(memo_record["irn"])
            
            if irn_formatted not in irn_batch.irns:
                irn_batch.irns.append(irn_formatted)

            if len(irn_batch.irns) == 250:
                batch_records = self.batch_search(irn_batch.irns, endpoint)

                if len(batch_records.records) > 0:
                    for record in tqdm(batch_records.records, desc="Working: "):
                        self.save_record(record=record, endpoint=endpoint, label=config["corefile"])

                irn_batch.irns = []

        # Search for any remaining IRNs
        if len(irn_batch.irns) > 0:
            batch_records = self.batch_search(irn_batch=irn_batch.irns, endpoint=endpoint)

            if len(batch_records.records) > 0:
                for record in tqdm(batch_records.records, desc="Working: "):
                    self.save_record(record=record, endpoint=endpoint, label=config["corefile"])

        stats.end_harvest()

        extension_list = [config["record_memo"][i] for i in config["record_memo"] if config["record_memo"][i]["is_extension"] == True]

        if len(extension_list) > 0:
            self.run_extension_harvest(extension_list)

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

    def check_for_triggers(self, record):
        # Review a harvested record against mapping to see what extension records need to be grabbed
        for trigger in mapping.reharvest_triggers:
            if trigger.parent_endpoint == record.endpoint:
                self.run_extension_trigger(record=record, trigger=trigger)

    def run_extension_trigger(self, record, trigger):
        # Find all endpoints/irns for extension records and add to memo
        # Applies a label if the new record should be written out
        # Label is None if the new record is just for a lookup function
        trigger_path = trigger.harvest_path.split(".")
        if "i" in trigger_path:
            extension_irns = processor.collate_list(record.data, path=trigger_path)
            if extension_irns:
                extension_irns = [i for i in extension_irns if i is not None]
                for extension_irn in extension_irns:
                    self.save_extension_details(irn=extension_irn, record=record, trigger=trigger)

        else:
            extension_irn = processor.literal(record.data, path=trigger_path)
            if extension_irn:
                self.save_extension_details(irn=extension_irn, record=record, trigger=trigger)

    def save_extension_details(self, irn, record, trigger):
        extension_pid = "tepapa:collection/{e}/{i}".format(e=trigger.harvest_endpoint, i=irn)

        # Check if record is already in memo
        if config["record_memo"].get(extension_pid):
            # If so, add new label if record will be written out
            if trigger.label:
                if trigger.label not in config["record_memo"][extension_pid]["write_to"]:
                    config["record_memo"][extension_pid]["write_to"].append(trigger.label)
                    config["record_memo"][extension_pid]["structure"].update({trigger.label: {"write": True, "extends": [record.pid]}})
                else:
                    if record.pid not in config["record_memo"][extension_pid]["structure"][trigger.label]["extends"]:
                        config["record_memo"][extension_pid]["structure"][trigger.label]["extends"].append(record.pid)
        else:
            # Otherwise add to memo
            add_to_record_memo(status="pending", irn=irn, endpoint=trigger.harvest_endpoint, extension=True, label=trigger.label, extends=record.pid)

    def run_extension_harvest(self, extension_list):
        # Work through list of triggered queries to pull down extra records
        print("Running extra queries")

        # Split up records by endpoint to allow searching just by IRN
        queries_by_endpoint = {"agent": [], "fieldcollection": [], "object": [], "place": [], "taxon": []}

        for pending_record in tqdm(extension_list, desc="Working: "):
            endpoint = pending_record["endpoint"]
            irn = pending_record["irn"]

            # Format a segment of the search query and store it to run a batch search
            irn_formatted = "(id:{})".format(irn)

            if irn_formatted not in queries_by_endpoint[endpoint]:
                queries_by_endpoint[endpoint].append(irn_formatted)

            # Run whenever there's 250 IRNs saved for an endpoint
            if len(queries_by_endpoint[endpoint]) == 250:
                extension_batch = self.batch_search(irn_batch=queries_by_endpoint[endpoint], endpoint=endpoint)
                self.save_extension_records(extension_results=extension_batch.records, extension_endpoint=endpoint)
                queries_by_endpoint[endpoint] = []

        # Run searches for remaining records
        for endpoint in queries_by_endpoint.keys():
            if len(queries_by_endpoint[endpoint]) > 0:
                extension_batch = self.batch_search(irn_batch=queries_by_endpoint[endpoint], endpoint=endpoint)
                self.save_extension_records(extension_results=extension_batch.records, extension_endpoint=endpoint)

    def save_extension_records(self, extension_results, extension_endpoint):
        for record in extension_results:
            pid = record.get("pid")
            
            if config["record_memo"][pid]["status"] == "pending":
                extension_record = ApiRecord(data=record, endpoint=extension_endpoint)
                records.append(extension_record)

                config["record_memo"][pid]["status"] = "received"
                stats.extension_records_count += 1

class HarvestBatch():
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.irns = []

harvester = Harvester()