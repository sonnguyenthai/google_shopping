# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import lxml.etree
import lxml.builder
import re
import os
from datetime import datetime

from scrapy.utils.project import get_project_settings


PAT = re.compile('\W')

class GoogleShoppingPipeline(object):
    def process_item(self, item, spider):
        self._export_xml(item)
        return item

    def _export_xml(self, item):
        #name = item['matching'].gtin
        xml_builder = lxml.builder.ElementMaker()
        root = xml_builder.root

        sellers = []
        for seller in item['sellers']:
            x_seller = xml_builder.seller(
                xml_builder.name(seller.name),
                xml_builder.details(seller.details),
                xml_builder.baseprice(seller.baseprice),
                xml_builder.totalprice(seller.totalprice),
                xml_builder.url(seller.url)
            )
            sellers.append(x_seller)

        matching = xml_builder.matching(
            xml_builder.brand(item['matching'].brand),
            xml_builder.reference(item['matching'].reference),
            xml_builder.gtin(item['matching'].gtin),
        )

        xml  = root(
            xml_builder.url(item['url']),
            xml_builder.ProductImageUrl(item['image_url']),
            xml_builder.ProductLabel(item['label']),
            xml_builder.ProductDescription(item['description']),
            xml_builder.sellers(*sellers),
            matching,
            xml_builder.parsingdate(item['date'])
        )

        cont = lxml.etree.tostring(xml, pretty_print=True, encoding='utf-8', xml_declaration=True)

        settings = get_project_settings()

        path = settings.get('PRODUCT_PATH')

        name_by_datetime =  PAT.sub("_", item['date'])
        name_by_date = PAT.sub("_", datetime.utcnow().strftime("%d_%m_%Y"))
        directory = os.path.join(path, name_by_date)

        if not os.path.exists(directory):
            os.makedirs(directory)

        name = "%s_%s_%s" %(
            PAT.sub("_", item['matching'].brand),
            item['matching'].gtin,
            name_by_datetime)
        f = open('%s/%s.xml' %(directory,name), 'w+')
        f.write(cont)
        f.close()