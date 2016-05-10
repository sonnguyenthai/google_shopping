import urllib2
import socket
import re
from datetime import datetime


import settings

def is_bad_proxy(pip, scheme='http'):
    try:
        proxy_handler = urllib2.ProxyHandler({scheme: pip})
        opener = urllib2.build_opener(proxy_handler)
        opener.addheaders = [('User-agent', settings.USER_AGENT)]
        urllib2.install_opener(opener)
        req=urllib2.Request('https://www.google.fr/shopping/')  # change the URL to test here
        sock=urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        print 'Error code: ', e.code
        return e.code
    except Exception, detail:
        print "ERROR:", detail
        return True
    return False

def main():
    socket.setdefaulttimeout(120)
    proxies = urllib2.urlopen(settings.PROXY_LIST_URL).readlines()
    for proxy in proxies:
        parts = re.match('(\w+://)?(\w+:\w+@)?(.+)', proxy)
        scheme = 'http'
        if parts.group(1):
            scheme = parts.group(1)
        if is_bad_proxy(proxy, scheme):
            print "Bad Proxy %s" % (proxy)
        else:
            print "%s is working" % (proxy)

if __name__ == '__main__':
    #main()
    print datetime.utcnow()