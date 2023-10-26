# -*- coding: utf-8 -*-

from blastochor.settings.Settings import config, InputList
from blastochor.settings.Stats import stats
from blastochor.util import Mapper, Harvester, Records

def blasto():
    print("blastochor blasting")

    stats.start()

    harvester = Harvester.harvester
    mode = config.get("mode")
    if mode == "list":
        InputList(config.get("list_source"))
        harvester.harvest_from_list()
    else:
        harvester.complete_harvest(mode)

    # (Hopefully) temporary workaround to some ETL coordinate transformation
    if config.get("coordinate_workaround"):
        from blastochor.util.CoordinateWorkaround import apply_coordinate_workaround
        apply_coordinate_workaround()

    for output in Mapper.mapping.outputs:
        output.write_to_csv()

    stats.end()
    stats.print_stats()

if __name__ == '__main__':
    if config["profiler_on"]:
        import cProfile, pstats
        profiler = cProfile.Profile()
        profiler.enable()
        blasto()
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.strip_dirs()
        stats.dump_stats(config["profiler_filename"])
    else:
        blasto()