import os
import urlparse
from datetime import datetime

from lxml import etree

from scrapy.http import Request
from scrapy.spider import Spider
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from google_shopping.spiders import FR_FLOATING_POINT_RGEX
from google_shopping.items import Seller, Matching, TyreProductItem
from google_shopping.settings import PICKLEDB_NAME

import pickledb


def get_matching_value(response, name, alt=u"R\xe9f\xe9rences"):
    """
    Get matching value (Brand, Reference, GTIN) by name
    :param response:
    :param name:
    :param alt:
    :return: (String) value
    """
    if not alt:
        alt = name
    value = response.xpath(
        u'//*[contains(string(.),"%s") '
        u'or contains(string(.),"%s")]'
        u'/following-sibling::*[contains(@class, "specs-value")]/text()' %(name, alt)
    ).extract()

    if not value:
        return ''

    return value[0].strip()
    
class UpdatePrice(Spider):

    name = "update_price"


    def __init__(self, *args, **kwargs):
        super(UpdatePrice, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        dispatcher.connect(self.spider_opened, signals.spider_opened)

    def spider_closed(self, spider, reason):
        if reason == 'finished':
            db = pickledb.load(PICKLEDB_NAME, True)
            db.set(self.name, 'Done')

    def spider_opened(self, spider):
        db = pickledb.load(PICKLEDB_NAME, True)
        db.set(self.name, 'Running')

    def start_requests(self):
        """
        Read xml file then make request to product url
        """
        path = self.settings.get('PRODUCT_PATH', '')
        if path:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(".xml"):
                        xml_file = os.path.join(root, file)
                        xml = etree.parse(xml_file)
                        url = xml.xpath('//root/url')
                        if url:
                            url = url[0].text
                            yield Request(url, meta={'xml':xml}, dont_filter=True)

    def parse(self, response):
        """
        Get all sellers from google shopping product page
        :param response:
        :return: TyreProductItem
        """
        product = TyreProductItem()
        
        product['date'] = datetime.now().strftime("%d-%m-%Y %H:%M")
        brand = get_matching_value(response, 'Brand', 'Marque')
        
        label = response.xpath('string(//h1[@id="product-name"])').extract()
        if label:
            product['label'] = label[0].strip()
        else:
             product['label'] = ''

        desc = response.xpath(
            '//div[@id="product-description-full"]/text()'
        ).extract()
        if desc:
            product['description'] = desc[0]
        else:
            product['description'] = ''

        #img = response.xpath('//img[contains(@class, "_ioe")]/@src').extract()
        img = response.xpath('//div[@id="pp-altimg-init-main"]/img/@src').extract()
        if img:
            product['image_url'] = img[0]
        else:
            product['image_url'] = ''

        product['url'] = response.url

        gtin = get_matching_value(response, 'GTIN', 'GTIN')
        ref = get_matching_value(response, 'Part Numbers')

        matching = Matching(brand=brand, reference=ref, gtin=gtin)

        product['matching'] = matching

        response.meta['product'] = product
        
        sellers_url = response.xpath(
            '//div[@class="pag-bottom-links"]/a[@class="pag-detail-link" '
            'and contains(string(.), "en ligne")]/@href').extract()
        if sellers_url:
            s_url = urlparse.urljoin(response.url, sellers_url[0])
            return Request(url=s_url, meta=response.meta,
                           callback=self._get_sellers, dont_filter=True)
        else:
            return self._get_sellers(response)

    def _get_sellers(self, response):
        """
        Get all sellers from google shopping product page
        :param response:
        :return: TyreProductItem
        """
        prod = response.meta['product']
        sellers = []
        trs = response.xpath('//tr[@class="os-row"]')
        for tr in trs:
            name = tr.xpath(
                'string(.//td[@class="os-seller-name"])').extract()
            if name:
                name = name[0].strip()
            else:
                name = ''

            details = tr.xpath(
                'string(.//td[@class="os-details-col"])').extract()
            if details:
                details = details[0].strip()
            else:
                details = ''

            price = tr.xpath(
                'string(.//td[@class="os-price-col"])').re(FR_FLOATING_POINT_RGEX)
            if price:
                baseprice = price[0].strip()
            else:
                baseprice = ''

            total = tr.xpath(
                'string(.//td[@class="os-total-col"])').re(FR_FLOATING_POINT_RGEX)
            if total:
                totalprice = total[0].strip()
            else:
                totalprice = ''

            url = tr.xpath(
                'string(.//td[@class="os-seller-name"]//a/@href)').extract()
            if url:
                query = urlparse.urlparse(url[0]).query
                query_dict = urlparse.parse_qs(query)
                seller_url = query_dict.get('adurl', [''])[0]
            else:
                seller_url = ''

            seller = Seller(
                name=name, details=details,
                baseprice=baseprice, totalprice=totalprice, url=seller_url)
            sellers.append(seller)

        prod['sellers'] = sellers

        return prod