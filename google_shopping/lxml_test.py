from lxml import etree
import os

path = './products'
if path:
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".xml"):
                xml = os.path.join(root, file)
                st = etree.parse(xml)
                url = st.xpath('//root/url')
                if url:
                    url = url[0].text
                    print url

                des = st.xpath('//root/ProductDescription')
                print des[0].text