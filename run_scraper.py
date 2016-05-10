import os
import signal
import subprocess
import shlex
import time
from datetime import datetime

import pickledb
from google_shopping import settings

COMMAND = "scrapy crawl google_products -a quantity=%s" %settings.NUMBER_OF_PAGE
COMMAND = shlex.split(COMMAND)


if __name__ == "__main__":
    #path = os.path.dirname(__file__)
    #devnull = open('/dev/null', 'w')
    print "----------- START AT %s---------------" %datetime.utcnow()
    p = subprocess.Popen(COMMAND, shell=False)

    # Get the process id
    while True:
        start_time = datetime.utcnow()
        print '---------START CHECKING ----------------'
        DB = pickledb.load(settings.PICKLEDB_NAME, True)
        banned_count = DB.get(settings.BANNED_COUNT_KEY)
        if not banned_count:
            banned_count = 0
        print '--------------- BANNED REQUESTS COUNT NUMBER: %s--------------' %banned_count
        if not banned_count:
            banned_count = 0
        if banned_count > settings.ALLOWED_BANNED_REQUESTS_NUMBER:
            pid = p.pid
            os.kill(pid, signal.SIGINT)
            print "----------- STOPPED AT %s. RUNNING ABOUT %s minutes ---------------" %(datetime.utcnow(), (datetime.utcnow() - start_time).seconds/60)
            if not p.poll():
                print "Process %s correctly halted" %pid
            DB.set(settings.BANNED_COUNT_KEY, 0)
            time.sleep(12*60)

            print "----------- RESTART AT %s ---------------" %datetime.utcnow()
            p = subprocess.Popen(COMMAND, shell=False)
        print '---------------- END CHECKING ------------'
        time.sleep(10)
        
        if DB.get('google_products') == 'Done':
            DB.set('google_products', 'terminated')
            print "Scraper is done"
            break

