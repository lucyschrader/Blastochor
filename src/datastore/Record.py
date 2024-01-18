import json

from src.setup.Settings import read_config
from src.monitoring.Stats import stats
from src.datastore.Memo import memo, format_pid, add_to_memo, update_memo


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
