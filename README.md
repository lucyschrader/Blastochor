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

When your config and mapping are ready, run the app with `python ApiExporter.py`.

### Setup
`api_key_env`: Environment name for your unique API key. Default is TE-PAPA-KEY
`mapping_file`: Filename for file containing data mapping rules. No default (handled within app)
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
`allows_download`: Set to True to only return object records that include downloadable images, False to only return records that don't. Default is None
`min_image_size`: Only export object records that have images that are at least this many px on each side. Default is 0
`keyword_fields`: Fieldnames for extra filters on your search. Separate with a comma and no space
`keyword_values`: Values for extra filters. Ensure you have the same number of terms as `keyword_fields` and they're in the right order.

## Mapping
Mapping files are plain text (.txt) files that name the CSVs that should be created, and lines of rules with the export-side fields in each file. Each rule then includes the API source field used and the transformation rules applied.

To start the mapping for a new CSV, use a \#:
`# Core`

A rule is made up of the output fieldname, an equals sign, and at least one function paired with parameters, usually a source value.
`occurrenceID = literal:pid`

This means that the \#Core CSV will include a column called 'occurrenceID', the value of which is created by taking the literal value of each record's `pid` field.

Functions can be chained together with a '|' and the `prev` parameter, for example:
`associatedMedia = collate_list:hasRepresentation, previewUrl | concatenate:prev`

An object record that has multiple images (`hasRepresentation`) will have each `previewUrl` value pulled out. Those values will then be concatenated into a single value, which populates the `associatedMedia` column.

### Functions

literal (parameters: fieldname)
Returns the literal value found in each record at the supplied field

hardcoded (parameters: string)
Returns the provided string for each record

collate_list (parameters: parent, fieldname, index)
Returns a string of multiple values, separated with '|'.
If the field is at the top level of the record, the parent is 'None'
Index is optional - use if you only want to retrieve a specific value from a list (for example, use 0 to just get the first value)

More functions coming...