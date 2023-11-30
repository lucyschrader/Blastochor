import csv
from blastochor.settings.Settings import read_config, write_config
from blastochor.util.Memo import memo, add_to_record_memo, format_pid, check_memo_for_pid, update_memo_with_media


def read_input_list(source_file):
    endpoint = read_config("endpoint")
    label = read_config("corefile")

    if source_file.endswith(".csv"):
        import_file_from_csv(source_file, endpoint, label)
    elif source_file.endswith(".txt"):
        import_file_from_txt(source_file, endpoint, label)


def import_list_from_csv(source_file, endpoint, label):
    with open(source_file, newline="", encoding="utf-8") as f:
        source_data = csv.DictReader(f, delimiter=",")

        for row in source_data:
            record_irn = int(row.get("record_irn"))
            media_irn = int(row.get("media_irn"))
            if read_config("use_skipfile") == True:
                if skip_check(record_irn) == True:
                    break

            add_to_memo(record_irn=record_irn, media_irn=media_irn, endpoint=endpoint, label=label)


def import_list_from_txt(source_file, endpoint, label):
    with open(source_file, "r", encoding="utf-8") as f:
        source_data = f.readlines()

        for row in source_data:
            record_irn = int(row.strip())
            if read_config("use_skipfile"):
                if skip_check(record_irn):
                    break

            add_to_memo(record_irn=record_irn, endpoint=endpoint, label=label)


def skip_check(irn):
    if irn in read_config("skiplist"):
        return True

    return False


def add_to_memo(record_irn=None, media_irn=None, endpoint=None, label=None):
    # If the record is not already in the memo, add it now
    record_pid = format_pid(endpoint=endpoint, irn=record_irn)
    if not check_memo_for_pid(record_pid):
        add_to_record_memo(status="pending", irn=record_irn, endpoint=endpoint, label=label)

    # If specific images are required, append their IRNs to the memo
    if media_irn:
        update_memo_with_media(record_pid, media_irn)
