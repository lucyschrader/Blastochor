memo = {}


def format_pid(endpoint="object", irn=None):
    if irn:
        return "tepapa:collection/{e}/{i}".format(e=endpoint, i=irn)
    else:
        return None


def retrieve_from_memo(pid=None):
    memo_record = memo.get(pid)
    return memo_record


def add_to_memo(status=None, irn=None, endpoint=None, label=None, extension=None):
    global memo
    pid = format_pid(endpoint=endpoint, irn=irn)
    memo_record = retrieve_from_memo(pid)
    if memo_record:
        return memo_record["pid"]
    else:
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
            "media_irns": [],
            "checked_if_modified": False,
            "created_recently": False,
            "modified_recently": False
        }

        if label:
            memo[pid]["write_to"].append(label)
            memo[pid]["structure"].update({label: {"write": True, "extends": []}})

        return pid


def update_memo(pid, update_type, value, label=None):
    global memo
    if retrieve_from_memo(pid):
        match update_type:
            case "add_label":
                if value not in memo[pid]["write_to"]:
                    memo[pid]["write_to"].append(value)
                    memo[pid]["structure"].update({value: {"write": True, "extends": []}})

            case "extends":
                if label:
                    if value not in memo[pid]["structure"][label]["extends"]:
                        memo[pid]["structure"][label]["extends"].append(value)
                memo[pid]["is_extension"] = True

            case "media":
                memo[pid]["media_irns"].append(value)

            case _:
                memo[pid][update_type] = value
    else:
        return False
