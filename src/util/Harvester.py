from math import ceil
import time
from tqdm import tqdm
from askCO import Search, Scroll, Resource

from src.setup.Settings import read_config, write_config
from src.monitoring.Stats import stats
from src.datastore.RecordStore import records
from src.datastore.Record import Record
from src.datastore.Memo import memo, format_pid, retrieve_from_memo, add_to_memo, update_memo
from src.util.ProcessingFunctions import collate_list, literal


# Harvest records from Te Papa's Collections Online API
class Harvester():
    def __init__(self, sleep=0.1):
        self.quiet = read_config("quiet")
        self.sleep = sleep
        self.api_key = read_config("api_key")
        self.timeout = read_config("timeout")
        self.attempts = read_config("attempts")
        self.label = read_config("corefile")

        if not self.quiet:
            print("Harvester details: API key = {ak}, timeout = {t}, attempts = {a}".format(ak=self.api_key,
                                                                                            t=self.timeout,
                                                                                            a=self.attempts))

    def complete_harvest(self, mode):
        # Gather search or scroll parameters and turn returned results into Record objects
        endpoint = read_config("endpoint")
        query = read_config("query")
        sort = read_config("sort")
        filters = read_config("filters")
        start = 0
        size = read_config("size")

        stats.mark_time("harvest start")

        if mode == "search":
            self.harvest_search(endpoint, query, sort, filters, start, size)
        elif mode == "scroll":
            self.harvest_scroll(endpoint, query, sort, filters, size)

        stats.mark_time("harvest end")

        self.retrieve_extension_records()

    def retrieve_extension_records(self):
        extension_list = [memo[i] for i in memo.keys() if memo[i].get("is_extension")]

        stats.mark_time("extension start")

        if len(extension_list) > 0:
            self.run_extension_harvest(extension_list)

        stats.mark_time("extension end")

        print("All records saved")

    def harvest_search(self, endpoint, query, sort, filters, start, size):
        initial_search = Search(
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
        initial_search.send_query()
        stats.api_call_count += 1

        stats.initial_record_count = initial_search.record_count
        if not read_config("quiet"):
            print("Search record count: {}".format(stats.initial_record_count))

        if read_config("record_limit"):
            record_limit = read_config("record_limit")
        else:
            record_limit = stats.initial_result_count

        page_count = ceil(record_limit / size)

        # Request each page of results
        for i in tqdm(range(0, page_count), desc="Retrieving search pages: "):
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

            if len(search_page.records) > 0:
                for record in search_page.records:
                    if self.duplicate_check(record, endpoint):
                        self.save_record(record=record, endpoint=endpoint, label=self.label)

            start += size
            time.sleep(self.sleep)

    def harvest_scroll(self, endpoint, query, sort, filters, size):
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
            max_records=read_config("record_limit"))

        scroll.send_query()
        print("Scroll complete")

        stats.initial_record_count = scroll.record_count
        if not read_config("quiet"):
            print("Search record count: {}".format(stats.initial_record_count))

        stats.api_call_count += ceil(len(scroll.records) / size) + 1

        if scroll.record_count > 0:
            print("Saving scrolled records")
            for record in tqdm(scroll.records, desc="Saving scrolled records: "):
                if self.duplicate_check(record, endpoint):
                    self.save_record(record=record, endpoint=endpoint, label=self.label)

    def harvest_from_list(self):
        stats.mark_time("harvest start")
        stats.source_list_count = len(memo)
        endpoint = read_config("endpoint")

        print("Retrieving records from list")

        irn_batch = []

        # Segment list into batches of 250 and run a search for each batch
        for pid in list(memo.keys()):
            memo_record = retrieve_from_memo(pid)
            formatted_irn = "(id:{})".format(memo_record["irn"])
            if formatted_irn not in irn_batch:
                irn_batch.append(formatted_irn)

            if len(irn_batch) == 250:
                self.retrieve_and_save_batch(irn_batch, endpoint)
                irn_batch = []

        # Retrieve and save any remaining records
        if len(irn_batch) > 0:
            self.retrieve_and_save_batch(irn_batch, endpoint)

        stats.mark_time("harvest end")

        self.retrieve_extension_records()

    def retrieve_and_save_batch(self, irn_batch, endpoint):
        batch_records = self.batch_search(irn_batch, endpoint)
        if len(batch_records.records) > 0:
            for record in batch_records.records:
                self.save_record(record, endpoint, read_config("corefile"))

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

    def duplicate_check(self, record, endpoint):
        # Check if record has already been received and update memo as needed
        memo_check = retrieve_from_memo(record["pid"])
        if memo_check:
            if memo_check["status"] == "received":
                return False
            elif memo_check["status"] == "pending":
                update_memo(record["pid"], "status", "received")
        else:
            add_to_memo(status="received", irn=record["id"], endpoint=endpoint, label=self.label)

        return True

    def save_record(self, record, endpoint, label):
        new_record = Record(data=record, endpoint=endpoint)
        records.append(new_record)
        if read_config("use_quality_score"):
            save_quality_score(record)
        if label == read_config("corefile"):
            self.check_for_triggers(new_record)

    def check_for_triggers(self, record):
        # Review a harvested record against mapping rules to see what extension records are needed
        mapping = read_config("mapping")
        for trigger in mapping.reharvest_triggers:
            if trigger.parent_endpoint == record.endpoint:
                self.run_extension_trigger(record=record, trigger=trigger)

    def run_extension_trigger(self, record, trigger):
        # Find all endpoints/irns for extension records and add to memo
        # Applies a label if the new record should be written out
        # Label is None if the new record is just for a lookup function
        paths = trigger.harvest_path.split(", ")
        for path in paths:
            trigger_path = path.split(".")
            if "i" in trigger_path:
                extension_irns = collate_list(record.data, path=trigger_path)
                if extension_irns:
                    extension_irns = [i for i in extension_irns if i is not None]
                    for extension_irn in extension_irns:
                        self.save_extension_details(irn=extension_irn, record=record, trigger=trigger)

            else:
                extension_irn = literal(record.data, path=trigger_path)
                if extension_irn:
                    self.save_extension_details(irn=extension_irn, record=record, trigger=trigger)

    def save_extension_details(self, irn, record, trigger):
        extension_pid = format_pid(trigger.harvest_endpoint, irn)

        # Check if record is already in memo
        if retrieve_from_memo(extension_pid):
            # If so, add new label if record will be written out
            if trigger.label:
                update_memo(extension_pid, "add_label", trigger.label)
                update_memo(extension_pid, "extends", record.pid, label=trigger.label)
        else:
            # Otherwise add to memo
            add_to_memo(status="pending",
                        irn=irn,
                        endpoint=trigger.harvest_endpoint,
                        extension=True,
                        label=trigger.label)
            update_memo(extension_pid, "extends", record.pid, label=trigger.label)

    def run_extension_harvest(self, extension_list):
        # Work through list of triggered queries to pull down extra records
        print("Running extra queries")

        # Split up records by endpoint to allow searching just by IRN
        queries_by_endpoint = {"agent": [],
                               "fieldcollection": [],
                               "object": [],
                               "place": [],
                               "taxon": []}

        for pending_record in tqdm(extension_list, desc="Working: "):
            endpoint = pending_record["endpoint"]
            irn = pending_record["irn"]
            pid = format_pid(endpoint, irn)
            if retrieve_from_memo(pid).get("status") == "received":
                continue
            else:
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
        for endpoint in list(queries_by_endpoint.keys()):
            if len(queries_by_endpoint[endpoint]) > 0:
                extension_batch = self.batch_search(irn_batch=queries_by_endpoint[endpoint], endpoint=endpoint)
                self.save_extension_records(extension_results=extension_batch.records, extension_endpoint=endpoint)

    def save_extension_records(self, extension_results, extension_endpoint):
        for record in extension_results:
            pid = record.get("pid")

            if retrieve_from_memo(pid).get("status") == "pending":
                if self.duplicate_check(record, extension_endpoint):
                    self.save_record(record=record, endpoint=extension_endpoint, label=None)
                    stats.extension_records_count += 1


def save_quality_score(record):
    try:
        record_quality_score = record["_meta"]["qualityScore"]
        if not stats.quality_score_lower:
            stats.quality_score_lower = record_quality_score
        if not stats.quality_score_upper:
            stats.quality_score_upper = record_quality_score
        if record_quality_score < stats.quality_score_lower:
            stats.quality_score_lower = record_quality_score
        if record_quality_score > stats.quality_score_upper:
            stats.quality_score_upper = record_quality_score
    except KeyError:
        pass
