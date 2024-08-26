from src.setup.Settings import read_config
from src.datastore.RecordStore import records
from src.datastore.Memo import retrieve_from_memo
from lxml import etree


# When triggered, finds the EMu coordinate and datum values for collection event records
# and replaces the API values, avoiding the transformation applied in some cases by the ETL
def apply_coordinate_workaround():
    print("Starting coordinate workaround")
    emu_data_file = "{d}/resources/{f}".format(d=read_config("input_dir"),
                                               f=read_config("emufile"))

    # Define the table name. Tuples are the start of a new record if their parent is this
    table_name = "ecollectionevents"

    # Main loop to iterate through our records
    # We do this in chunks as the xml file can be quite large
    record_context = etree.iterparse(emu_data_file, events=('end',), tag='tuple')

    for event, record in record_context:
        # Check if the chunk is a record
        if not check_is_record(record, table_name):
            continue

        # Get the record's IRN or continue to next if no IRN
        event_irn = check_has_irn(record)
        if not event_irn:
            continue

        # Format pid from irn to allow lookup in memo
        event_pid = "tepapa:collection/fieldcollection/{}".format(event_irn)

        if not retrieve_from_memo(event_pid):
            continue

        # Get EMu values for latitude, longitude and datum
        lat_value = get_emu_value(record, "LatLatitudeDecimal")
        long_value = get_emu_value(record, "LatLongitudeDecimal")
        datum_value = get_emu_value(record, "LatDatum")

        # Map datum to the right EPSG code
        if datum_value:
            datum_value = map_datum_value(datum_value)

        # Update the saved record with the original EMu values
        update_record(event_pid, lat_value, long_value, datum_value)

    print("Coordinate workaround finished")


def check_is_record(record, table_name):
    parent = record.getparent()
    if parent is not None:
        parent_name = parent.attrib.get("name")
        if parent_name == table_name:
            return True
        else:
            return False
    else:
        return False


def check_has_irn(record):
    elem = record.find("atom[@name='irn']")
    if elem is not None and elem.text:
        irn = elem.text
        return irn
    else:
        return False


def get_emu_value(record, fieldname):
    values = []
    for atom in record.iter("atom"):
        atom_text = atom.text
        atom_name = atom.get("name")

        if atom is not None and atom_name == fieldname:
            values.append(atom_text)

    if len(values) > 0:
        # Records may have multiple sets of values but GBIF only uses the first
        return values[0]
    else:
        return None


def map_datum_value(datum_value):
    if "NZGD1949" in datum_value:
        return "EPSG:4272"
    elif "UTM" in datum_value:
        # Waiting on confirmation of code
        return "EPSG:4272"
    elif "NZGD2000" in datum_value:
        # Correct EPSG code TBD
        return "EPSG:4959"
    elif ("WGS1984" or "WGS84") in datum_value:
        return "WGS1984"


def update_record(event_pid, lat_value, long_value, datum_value):
    if records.records[event_pid].data["atLocation"].get("mappingDetails"):
        if lat_value:
            records.records[event_pid].data["atLocation"]["mappingDetails"][0]["decimalLatitude"] = lat_value
        if long_value:
            records.records[event_pid].data["atLocation"]["mappingDetails"][0]["decimalLongitude"] = long_value
        if datum_value:
            records.records[event_pid].data["atLocation"]["mappingDetails"][0]["geodeticDatum"] = datum_value
