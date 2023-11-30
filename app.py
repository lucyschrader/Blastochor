# -*- coding: utf-8 -*-
import click
from blastochor.settings.Settings import read_config, write_config, setup_project, add_limit_to_config, update_settings
from blastochor.settings.InputList import read_input_list
from blastochor.settings.Stats import stats
from blastochor.util.Mapper import Mapping
from blastochor.util.Harvester import Harvester

def blasto():
    print("blastochor blasting")

    stats.start()

    write_config("mapping", Mapping())
    harvester = Harvester()

    mode = read_config("mode")
    if mode == "list":
        read_input_list(read_config("list_source"))
        harvester.harvest_from_list()
    else:
        harvester.complete_harvest(mode)

    # (Hopefully) temporary workaround to some ETL coordinate transformation
    if read_config("coordinate_workaround"):
        from blastochor.util.CoordinateWorkaround import apply_coordinate_workaround
        apply_coordinate_workaround()

    mapping = read_config("mapping")
    for output in mapping.outputs:
        output.write_to_csv()

    stats.end()
    stats.print_stats()


@click.command()
@click.option('--project', default='none', help='name of pre-defined project')
@click.option('--limit', default=-1, help='override max record limit in config when testing')
def cli(project, limit):
    setup_project(project)
    add_limit_to_config(limit)
    update_settings()

    blasto()


if __name__ == "__main__":
    cli()

'''
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
'''
