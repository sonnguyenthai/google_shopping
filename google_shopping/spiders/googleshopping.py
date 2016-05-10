import urlparse

from scrapy.log import ERROR, DEBUG
from scrapy.http import Request
from scrapy.contrib.exporter import XmlItemExporter

from google_shopping.items import TyreProductItem, Matching, Seller
from google_shopping.spiders import BaseSpider, FR_FLOATING_POINT_RGEX
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

class GoogleProductsSpider(BaseSpider):
    name = 'google_products'
    allowed_domains = ["www.google.fr"]
    start_urls = []

    SEARCH_URL = ("https://www.google.fr/search?tbm=shop"
                  "&q={search_term}&num=100")


    def spider_closed(self, spider, reason):
        if reason == 'finished':
            db = pickledb.load(PICKLEDB_NAME, True)
            db.set(self.name, 'Done')

    def spider_opened(self, spider):
        db = pickledb.load(PICKLEDB_NAME, True)
        db.set(self.name, 'Running')

    def parse_product(self, response):

        product = response.meta['product']

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

        product['url'] = response.url[:response.url.find('?')]

        gtin = get_matching_value(response, 'GTIN', 'GTIN')
        ref = get_matching_value(response, 'Part Numbers')

        matching = Matching(brand=brand, reference=ref, gtin=gtin)

        product['matching'] = matching

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

    def _scrape_total_matches(self, response):
        return 0

    def _scrape_product_links(self, response):
        items = response.css('ol.product-results li.psli')
        if not items:
            items = response.css('ol.product-results li.psgi')
            if not items:
                items = response.xpath('//div[@id="ires"]/ol/li[@class="g"]')

        if not items:
            self.log("Found no product links.", DEBUG)

        for item in items:
            link = item.xpath('.//h3[@class="r"]/a/@href').extract()
            if link:
                link = urlparse.urljoin(response.url, link[0])
                if '/shopping/product/' in link:
                    yield link, TyreProductItem()

    def _scrape_next_results_page_link(self, response):
        next = response.xpath(
            '//td[@class="b"]/a/@href|//a[@id="pnnext"]/@href').extract()
        if not next:
            link = None
            self.log('Next page link not found', DEBUG)
        else:
            link = urlparse.urljoin(response.url, next[0])
        return link


