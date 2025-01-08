import click
from src.setup.Settings import (read_config, write_config, setup_project, update_query, add_limit_to_config,
                                update_settings, update_list_source)
from src.setup.InputList import read_input_list
from src.monitoring.Stats import stats
from src.util.ExportHandler import create_export_dir, delete_old_exports
from src.monitoring.ExportReport import generate_export_report
from src.setup.Mapper import Mapping
from src.util.Harvester import Harvester


# Harvests records from a search or list of IRNs
# Harvested data is processed according to rules supplied in map
# Processed data is written out to one or more files
def blasto():
    print("Looks like team blasto is blasting off again")
    delete_old_exports()

    # Start stats
    stats.mark_time("start")

    write_config("mapping", Mapping())
    harvester = Harvester()

    # Read mode from config and run required harvest
    # Passes harvested data directly to processing
    mode = read_config("mode")
    if mode == "list":
        read_input_list(read_config("list_source"))
        harvester.harvest_from_list()
    else:
        harvester.complete_harvest(mode)

    # (Hopefully) temporary workaround to some ETL coordinate transformation
    if read_config("coordinate_workaround"):
        from src.util.CoordinateWorkaround import apply_coordinate_workaround
        apply_coordinate_workaround()

    # Create export directory
    create_export_dir()

    # Write out harvested and processed data
    mapping = read_config("mapping")
    stats.mark_time("processing start")
    for output in mapping.outputs:
        output.write_output()
    stats.mark_time("processing end")

    # Stop stats and write results
    stats.mark_time("end")
    generate_export_report()


@click.command()
@click.option('--project', default='none', help='name of pre-defined project')
@click.option('--query', default='none', help='override query string in config')
@click.option('--listsource', default='none', help='override list source in config')
@click.option('--limit', default=-1, help='override max record limit in config when testing')
@click.option('--profiler', default=False, help='run with cProfile')
@click.option('--exportid', default=None, help='provide an id to use when writing out script results')
def cli(project, query, listsource, limit, profiler, exportid):
    setup_project(project)
    update_query(query)
    update_list_source(listsource)
    add_limit_to_config(limit)
    write_config("export_id", exportid)
    update_settings()

    if profiler:
        from src.monitoring import Profiler
        Profiler.profiler.enable()
        blasto()
        Profiler.profiler.disable()
        Profiler.output_profile()
    else:
        blasto()


if __name__ == "__main__":
    cli()