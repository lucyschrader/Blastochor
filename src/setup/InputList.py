import csv
from src.setup.Settings import read_config, write_config
from src.datastore.Memo import memo, add_to_memo, format_pid, retrieve_from_memo, update_memo


# Read a supplied source file (csv or txt)
# and add all required records to the record memo
# with the status 'pending'.
def read_input_list(source_file):
    endpoint = read_config("endpoint")
    label = read_config("corefile")

    if source_file.endswith(".csv"):
        import_list_from_csv(source_file, endpoint, label)
    elif source_file.endswith(".txt"):
        import_list_from_txt(source_file, endpoint, label)


def import_list_from_csv(source_file, endpoint, label):
    with open(source_file, newline="", encoding="utf-8") as f:
        source_data = csv.DictReader(f, delimiter=",")

        for row in source_data:
            record_irn = int(row.get("record_irn"))
            media_irn = int(row.get("media_irn"))
            if read_config("use_skipfile"):
                if skip_check(record_irn):
                    break

            record_pid = add_to_memo(irn=record_irn, endpoint=endpoint, label=label)
            if media_irn:
                update_memo(record_pid, "media", media_irn)


def import_list_from_txt(source_file, endpoint, label):
    with open(source_file, "r", encoding="utf-8") as f:
        source_data = f.readlines()

        for row in source_data:
            record_irn = int(row.strip())
            if read_config("use_skipfile"):
                if skip_check(record_irn):
                    break

            add_to_memo(irn=record_irn, endpoint=endpoint, label=label)


def skip_check(irn):
    if irn in read_config("skiplist"):
        return True

    return False


def add_irn_to_memo(record_irn=None, media_irn=None, endpoint=None, label=None):
    # If the record is not already in the memo, add it now
    record_pid = format_pid(endpoint=endpoint, irn=record_irn)
    if not retrieve_from_memo(record_pid):
        add_to_memo(status="pending", irn=record_irn, endpoint=endpoint, label=label)

    # If specific images are required, append their IRNs to the memo
    if media_irn:
        update_memo(record_pid, "media", media_irn)
