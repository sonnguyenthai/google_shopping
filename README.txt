Prerequisites
-------------
Linux packages:
  - Python-dev
  - libxml2/libxml2-dev
  - python-lxml

Python packages:
  - pip


Install
-------------

- $ cd google_shopping (root dir)
- $ pip install -r requirements.txt


Settings
--------------
- Settings file: google_shopping/google_shopping/settings.py
- PROXY_LIST_URL: URL of the proxies list
- PRODUCT_PATH: path to directory which should contain xml files
- Other settings don't need to changed

Run
-------------
The scraper takes some arguments:
  - searchterms_str: Brand name as string. Can be a list of brands' names. i.e: "brand1, brand2 ..."
  - searchterms_fn: a file contains brands' names. One name per line. Default = ./brands.csv. Please note that
searchterms_fn is disabled when searchterms_str is enabled.
  - quantity: Limitation number of pages to search. Default = 20

Example of command:
- $ scrapy crawl google_products -a searchterms_str="MICHELIN" -a quantity=1