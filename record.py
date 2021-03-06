# -*- coding: utf8 -*-
import aqara
import aqara_devices as AD
import json
record_file = "event_recording.log"
import logging
log=logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("aqara_devices").setLevel(logging.INFO)

import time
def logit(address,devicetype,data):
    print(data)
    data["_ts_"] = time.time()
    with open ( record_file,"a") as logfile:
        logfile.write(json.dumps(data) + "\n")

def record():
    print("Attaching to Aqara Connector")
    connector = aqara.AquaraConnector(data_callback=logit)
    print("Starting listening loop")
    with connector:
        while(True):
            try:
                connector.check_incoming()
            except KeyboardInterrupt:
                connector.stop()
                sys.exit(0)
            except:
                log.error("Exception, retrying")

def on_new_temp(data):
    log.info("new_temp [%s/%s]: %.2f"%(data["source_device"].context.get("room",""), data["source_device"].context.get("room",""), data["value"]))

def on_temperature_change(data):
    try:
        log.info("temp_change [%s/%s] : %r (was %r)"%(data["source_device"].context.get("room",""), data["source_device"].context.get("room",""), data["value"],data["old_measurement"]["value"]))
    except:
        log.exception("temperature_change")
        pass

def on_new_capability(data):
    device = data["source_device"]
    capability = data["capability"]
    data_obj   = data["data_obj"]
    log.info("New capability '%s' device [%s/%s] (%s) id:%s"%(capability,device.context.get("room",""),device.context.get("name",""),device.model, device.sid))
    if capability == 'temperature':
        data_obj.register_callback_with_precision(on_temperature_change,0.1)
        data_obj.register_callback(on_new_temp,"data_new")

def on_new_device(data):
    try:
        device = data["device_object"]
        
        log.info("New device [%s/%s] (%s) id:%s"%(device.context.get("room",""),device.context.get("name",""),device.model, device.sid))
        device.register_callback(on_new_capability,"capability_new")
        #print data
    except:
        log.exception("on_new_device")

def replay(speed=5):

    root = AD.AqaraRoot()
    root.register_callback(on_new_device,"device_new")

    with open(record_file,"r") as logfile:
        lines = logfile.readlines()

    last_time = 0.
    for i,line in enumerate(lines):
        data = json.loads(line)

        #if speed is not none, replay with timestamps
        ts = data.get("_ts_")
        if (ts is not None):
            if (speed is not None):
                ts=float(ts)
                if last_time == 0. :
                    last_time = ts
                log.debug("sleeping %d s at speed %d"%(int(ts-last_time),speed))
                time.sleep((ts - last_time)/speed)
            last_time = ts

        root.handle_packet(line)

    return
    for model in root.dev_by_model.keys():
        print("%s: %d devices"%(model,len(root.dev_by_model[model])))
        for i,device in enumerate(root.dev_by_model[model]):
            print("\t%s %d [%s][%s] %s"%(model,i,device.context.get("room"),device.context.get("name"),device.sid))
            for capability in device.get_capabilities():
                print("\t\t%s"%capability)
                for i in range(40):
                    value = device.capabilities[capability].get_value(index=i)
                    if capability == "rgb":
                        try:
                            l,r,g,b = device.capabilities[capability].get_vrgb(index=i)
                            value = "L%d RGB(%d,%d,%d)"%(l,r,g,b)
                        except:
                            pass
                    if value is None:
                        break
                    print("\t\t\t%r"%value)
        print("")

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
