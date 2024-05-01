from datetime import datetime

from src.setup.Settings import read_config
from src.monitoring.Stats import stats
from src.datastore.Memo import memo, format_pid, retrieve_from_memo, add_to_memo, update_memo


class Record():
    def __init__(self, data, endpoint):
        self.data = data
        self.endpoint = endpoint
        self.irn = self.data.get("id")
        self.pid = self.data.get("pid")

        if read_config("restrict_locality"):
            self.check_locality_restriction()

        if read_config("compare_quality_score"):
            self.check_quality_score()

        self.check_new_or_modified()

        if not read_config("quiet"):
            print("Record created: {e}, {i}".format(e=self.endpoint, i=self.irn))

    def check_locality_restriction(self):
        # If restrict locality is on, find event records that need to be redacted
        if self.endpoint == "object":
            try:
                event_id = self.data["evidenceFor"]["atEvent"]["id"]
            except KeyError:
                event_id = None

            if event_id:
                if self.data.get("restrictLocalityData"):
                    event_pid = add_to_memo(irn=event_id, endpoint="fieldcollection", extension=True)
                    update_memo(event_pid, "restrict_locality", True)

                event_pid = format_pid(endpoint="fieldcollection", irn=event_id)
                update_memo(self.pid, "associated_event", event_pid)

    def check_quality_score(self):
        # If part of the primary harvest, save the upper and lower bounds of qualityScores for the result set
        if self.endpoint == read_config("endpoint"):
            try:
                quality_score = self.data["_meta"]["qualityScore"]
            except KeyError:
                quality_score = None

            if quality_score:
                if not stats.quality_score_lower:
                    stats.quality_score_lower = quality_score
                else:
                    if quality_score < stats.quality_score_lower:
                        stats.quality_score_lower = quality_score
                if not stats.quality_score_upper:
                    stats.quality_score_upper = quality_score
                else:
                    if quality_score > stats.quality_score_upper:
                        stats.quality_score_upper = quality_score

    def check_new_or_modified(self):
        if not retrieve_from_memo(self.pid)["checked_if_modified"]:
            modified_recently = self.compare_dates("modified")
            created_recently = self.compare_dates("created")

            update_memo(self.pid, "checked_if_modified", True)
            update_memo(self.pid, "modified_recently", modified_recently)
            update_memo(self.pid, "created_recently", created_recently)

    def compare_dates(self, datetype):
        record_date = self.data["_meta"][datetype]
        rd_datestamp = datetime.fromisoformat(record_date.replace("Z", ""))
        if rd_datestamp >= read_config("check_modified_since"):
            return True
        else:
            return False
