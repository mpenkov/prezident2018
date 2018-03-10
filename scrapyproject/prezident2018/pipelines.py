# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import json

import scrapy.exporters
import scrapy.utils.serialize


class LineExporter(scrapy.exporters.JsonLinesItemExporter):

    def export_item(self, item):
        itemdict = dict(self._get_serialized_fields(item))
        data = json.dumps(itemdict, ensure_ascii=False) + '\n'
        self.file.write(data.encode("utf-8"))
