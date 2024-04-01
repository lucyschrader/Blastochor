import os, shutil
from datetime import datetime
from src.setup.Settings import read_config


def create_export_dir():
	output_dir = read_config("output_dir")
	export_filename = read_config("export_filename")
	export_path = "{d}/{e}".format(d=output_dir, e=export_filename)
	if not os.path.exists(export_path):
		os.mkdir(export_path)


def validate_exports():
	pass


def zip_exported_files(export_files):
	# Currently produces invalid zip files, so not using
	from zipfile import ZipFile
	output_dir = read_config("output_dir")
	export_filename = read_config("export_filename")
	zipped_filename = "{}.zip".format(export_filename)
	write_location = "{d}/{e}/{f}".format(d=output_dir,
	                                      e=export_filename,
	                                      f=zipped_filename)
	with ZipFile(write_location, "w") as export_zip:
		for file in export_files:
			file_path = "{d}/{e}/{f}".format(d=output_dir,
	                                        e=export_filename,
	                                        f=file)
			export_zip.write(file_path)
	return write_location


def delete_old_exports():
	output_dir = read_config("output_dir")
	exports = os.listdir(output_dir)
	for item in exports:
		item_path = "{d}/{i}".format(d=output_dir,
		                             i=item)
		last_modified = os.path.getmtime(item_path)
		last_modified_dt = datetime.fromtimestamp(last_modified)
		if compare_timestamps(last_modified_dt):
			if os.path.isdir(item_path):
				shutil.rmtree(item_path)
			elif os.path.isfile(item_path):
				os.remove(item_path)


def compare_timestamps(last_modified):
	now = datetime.now()
	delta = now - last_modified
	if delta.days > 14:
		return True
	return False
