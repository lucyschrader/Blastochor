class RecordStore():
    def __init__(self):
        self.records = {}

    def append(self, record):
        this_pid = record.pid
        self.records.update({this_pid: record})

    def find_record(self, endpoint, irn):
        this_pid = "tepapa:collection/{e}/{i}".format(e=endpoint, i=irn)
        return self.records.get(this_pid)


records = RecordStore()
