import io
import re
import string
import urlparse
import urllib
from datetime import datetime
from itertools import islice

from scrapy.log import ERROR, WARNING, INFO
from scrapy.http import Request
from scrapy.spider import Spider
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


# Regular expression to match integer or floating point number with optional comma:
# 1; 12; 1,132,334; 1.05; 1,123.09
FLOATING_POINT_RGEX = re.compile('\d{1,3}[,\d{3}]*\.?\d*')

# 1; 12; 1.132.334; 1,05; 1.123,09 (French number format)
FR_FLOATING_POINT_RGEX = re.compile('\d{1,3}[.\d{3}]*\,?\d*')

def identity(x):
    return x

def cond_set(item, key, values, conv=identity):
    """Conditionally sets the first element of the given iterable to the given
    dict.

    The condition is that the key is not set in the item or its value is None.
    Also, the value to be set must not be None.
    """
    try:
        if values:
            value = next(iter(values))
            cond_set_value(item, key, value, conv)
    except StopIteration:
        pass

def cond_set_value(item, key, value, conv=identity):
    """Conditionally sets the given value to the given dict.

    The condition is that the key is not set in the item or its value is None.
    Also, the value to be set must not be None.
    """
    if item.get(key) is None and value is not None and conv(value) is not None:
        item[key] = conv(value)

class BaseSpider(Spider):
    start_urls = []

    banned_proxies = []

    SEARCH_URL = None  # Override.


    def __init__(self,
                 quantity=1,
                 searchterms_str=None, searchterms_fn='./brands.csv',
                 site_name=None,
                 *args, **kwargs):

        super(BaseSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_closed, signals.spider_closed)
        dispatcher.connect(self.spider_opened, signals.spider_opened)

        if site_name is None:
            assert len(self.allowed_domains) == 1, \
                "A single allowed domain is required to auto-detect site name."
            self.site_name = self.allowed_domains[0]
        else:
            self.site_name = site_name

        self.url_formatter = string.Formatter()

        self.quantity = int(quantity)*100

        self.searchterms = []
        if searchterms_str is not None:
            self.searchterms = searchterms_str.decode('utf-8').split(',')
        elif searchterms_fn is not None:
            with io.open(searchterms_fn, encoding='utf-8') as f:
                self.searchterms = f.readlines()
        else:
            self.log("No search terms provided!", ERROR)

        self.log("Created for %s with %d search terms."
                 % (self.site_name, len(self.searchterms)), INFO)

    def spider_closed(self, spider, reason):
        pass

    def spider_opened(self, spider):
        pass

    def start_requests(self):
        """Generate Requests from the SEARCH_URL and the search terms."""
        for st in self.searchterms:
            yield Request(
                self.url_formatter.format(
                    self.SEARCH_URL,
                    search_term=urllib.quote_plus(st.encode('utf-8')),
                ),
                meta={'search_term': st, 'remaining': self.quantity},
            )

    def parse(self, response):
        if self._search_page_error(response):
            remaining = response.meta['remaining']
            search_term = response.meta['search_term']

            self.log("For search term '%s' with %d items remaining,"
                     " failed to retrieve search page: %s"
                     % (search_term, remaining, response.request.url),
                     ERROR)
        else:
            prods_count = -1  # Also used after the loop.
            for prods_count, request_or_prod in enumerate(
                    self._get_products(response)):
                yield request_or_prod
            prods_count += 1  # Fix counter.

            request = self._get_next_products_page(response, prods_count)
            if request is not None:
                yield request


    def _get_products(self, response):
        remaining = response.meta['remaining']
        search_term = response.meta['search_term']
        prods_per_page = response.meta.get('products_per_page')
        total_matches = response.meta.get('total_matches')

        prods = self._scrape_product_links(response)

        if prods_per_page is None:
            # Materialize prods to get its size.
            prods = list(prods)
            prods_per_page = len(prods)
            response.meta['products_per_page'] = prods_per_page

        if total_matches is None:
            total_matches = self._scrape_total_matches(response)
            if total_matches is not None:
                response.meta['total_matches'] = total_matches
                self.log("Found %d total matches." % total_matches, INFO)
            else:
                self.log(
                    "Failed to parse total matches for %s" % response.url,
                    ERROR
                )

        if total_matches and not prods_per_page:
            # Parsing the page failed. Give up.
            self.log("Failed to get products for %s" % response.url, ERROR)
            return

        for i, (prod_url, prod_item) in enumerate(islice(prods, 0, remaining)):
            prod_item['date'] = datetime.now().strftime("%d-%m-%Y %H:%M")

            if prod_url is None:
                # The product is complete, no need for another request.
                yield prod_item
            elif isinstance(prod_url, Request):
                cond_set_value(prod_item, 'url', prod_url.url)  # Tentative.
                yield prod_url
            else:
                # Another request is necessary to complete the product.
                url = urlparse.urljoin(response.url, prod_url)
                cond_set_value(prod_item, 'url', url)  # Tentative.
                yield Request(
                    url,
                    callback=self.parse_product,
                    meta={'product': prod_item,
                          'search_term': search_term},
                )

    def _get_next_products_page(self, response, prods_found):
        link_page_attempt = response.meta.get('link_page_attempt', 1)

        result = None
        if prods_found is not None:
            # This was a real product listing page.
            remaining = response.meta['remaining']
            remaining -= prods_found
            if remaining > 0:
                next_page = self._scrape_next_results_page_link(response)
                if next_page is None:
                    pass
                elif isinstance(next_page, Request):
                    next_page.meta['remaining'] = remaining
                    result = next_page
                else:
                    url = urlparse.urljoin(response.url, next_page)
                    new_meta = dict(response.meta)
                    new_meta['remaining'] = remaining
                    result = Request(url, self.parse, meta=new_meta, priority=1)
        elif link_page_attempt > self.MAX_RETRIES:
            self.log(
                "Giving up on results page after %d attempts: %s" % (
                    link_page_attempt, response.request.url),
                ERROR
            )
        else:
            self.log(
                "Will retry to get results page (attempt %d): %s" % (
                    link_page_attempt, response.request.url),
                WARNING
            )

            # Found no product links. Probably a transient error, lets retry.
            new_meta = response.meta.copy()
            new_meta['link_page_attempt'] = link_page_attempt + 1
            result = response.request.replace(
                meta=new_meta, cookies={}, dont_filter=True)

        return result

    ## Abstract methods.

    def parse_product(self, response):
        """parse_product(response:Response)

        Handles parsing of a product page.
        """
        raise NotImplementedError

    def _search_page_error(self, response):
        """_search_page_error(response:Response):bool

        Sometimes an error status code is not returned and an error page is
        displayed. This methods detects that case for the search page.
        """
        # Default implementation for sites that send proper status codes.
        return False

    def _scrape_total_matches(self, response):
        """_scrape_total_matches(response:Response):int

        Scrapes the total number of matches of the search term.
        """
        raise NotImplementedError

    def _scrape_product_links(self, response):
        """_scrape_product_links(response:Response)
                :iter<tuple<str, SiteProductItem>>

        Returns the products in the current results page and a TyreProductItem
        which may be partially initialized.
        """
        raise NotImplementedError

    def _scrape_next_results_page_link(self, response):
        """_scrape_next_results_page_link(response:Response):str

        Scrapes the URL for the next results page.
        It should return None if no next page is available.
        """
        raise NotImplementedError
