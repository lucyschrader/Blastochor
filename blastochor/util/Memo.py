memo = {}


def format_pid(endpoint="object", irn=None):
    if irn:
        return "tepapa:collection/{e}/{i}".format(e=endpoint, i=irn)
    else:
        return None


def check_memo_for_pid(pid=None):
    global memo
    if pid:
        record_memo = memo.get(pid)
        return record_memo
    else:
        return None


def add_to_record_memo(status=None, irn=None, endpoint=None, label=None, extension=None):
    global memo
    pid = format_pid(endpoint=endpoint, irn=irn)

    if not status:
        status = "pending"
    if not extension:
        extension = False

    memo[pid] = {
        "status": status,
        "irn": irn,
        "endpoint": endpoint,
        "pid": pid,
        "write_to": [],
        "structure": {},
        "is_extension": extension,
        "media_irns": []
    }

    if label:
        memo[pid]["write_to"].append(label)
        memo[pid]["structure"].update({label: {"write": True, "extends": []}})

    return pid


def update_memo_with_media(pid, media_irn):
    global memo
    memo[pid]["media_irns"].append(media_irn)
