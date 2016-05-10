import base64
import re
import random
import urllib2
from datetime import datetime
from datetime import timedelta

import pickledb
from dateutil import parser
from scrapy import log
from scrapylib.crawlera import CrawleraMiddleware, ConnectionRefusedError

from settings import DELAY_TIME, PICKLEDB_NAME, BANNED_COUNT_KEY, RETRY_HTTP_CODES



def increase(key, value):
    DB = pickledb.load(PICKLEDB_NAME, True)
    a = DB.get(key)
    if not a:
        a = 0
    DB.set(key, a+value)

class RandomProxy(object):
    def __init__(self, settings):
        self.proxies_url = settings.get('PROXY_LIST_URL')
        self.get_proxies()

    def get_proxies(self):
        fin = urllib2.urlopen(self.proxies_url)

        self.proxies = {}
        for line in fin.readlines():
            parts = re.match('(\w+://)?(\w+:\w+@)?(.+)', line)

            # Cut trailing @
            if parts.group(2):
                user_pass = parts.group(2)[:-1]
            else:
                user_pass = ''

            if parts.group(1):
                key = parts.group(1) + parts.group(3)
            else:
                key = "http://%s" %parts.group(3)

            self.proxies[key] = user_pass

        self.download_time = datetime.now()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        # If the proxy is set and there is no retries then don't override.
        retries = request.meta.get('retry_times', 0)
        if 'proxy' in request.meta:
            if not retries:
                return

        if self.download_time + timedelta(minutes=15) < datetime.now():
            self.get_proxies()

        # Clean previous proxy auth.
        if request.headers.has_key('Proxy-Authorization'):
            del request.headers['Proxy-Authorization']

        proxy_address = random.choice(self.proxies.keys())
        proxy_user_pass = self.proxies[proxy_address]
        if spider.name == "google_products":
            proxy_address = proxy_address.replace("http", "https")
        print proxy_address, proxy_user_pass
        request.meta['proxy'] = proxy_address
        if proxy_user_pass:
            basic_auth = 'Basic ' + base64.encodestring(proxy_user_pass).strip()
            request.headers['Proxy-Authorization'] = basic_auth

    def process_response(self, request, response, spider):
         #print 'Je suis Son ------------------------------->'
         if response.status in RETRY_HTTP_CODES:
             print "Increasing banned requests count by 1"
             increase(BANNED_COUNT_KEY, 1)
         return response

    def process_exception(self, request, exception, spider):
        #increase(BANNED_COUNT_KEY, 1)
        proxy = request.meta.get('proxy', None)
        log.msg('Removing failed proxy <%s>, %d proxies left' % (
                    proxy, len(self.proxies)))
        try:
            del self.proxies[proxy]
        except KeyError:
            pass

class CustomCrawleraMiddleware(CrawleraMiddleware):

    #connection_refused_delay = DELAY_TIME

    def process_response(self, request, response, spider):
        if not self._is_enabled_for_request(request):
            return response
        key = self._get_slot_key(request)
        self._restore_original_delay(request)
        if response.status == self.ban_code:
            self._bans[key] += 1
            if self._bans[key] > self.maxbans:
                self.crawler.engine.close_spider(spider, 'banned')
            else:
                after = response.headers.get('retry-after')
                if after:
                    try:
                        delay = float(after)
                    except ValueError: # After is a datetime value
                        after_time = parser.parse(after, ignoretz=True)
                        delay = (after_time - datetime.now()).seconds

                    self._set_custom_delay(request, delay)
                else:
                    self._set_custom_delay(request, DELAY_TIME)
        else:
            self._bans[key] = 0
        return response

    def process_exception(self, request, exception, spider):
        if not self._is_enabled_for_request(request):
            return
        if isinstance(exception, ConnectionRefusedError):
            # Handle crawlera downtime
            self._set_custom_delay(request, self.connection_refused_delay)