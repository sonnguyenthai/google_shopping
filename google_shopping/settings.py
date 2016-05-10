# -*- coding: utf-8 -*-

# Scrapy settings for google_shopping project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#
import os


BOT_NAME = 'google_shopping'

SPIDER_MODULES = ['google_shopping.spiders']
NEWSPIDER_MODULE = 'google_shopping.spiders'

# Delay between requests not to be blocked (seconds).
DOWNLOAD_DELAY = 2

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:35.0) Gecko/20100101 Firefox/35.0'

ITEM_PIPELINES = {
    'google_shopping.pipelines.GoogleShoppingPipeline': 200,
}

# Retry many times since proxies often fail
RETRY_TIMES = 10
# Retry on most error codes since proxies fail for different reasons
RETRY_HTTP_CODES = [500, 503, 504, 400, 403, 404, 408]

# Disable CrawleraMiddleware and enable 3 lines bellow it to switch on using proxies list
DOWNLOADER_MIDDLEWARES = {
    #'google_shopping.custom_middlewares.CustomCrawleraMiddleware': 600
    #'scrapy.contrib.downloadermiddleware.retry.RetryMiddleware': 100,
    #'google_shopping.custom_middlewares.RandomProxy': 90,
    'scrapy.contrib.downloadermiddleware.httpproxy.HttpProxyMiddleware': 110,
}

PROXY_LIST_URL = 'https://d3s763n0ugqswt.cloudfront.net/proxy.txt'
#PROXY_LIST_URL = 'http://localhost/proxies.txt'

# Path to directory which should contain all xml files
PRODUCT_PATH = os.path.join(os.path.dirname(__file__), "products")

# Clawlera configuration
CRAWLERA_URL = 'http://paygo.crawlera.com:8010'
CRAWLERA_ENABLED = True
CRAWLERA_USER = 'rcouraud'
CRAWLERA_PASS = 'FEf3zwVsNz'
# CONCURRENT_REQUESTS = 32
# CONCURRENT_REQUESTS_PER_DOMAIN = 32
AUTOTHROTTLE_ENABLED = False
DOWNLOAD_TIMEOUT = 600

# Delay time for response code 503
DELAY_TIME = 12*60

#
CONCURRENT_REQUESTS_PER_IP = 8

# Directory where stores information for restarting the scraper.
JOBDIR = os.path.join(os.path.dirname(__file__), "google_products")

# PickleDB settings
PICKLEDB_NAME = os.path.join(os.path.dirname(__file__), "PickleDB.db")
BANNED_COUNT_KEY = "banned_count"

# Number of banned requests before stopping the scraper.
ALLOWED_BANNED_REQUESTS_NUMBER = 20

# Number of pages for scraping
NUMBER_OF_PAGE = 2
#
# LOG_ENABLED = True
# LOG_FILE = os.path.join(os.path.dirname(__file__), "scraper.log")
# LOG_LEVEL = 'WARNING'
