# -*- coding: utf-8 -*-

import Settings
import askCO
import Harvester
import DataCollator
import Processor
import Mapper
import Writer

class DataExporter():
    def __init__(self):
        self.settings = Settings.Settings()
        self.mode = self.settings.mode
        self.quiet = self.settings.quiet

        self.mapping = Mapper.Mapping()
        self.harvester = HarvestCO.Harvester()
        self.records = DataCollator.Records()
        self.processor = Processor.ValueProcessor()

        if self.settings.corefile == None:
            self.settings.corefile = self.mapping.outputs[0]

        self.run_harvest()
        self.write_data()

    def run_harvest(self):
        if self.mode == "search":
            self.harvester.harvest_from_search()
        elif self.mode == "list":
            self.input_list = Settings.InputList(self.settings.list.source)
            self.harvester.harvest_from_list(self.input_list.irn_list)

    def write_data(self):
        for label in self.mapping.outputs:
            DataCollator.Output(label=label)

app = DataExporter()