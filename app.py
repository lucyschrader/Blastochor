# -*- coding: utf-8 -*-

from blastochor.settings.Settings import config, InputList
from blastochor.settings.Stats import stats
from blastochor.util import Mapper, Harvester, Records

if __name__ == '__main__':
    print("blastochor blasting")

    stats.start()

    harvester = Harvester.harvester
    mode = config.get("mode")
    if mode == "list":
        InputList(config.get("list_source"))
        harvester.harvest_from_list()
    else:
        harvester.complete_harvest(mode)

    for output in Mapper.mapping.outputs:
        output.write_to_csv()

    stats.end()
    stats.print_stats()