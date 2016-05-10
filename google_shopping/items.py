# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import collections

from scrapy import Field, Item

Seller = collections.namedtuple(
    'Seller', ['name', 'details', 'baseprice', 'totalprice', 'url'])

Matching = collections.namedtuple('Matching', ['brand', 'reference', 'gtin'])

class TyreProductItem(Item):
    url = Field()
    image_url = Field()
    label = Field()
    description = Field()
    sellers = Field() # List of Seller objects
    matching = Field() # Matching object
    date = Field()