# Blastochor: Harvest data from Te Papa's collections API

["blastochory, where the stem of the plant crawls along the ground to deposit its seed far from the base of the plant"](https://en.wikipedia.org/wiki/Seed_dispersal#Autochory)

This tool lets you access Te Papa's collections API using some basic configuration options, transform the data based on a mapping file, and export the data as a single CSV or multiple CSVs that reference one another, such as can be combined in a Darwin Core Archive (DwC-A).

This repo includes a basic mapping file that will be used if another is not provided.

[API documentation](https://data.tepapa.govt.nz/docs/)

## Still to do
- A complete default mapping that dumps out as much data as possible
- Conditional inclusion of records after harvest has run (eg only write out if x field is present, if image size is over x pixels)
- Sample mode to pull down representative range of records for testing
- Output as json
- Command line options to run a search or single record, returning json or flattened default csv
- Front end to create mapping file and run from browser
- Look into how easily this app could be forked for other museum APIs

## Installation
Clone this repo using `git clone`. Install the following packages:
- Requests
- PyYAML

Go to https://data.tepapa.govt.nz/docs/register.html and register for an API key. Add the API key to an environment variable called 'TE-PAPA-KEY'.

If using a custom mapping, this should sit alongside Config.yml.

## Usage
Edit the `Config.yml` file to set search and export parameters.

The main functional setting is `search`, `scroll` or `list`. You can either send a search query, which will page through and return all relevant records (limit 50K), scroll through all records (no limit) or provide the app with a list of IRNs (internal reference numbers, Te Papa's record identifiers), which will be individually queried and returned.

When your config and mapping are ready, run the app with `python -m app`.

### Setup
`api_key_env`: Environment name for your unique API key. Default is TE-PAPA-KEY

`mapping_file`: Filename for file containing data mapping rules. Default is null (points to a default mapping inside the app)

`corefile`: If exporting multiple files, set to the label of the primary file, eg "core". Default is null

`input_dir`: Directory holding any source files, like a skiplist or list or IRNs. Default is input_files

`output_dir`: Directory for exported CSVs. Default is output_files

`use_skiplist`: Set to True if using a skiplist. Default is False

`skipfile`: Filename for skiplist. Default is null

`min_image_size`: Only export object records that have images that are at least this many px on each side. Default is blank

`max_list_size`: Only collate lists of values into a single value up to the specified size. Default is 100

`group_rows`: If exploding records into multiple rows, set to true to group them under a parent row. Default is null

`parent_label`: If grouping rows, sets a label for the parent. Only used if `group_rows` is true

`parent_fields`, `child_fields`, `ungrouped_fields`: Specify fields that need to be included or excluded for each kind of row. Set `include` to true to only include the specified fields, or false to include everything except those specified. Only used if `group_rows` is true

### Run
`mode`: Set to search or list. Default is search

`quiet`: Set to False if you want progress messages written to the CLI. Default is True

`base_url`: URL used to query the API. Default is https://data.tepapa.govt.nz/collection/

`endpoint`: Used when querying individual records. Set to the primary endpoint you want data from. Default is object

`timeout`: How long in seconds to allow each query before timing out and retrying. Default is 5

`attempts`: How many times to retry each query before returning None. Default is 3

### List mode settings
`list_source`: Filename for list of IRNs to query

### Search/scroll mode settings
`max-records`: Set a limit on the number of records you want to export. Default is -1 (no limit)

`size`: Set a limit on the number of records returned in one page of results. Set to a maximum of 1000 for scroll. Default is 100

`query`: String to search for. Default is * (wildcard)

`sort`: Fieldname to sort results by, such as id, \_meta.modified. Add a `-` before the field to sort in reverse order. Default is null (sorts by id)

Filters:

`collection`: Set collection to constrain search. Uses the APIs collection labels (PacificCultures, not Pacific Cultures). Default is null

`allows_download`: Set to true to only return object records that include downloadable images, false to only return records that don't. Default is null

`keyword_fields`: Fieldnames for extra filters on your search. Separate with `, `

`keyword_values`: Values for extra filters. Ensure you have the same number of terms as `keyword_fields` and they're in the right order. Separate with `, `

## Mapping
Mapping files are YAML (.yaml) files that name the CSVs that should be created, triggers for harvesting additional records, and lines of rules with the export-side fields in each file. Each rule then includes the API source field used and the transformation rules applied.

Each output file is a list item containing a dictionary of options.

`label` is what the app uses to generate output files and ensure they're applying the right rules to the right records.

`reference_column` adds a column to the start of the CSV using the provided title, leaving a place for non-core files to reference the core file in each row.

`primary_endpoint` is the endpoint (eg object, agent, taxon) this file will mainly use. Other endpoints can be specified in certain processing functions.

`explode` sets a field with a list value where each child is written out separately, such as when you want a new row for every image attached to an object record.

`reduce` cuts down the record's data to just the specified section, for example the list of images under `hasRepresentation`. This makes it easier to then navigate to subfields. The script expects the reduced data to be a list.

### Extend
`extend` contains a list of triggers, identifying certain fields that contain IRNs that should also be harvested. For example:
```
endpoint: fieldcollection
path: evidenceFor.atEvent.id
for_label: event
```

This checks harvested records for an IRN in the evidenceFor.atEvent.id field. If found, it will send a separate query to the fieldcollection endpoint, storing the record for later use in the `event` file.

If the record has already been harvested, the record object will just be updated with a flag that it needs to be included in that file.

To output another CSV with the same endpoint as the core file, just point the extend rule back to the source. For example:
```
endpoint: object
path: id
for_label: identification
```

If `for_label` is `null`, the record will be saved but not written out anywhere - do this if you just need some of the record's data for another function.

### Fields
The `fields` section contains a list of data transformation rules, headed up with the output field names. These need to be in the order you want them to show in your CSV. The rules are applied to every record included in the file.

Each field then contains a list of functions (just one or several), which contain the API fields, strings, integers, or other parameters they'll be working on.

For example:
```
- occurrenceID:
  - literal:
    - pid
```

This means the file will have a column called `occurrenceID`, which take a straight copy of the contents of the record's `pid` field.

When using a field name as a parameter, you need to provide the full path (unless you've `reduced` the record - see above). If one of the fields in the path contains a list, include an `i` to show it needs to be iterated through. For example:
`identification.i.identifiedBy.title`

Functions can be chained together by adding them as further list items.

### Available functions
`literal`

Copies the value at the given location
- parameters: path to field. If the path includes a list, add an integer to copy a specified list member - if no integer is provided for a list, it will just get the first (`0`) value.
- example: `pid`
- example: `additionalType, 0`
- example: `production.i.creator.title, 1`

`hardcoded`

Sets the value to the string provided. Set the parameter to `explode_ordinal` if you want the value to be the row's order within the record.
- parameters: a string
- example: `https://data.tepapa.govt.nz`

`collate_list`

Gets all values of a field within a list. Automatically concatenated with " | " before writing out. Maximum length of list is controlled in `Config.yml`.
- parameters: path to field
- example: `hasRepresentation.i.rights.title`

`clean_html`

Removes unwanted html markup from a value previously returned, such as a `description`.
- parameters: null

`concatenate`

Joins values in a list using " | ", after removing None values. Use after calling another function that produces a list
- parameters: null

`conditional`

Returns a value for a given field if another field matches a specified value, indicated using `=`. Both paths need to be in the same section of the record. If the path given points to a list, each child of the list will be checked. If multiple values match only the first will be returned.
- parameters: path to field and path to field to check, with the specified value
- example: `related.i.contentUrl` and `related.i.title=ORCID`

`country_code`

Finds a country name in a record and looks up its ISO 2-character country code.
- parameters: path to a field that contains a country name
- example: `evidenceFor.atEvent.atLocation.country`

`create_filename`

Use after a function that returns a string. Replaces unsafe characters (` , ?, \, :, ;` and so on) with an underscore, or removes them.
- parameters: suffix to append to the filename
- example: `jpg`

`fallback`

Use to substitute another value if the original request returns None. Next another set of functions and parameters underneath.
```
- format_string:
  - {} ({})
  - production.i.contributor.title, production.i.role
  - required
- fallback:
  - literal:
    - production.i.contributor.title
```

This returns a formatted string if both a contributor's title and their role are present. Because `format_string` uses the required parameter, if there's no `role` the function will return None, and then just the title will be returned as a literal value.

`for_each`

Use after another function that returns a list. Goes through and performs further transformations on each member. You can add the `concatenate` function below `for_each`, or it will automatically happen when writing out. Format this in the mapping document by nesting the rest of the functions below, for example:
```
- recordedByID:
  - collate_list:
    - evidenceFor.atEvent.recordedBy.i.id
  - for_each:
    - lookup:
      - agent
    - conditional:
      - related.i.contentUrl
      - related.i.title=ORCID
  - concatenate:
    - null
```

This finds the agent id for every person at a specimen collection event, looks them up one at a time, and checks if they have an ORCID identifier. None values get stripped out once all child functions have run.

`format_string`

Finds a value and inserts it into a provided string at a specified place. Mark the location for each value using `{}`. Include an optional third parameter `required` to return None if any of the values are unavailable.
- parameters: string, path to field (if more than one, separated with `, `), required (optional)
- example: `https://collections.tepapa.govt.nz/object/{}` and `id`
- example: `{} of {}` and `typeStatus, qualifiedName` and `required`

`lookup`

Find an IRN in the record and return the associated record for the next function. Record needs to have been harvested either directly or using `extend` functionality.
- parameters: endpoint and path to field for the record's IRN
- example: `agent` and `production.i.contributor.id`

`must_match`

After pulling out a value or list of values, check each term against an authority list and only keep the ones you want.
- parameters: list of authority terms, separated with `, `. Make sure they're all lowercase
- example: `canvas, paper, plaster, cardboard, ceramic, wood, clay`

`prioritise`

Try multiple paths in order and return the value of the first available one. Useful when trying to return the most precise available location.
- parameters: list of paths, separated by `, `

`related`

Make a fresh query to the special /related endpoint for the current record, returning records that are connected in some way. Can only be used on a complete record as it requires the `href` value. Set a size to limit the number of results (default is 100), and specify types of records to filter down.
- parameters: size (int) and types (Capitalise, separate with `,` - note the lack of a space character)
- example: `50` and `Object,Specimen`

`use_config`

Pull a specified term out of the config file. Can also use `hardcoded` but lets you avoid doubling up if you change the parameter.
- parameters: a string
- example: `base_url`

`use_group_labels`

If grouping rows for each record, lets you set a label for the parent row, each child row, and standalone rows.
- parameters: three strings, can be null
- example: `sequence`, `image`, `image`