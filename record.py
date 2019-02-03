import aqara
import json

def log(address,devicetype,data):
    print(data)
    with open ("event_recording.log","a") as logfile:
        logfile.write(json.dumps(data) + "\n")

connector = aqara.AquaraConnector(data_callback=log)

while(True):
    connector.check_incoming()
