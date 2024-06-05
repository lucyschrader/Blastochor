import os
import yaml
import json
from datetime import datetime, timedelta
from src.setup.Validator import ConfigValidator


config = {}
collections = ["Archaeozoology", "Art", "Birds", "CollectedArchives", "Crustacea", "Fish",
               "FossilVertebrates", "Geology", "History", "Insects", "LandMammals",
               "MarineInvertebrates", "MarineMammals", "Molluscs", "MuseumArchives",
               "PacificCultures", "Philatelic", "Photography", "Plants", "RareBooks",
               "ReptilesAndAmphibians", "TaongaMāori"]
humanities = ["Art", "CollectedArchives", "History", "MuseumArchives", "PacificCultures",
              "Philatelic", "Photography", "RareBooks", "TaongaMāori"]
sciences = ["Archaeozoology", "Birds", "Crustacea", "Fish", "FossilVertebrates", "Geology",
            "Insects", "LandMammals", "MarineInvertebrates", "MarineMammals", "Molluscs",
            "Plants", "ReptilesAndAmphibians"]
defaults = {"mapfile": "default.yaml",
            "endpoint": "object",
            "query": "*",
            "timeout": 5,
            "attempts": 3,
            "days_since_modified": 31}


def read_config(key):
    value = config.get(key)
    return value


def write_config(key, value):
    global config
    config[key] = value


def setup_project(project):
    if project != "none":
        config_file = "src/projects/{}_config.yaml".format(project)

    else:
        config_file = "config.yaml"

    if not os.path.exists(config_file):
        config_file = "src/projects/default.yaml"

    read_config_file(config_file, project)


def read_config_file(config_file, project):
    global config
    print(os.getcwd())
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            print("Reading {}".format(config_file))
            config = yaml.safe_load(f)
    except IOError:
        break_on_settings_error("No config file found")

    config_validator = ConfigValidator(config)
    if config_validator.fail:
        break_on_settings_error("Config validation failed")

    if project != "none":
        write_config("project_name", project)


def update_query(query):
    if query != "none":
        write_config("query", query)


def update_list_source(list_source):
    if list_source != "none":
        write_config("list_source", list_source)


def add_limit_to_config(limit):
    if limit != -1:
        write_config("record_limit", limit)


def update_settings():
    set_mode()
    set_mapfile()
    set_input_dir()
    set_output_dir()
    set_skiplist()
    set_endpoint()
    load_country_codes()
    set_check_modified()
    format_export_string()

    # API parameters
    set_api_key()
    set_timeout()
    set_attempts()

    # List mode parameters
    set_list_source()

    # Search mode parameters
    set_query()
    if config.get("mode") != "list":
        set_filters()

    if not read_config("quiet"):
        print("Settings updated...")


def set_mode():
    # Return error if no mode selected
    mode = read_config("mode")
    if not mode:
        break_on_settings_error("No mode selected - must be search, scroll or list")
    else:
        if mode not in ["search", "scroll", "list"]:
            break_on_settings_error("Mode must be search, scroll or list")


def set_mapfile():
    # Defaults to defaultmap if no map provided
    map_file = read_config("mapping_file")
    if not map_file:
        map_file = defaults["mapfile"]
        print("No mapfile provided. Setting to default map")

    # Point to map
    map_path = "src/resources/mapfiles/{}".format(map_file)
    write_config("mapping_file", map_path)


def set_input_dir():
    # Return error if no input directory
    input_dir = read_config("input_dir")
    if not input_dir:
        break_on_settings_error("Input directory location needed")
    else:
        if not os.path.exists(input_dir):
            os.mkdir(input_dir)


def set_output_dir():
    # Return error if no output directory
    output_dir = read_config("output_dir")
    if not output_dir:
        break_on_settings_error("Output directory location needed to write files")
    else:
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)


def set_skiplist():
    # Reads in list of IRNs to skip if provided
    if read_config("use_skiplist"):
        populate_skiplist()


def populate_skiplist():
    skiplist = []
    skipfile = "{d}/{f}".format(d=read_config("input_dir"), r=read_config("skipfile"))
    with open(read_config("skipfile"), 'r', encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        skiplist.append(int(line.strip()))

    write_config("skiplist", skiplist)

    if not read_config("quiet"):
        print("Skiplist populated")


def set_endpoint():
    # Default to object endpoint if none provided
    if not read_config("endpoint"):
        write_config("endpoint", defaults["endpoint"])
        print("No endpoint provided. Setting to object")


def load_country_codes():
    try:
        with open("src/resources/countrycodes.json") as f:
            country_codes = json.load(f)
            write_config("country_codes", country_codes)
    except IOError:
        if not read_config("quiet"):
            print("No country code file found")


def set_check_modified():
    days_since_modified = read_config("days_since_modified")
    if not days_since_modified:
        days_since_modified = defaults["days_since_modified"]
        write_config("days_since_modified", days_since_modified)

    check_modified_since = datetime.today() - timedelta(days=days_since_modified)
    write_config("check_modified_since", check_modified_since)


def format_export_string():
    project_name = read_config("project_name")
    export_id = read_config("export_id")
    export_filename_string = datetime.now().strftime("%Y%m%d-%H%M%S")
    if project_name:
        export_filename_string += "-{}".format(project_name)
    if export_id:
        export_filename_string += "-{}".format(export_id)

    write_config("export_filename", export_filename_string)


def set_api_key():
    # Return error if no API key
    if read_config("api_key_env"):
        try:
            write_config("api_key", os.environ[read_config("api_key_env")])
            if not read_config("quiet"):
                print("API key set to {}".format(read_config("api_key")))
        except ValueError:
            break_on_settings_error("No API key found in environment")
    else:
        break_on_settings_error("API key required to live")


def set_timeout():
    # Set timeout to 5 seconds if not provided
    if not read_config("timeout"):
        write_config("timeout", defaults["timeout"])


def set_attempts():
    # Set attempt count to 3 if not provided
    if not read_config("attempts"):
        write_config("attempts", defaults["attempts"])


def set_list_source():
    # Concatenate input directory and list source filename
    list_source = read_config("list_source")
    if list_source:
        list_filepath = "{d}/{f}".format(d=read_config("input_dir"), f=read_config("list_source"))
        write_config("list_source", list_filepath)


def set_query():
    # Set search query to wildcard if not provided
    if not read_config("query"):
        write_config("query", defaults["query"])


def set_filters():
    filters = []

    # Filter to a user-selected collection
    filter_config = read_config("filter")
    user_collection = filter_config.get("collection")
    if user_collection:
        user_collection = user_collection.split("|")
        colls = []
        coll_types = []
        for c in user_collection:
            if c in collections:
                colls.append(c)
                if user_collection in humanities:
                    coll_types.append("Object")
                elif user_collection in sciences:
                    coll_types.append("Specimen")

        if len(colls) > 0:
            if len(colls) == 1:
                coll_filter_value = colls[0]
            else:
                coll_filter_value = colls
            filters.append({"field": "collection", "keyword": coll_filter_value})

        if len(coll_types) > 0:
            coll_types = list(set(coll_types))
            if len(coll_types) == 1:
                coll_type_filter_value = coll_types[0]
            else:
                coll_type_filter_value = coll_types
            filters.append({"field": "type", "keyword": coll_type_filter_value})
    else:
        if not read_config("quiet"):
            print("No valid collection in filter config. Getting records for all collections")

    # Filter to records with downloadable images
    if filter_config.get("allows_download") is not None:
        if filter_config.get("allows_download"):
            filters.append({"field": "hasRepresentation.rights.allowsDownload", "keyword": "True"})
        elif not filter_config.get("allows_download"):
            filters.append({"field": "hasRepresentation.rights.allowsDownload", "keyword": "False"})

    # Filter using user-selected keywords
    kw_fields = filter_config.get("keyword_fields")
    kw_values = filter_config.get("keyword_values")

    if kw_fields:
        kw_fields = kw_fields.split("|")
        kw_values = kw_values.split("|")
        for i in range(0, len(kw_fields)):
            filters.append({"field": kw_fields[i], "keyword": kw_values[i]})

    write_config("filters", filters)


def break_on_settings_error(message):
    exit("Error during setup: {}".format(message))
