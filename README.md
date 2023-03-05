# Blastochor: Harvest data from Te Papa's collections API

["blastochory, where the stem of the plant crawls along the ground to deposit its seed far from the base of the plant"](https://en.wikipedia.org/wiki/Seed_dispersal#Autochory)

Fun fact: this doesn't work yet, but check back later. :)

This tool lets you Te Papa's collections API using some basic configuration options, transform the data based on a mapping file, and export the data as a single CSV or multiple CSVs that reference one another, such as can be combined in a Darwin Core Archive (DwC-A).

This repo includes a basic mapping file that will be used if another is not provided.

[API documentation](https://data.tepapa.govt.nz/docs/)

## Installation
Clone this repo using `git clone`. Install the following packages:
- Requests
- PyYAML

Go to https://data.tepapa.govt.nz/docs/register.html and register for an API key. Add the API key to an environment variable called 'TE-PAPA-KEY'.

If using a custom mapping, this should sit alongside Config.yml.

## Usage
Edit the `Config.yml` file to set search and export parameters.

The main functional setting is `search` or `list`. You can either send a search query, which will page through and return all relevant records, or provide the app with a list of IRNs (internal reference numbers, Te Papa's record identifiers), which will be individually queried and returned.

When your config and mapping are ready, run the app with `python Blastochor.py`.

### Setup
`api_key_env`: Environment name for your unique API key. Default is TE-PAPA-KEY
`mapping_file`: Filename for file containing data mapping rules. No default (handled within app)
`corefile`: If exporting multiple files, set to the label of the primary file, eg "core". Default is blank
`input_dir`: Directory holding any source files, like a skiplist or list or IRNs. Default is input_files
`output_dir`: Directory for exported CSVs. Default is output_files
`use_skiplist`: Set to True if using a skiplist. Default is False
`skipfile`: Filename for skiplist. Default is blank

### Run
`mode`: Set to search or list. Default is search
`quiet`: Set to False if you want progress messages written to the CLI. Default is True
`base_url`: URL used to query the API. Default is https://data.tepapa.govt.nz/collection/
`endpoint`: Used when querying individual records. Set to the primary endpoint you want data from. Default is object

### List mode settings
`source`: Filename for list of IRNs to query

### Search mode settings
`max-records`: Set a limit on the number of records you want to export. Default is -1 (no limit)
`size`: Set a limit on the number of records returned in one page of results. Default is 100

`query`: String to search for. Default is * (wildcard)
`sort_field`: Fieldname to sort results by, such as id, \_meta.modified. Default is blank (sorts by id)
`sort_value`: Direction of sort, asc or desc. Default is blank (sorts asc)

`collection`: Set collection to constrain search. Uses the APIs collection labels (PacificCultures, not Pacific Cultures). Default is blank
`allows_download`: Set to True to only return object records that include downloadable images, False to only return records that don't. Default is blank
`min_image_size`: Only export object records that have images that are at least this many px on each side. Default is blank
`keyword_fields`: Fieldnames for extra filters on your search. Separate with a comma and no space
`keyword_values`: Values for extra filters. Ensure you have the same number of terms as `keyword_fields` and they're in the right order.

## Mapping
Mapping files are YAML (.yaml) files that name the CSVs that should be created, triggers for harvesting additional records, and lines of rules with the export-side fields in each file. Each rule then includes the API source field used and the transformation rules applied.

Each output file is a list item containing a dictionary of options.

`label` is what the app uses to generate output files and ensure they're applying the right rules to the right records.

`primary_endpoint` is the endpoint (eg object, agent, taxon) this file will mainly use. Other endpoints can be specified in certain processing functions.

`explode` sets a field with a list value where each child is written out separately, such as when you want a new row for every image attached to an object record.

`reduce` sets a part of a whole record, applying all the following rules just to that section. Use this if the file only needs part of a record to simplify the processing rules.

`extend` contains a list of triggers, identifying certain fields that contain IRNs that should also be harvested. For example:
endpoint: fieldcollection
path: evidenceFor.atEvent.id
for_label: event

This checks harvested records for an IRN in the evidenceFor.atEvent.id field. If found, it will send a separate query to the fieldcollection endpoint, storing the record for later use in the `event` file.

If `for_label` is `null`, the record will be saved but not written out anywhere - do this if you just need some of the record's data for another function.

The `fields` section contains a list of data transformation rules, headed up with the output field names. These need to be in the order you want them to show in your CSV. The rules are applied to every record included in the file.

Each field then contains a list of functions (just one or several), which contain the API fields, strings, integers, or other parameters they'll be working on.

For example:
- occurrenceID:
  - literal:
    - pid

This means the file will have a column called `OccurrenceID`, which take a straight copy of the contents of the record's `pid` field.

When using a field name as a parameter, you need to provide the full path (unless you've `reduced` the record - more below). If one of the fields in the path contains a list, include an `i` to show it needs to be iterated through. For example:
`identification.i.identifiedBy.title`

Functions can be chained together by adding them as further list items.

### Available functions
`literal`
Copies the value at the given location
- parameters: field path. If the path includes a list, add an integer to copy a specified list member. Use `collate_list` to copy all list members
- example: `pid`
- example: `additionalType, 0`
- example: `production.i.creator.title, 1`

`hardcoded`
Sets the value to the string provided
- parameters: a string
- example: "https://data.tepapa.govt.nz"

`collate_list`
Gets all values of a field within a list. Automatically concatenated with "|" before writing out.
- parameters: field path
- example: `hasRepresentation.i.rights.title`

More functions coming...