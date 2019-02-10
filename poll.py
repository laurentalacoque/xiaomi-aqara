import aqara
import json
import logging
logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
#logging.getLogger("aqara_devices").setLevel(logging.WARNING)
import aqara_devices as AD

root = AD.AqaraRoot()
def handle_packet(address,kind,data):
    root.handle_packet(data)

connector = aqara.AquaraConnector(start_server=True,data_callback=handle_packet)

import time
with connector:
    while(True):
        #print("checking data")
        connector.check_incoming()


