# -*- coding: utf-8 -*-

from blastochor.settings.Settings import config, stats
from blastochor.util import Mapper, Harvester, Records

# TODO: Add a function that tracks how long it takes to run
# And probably a progress bar tbh

if __name__ == '__main__':
    print("blastochor blasting")

    stats.start()

    harvester = Harvester.harvester
    if config.get("mode") == "search":
        harvester.harvest_from_search()
    elif config.get("mode") == "list":
        input_list = Settings.InputList(settings.list.source)
        harvester.harvest_from_list(input_list.irn_list)

    for output in Mapper.mapping.outputs:
        output.write_to_csv()

    stats.end()
    stats.print_stats()