# -*- coding: utf8 -*-
import aqara
import aqara_devices as AD
import json
record_file = "event_recording.log"

def log(address,devicetype,data):
    print(data)
    with open ( record_file,"a") as logfile:
        logfile.write(json.dumps(data) + "\n")

def record():
    print("Attaching to Aqara Connector")
    connector = aqara.AquaraConnector(data_callback=log)
    print("Starting listening loop")
    while(True):
        connector.check_incoming()
        
def replay():
    import logging
    logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("aqara_devices").setLevel(logging.WARNING)
    root = AD.AqaraRoot()
    with open(record_file,"r") as logfile:
        lines = logfile.readlines()
    for i,line in enumerate(lines):
        root.handle_packet(line)

    for model in root.dev_by_model.keys():
        print("%s: %d devices"%(model,len(root.dev_by_model[model])))
        
        print("\t" + " ".join(root.dev_by_model[model].keys()[0].get_capabilities()))
            
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Aqara event logger")
    parser.add_argument("-r", "--record",
                    help="(default) Record aqara packets data into %s"%record_file,
                    action="store_true")
    parser.add_argument("-p", "--replay",
                    help="Replays aqara packets stored in %s"%record_file,
                    action="store_true")
    
    args = parser.parse_args()
    
    if (args.replay and args.record):
        print("Error, choose only one option")
        import sys
        sys.exit(1)
    if (args.replay):
        replay()
    else:
        record()