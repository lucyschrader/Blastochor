import os
import yaml
import csv
from datetime import datetime
from src.setup.Settings import read_config, write_config
from src.monitoring.Stats import stats


def generate_export_report():
	stats.process_runtimes()
	stats.count_recently_modified_records()
	output_dir = read_config("output_dir")
	export_filename = read_config("export_filename")
	export_report_filename = "{}.yaml".format(export_filename)
	export_report_path = "{d}/{e}/{f}".format(d=output_dir,
	                                          e=export_filename,
	                                          f=export_report_filename)
	write_config("export_report_path", export_report_path)
	export_report_dict = gather_report_data()
	with open(export_report_path, "w", encoding="utf-8") as export_report:
		yaml.dump(export_report_dict, export_report)

	stats.print_stats()


def gather_report_data():
	report_dict = {"export_id": read_config("export_id"),
	               "runtime": stats.run_time,
	               "api_calls": stats.api_call_count,
	               "harvest_time": stats.harvest_time,
	               "extension_time": stats.extension_time,
	               "extension_records": stats.extension_records_count,
	               "processing_time": stats.processing_time,
	               "export_filenames": stats.export_filenames,
	               "update_counts": stats.modified_file_count}
	return report_dict


def clear_old_reports():
	output_dir = read_config("output_dir")
	export_report_dir = "{}/exports".format(output_dir)
	if os.path.exists(export_report_dir):
		export_reports = os.listdir(export_report_dir)
		for report in export_reports:
			file_path = "{d}/{f}".format(d=export_report_dir, f=report)
			last_modified = os.path.getmtime(file_path)
			last_modified_dt = datetime.fromtimestamp(last_modified)
			if compare_timestamps(last_modified_dt):
				os.remove(file_path)


def compare_timestamps(last_modified):
	now = datetime.now()
	delta = now - last_modified
	if delta.days > 7:
		return True
	return False


def analyse_export():
	output_dir = read_config("output_dir")
	export_report_path = read_config("export_report_path")
	if export_report_path:
		with open(export_report_path, "r", encoding="utf-8") as f:
			export_report = yaml.safe_load(f)
			export_files = export_report["export_filenames"]
			for file in export_files:
				export_file_path = "{d}/{f}".format(d=output_dir, f=file)
