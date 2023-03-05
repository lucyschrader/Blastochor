# -*- coding: utf-8 -*-

from blastochor.settings.Settings import config
from blastochor.util import Mapper, Harvester, Records

if __name__ == '__main__':
    print("blastochor blasting")
    harvester = Harvester.harvester
    if config.get("mode") == "search":
        harvester.harvest_from_search()
    elif config.get("mode") == "list":
        input_list = Settings.InputList(settings.list.source)
        harvester.harvest_from_list(input_list.irn_list)

    for output in Mapper.mapping.outputs:
        output.write_to_csv()