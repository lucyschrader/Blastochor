import os
import yaml


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
            "attempts": 3}


def read_config(key):
    global config
    value = config.get(key)
    return value


def write_config(key, value):
    global config
    config[key] = value


def setup_project(project):
    if project != "none":
        config_file = "blastochor/projects/{}_config.yaml".format(project)
    else:
        config_file = "config.yaml"

    if not os.path.exists(config_file):
            config_file = "blastochor/projects/default.yaml"

    read_config_file(config_file)


def read_config_file(config_file):
    global config
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            print("Reading {}".format(config_file))
            config = yaml.safe_load(f)
    except IOError:
        break_on_settings_error("No config file found")


def add_limit_to_config(limit):
    if limit != -1:
        write_config("record_limit", limit)


def update_settings():
    set_mode()
    set_mapfile()
    set_output_dir()
    set_skiplist()
    set_endpoint()

    # API parameters
    set_api_key()
    set_timeout()
    set_attempts()

    # List mode parameters
    set_list_source()

    # Search mode parameters
    set_query()
    if read_config("mode") != "list":
        set_filters()

    if not read_config("quiet"):
        print("Settings updated...")


def set_mode():
    # Return error if no mode selected
    # DO! Return error if mode is none or not search/scroll/list
    if not read_config("mode"):
        break_on_settings_error("No mode selected - must be search, scroll or list")


def set_mapfile():
    # Defaults to defaultmap if no map provided
    map_file = read_config("mapping_file")
    if not map_file:
        global defaults
        map_file = defaults["mapfile"]
        print("No mapfile provided. Setting to default map")

    # Point to map
    map_path = "blastochor/resources/mapfiles/{}".format(map_file)
    write_config("mapping_file", map_path)
    config["mapping_file"] = map_path


def set_output_dir():
    # Return error if no output directory
    # TODO: properly check for directory's existence and create if not found
    if not read_config("output_dir"):
        break_on_settings_error("Output directory location needed to write files")


def set_skiplist():
    # Reads in list of IRNs to skip if provided
    if read_config("use_skiplist"):
        populate_skiplist()


def populate_skiplist():
    skiplist = []
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
        global defaults
        write_config("endpoint", defaults["endpoint"])
        print("No endpoint provided. Setting to object")


def set_api_key():
    # Return error if no API key
    if read_config("api_key_env"):
        try:
            write_config("api_key", os.environ.get(read_config("api_key_env")))
        except KeyError:
            break_on_settings_error("No API key found in environment")
    else:
        break_on_settings_error("API key required to live")


def set_timeout():
    # Set timeout to 5 seconds if not provided
    if not read_config("timeout"):
        global defaults
        write_config("timeout", defaults["timeout"])


def set_attempts():
    # Set attempt count to 3 if not provided
    if not read_config("attempts"):
        global defaults
        write_config("attempts", defaults["attempts"])


def set_list_source():
    # Concatenate input directory and list source filename
    if read_config("list_source"):
        list_filepath = "./{d}/{f}".format(d=read_config("input_dir"), f=read_config("list_source"))
        write_config("list_source", list_filepath)


def set_query():
    # Set search query to wildcard if not provided
    if not read_config("query"):
        global defaults
        write_config("query", defaults["query"])


def set_filters():
    filters = []

    # Filter to a user-selected collection
    filter_config = read_config("filter")
    user_collection = filter_config.get("collection")
    if user_collection:
        if user_collection in collections:
            filters.append({"field": "collection", "keyword": user_collection})
            if user_collection in humanities:
                filters.append({"field": "type", "keyword": "Object"})
            elif user_collection in sciences:
                filters.append({"field": "type", "keyword": "Specimen"})
        else:
            if not read_config("quiet"):
                print("Invalid collection in filter config. Getting records for all collections")

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
        kw_fields = kw_fields.split(", ")
        kw_values = kw_values.split(", ")
        for i in range(0, len(kw_fields)):
            filters.append({"field": kw_fields[i], "keyword": kw_values[i]})

    write_config("filters", filters)


def break_on_settings_error(message):
    exit("Error during setup: {}".format(message))
