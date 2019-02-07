import aqara
import json
import logging
logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("aqara_devices").setLevel(logging.INFO)
import aqara_devices as AD

root = AD.AqaraRoot()
def handle_packet(address,kind,data):
    root.handle_packet(data)

connector = aqara.AquaraConnector(data_callback=handle_packet)

import time
while(True):
    #print("checking data")
    connector.check_incoming()
