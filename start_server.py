import aqara
import logging
log=logging.getLogger(__name__)

import argparse

parser = argparse.ArgumentParser(description='Aqara tcp hub server')
parser.add_argument("--log", help='destination log file')

args = parser.parse_args()
if args.log is not None:
    try:
        logging.basicConfig(level=logging.INFO, filename = args.log)
    except:
        logging.basicConfig(level=logging.INFO, filename = "/tmp/aqaraserver.log")
else:
    logging.basicConfig(level=logging.INFO)

for i in range(10):
    try:
        log.info("Starting server (retry %d)"%i)
        connector = aqara.AquaraConnector(start_server=True)
        break;
    except:
        log.exception("failed starting server")
    import time
    time.sleep(10) #wait 10 seconds

#Server hopefull started
try:
    with connector:
        while(True):
            connector.check_incoming()
except:
    log.exception()


