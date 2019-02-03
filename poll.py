import aqara
import json

known_devices = {}
try:
    with open("known_devices.json") as kdf:
        file_content=kdf.read()
        known_devices = json.loads(file_content)
except:
    pass
def get_infos(data,known_devices):
    sid = data["sid"]
    status = ""
    try:
        kd = known_devices.get(sid,{})
        room = kd.get("room","?")
        name = kd.get("name","?")
        model = data["model"]
        if model == "switch":
            status = data["data"]["status"]
        elif (model == "weather.v1") or (model == "weather.v2"):
            temperature = data["data"].get("temperature","-")
            pressure = data["data"].get("pressure","-")
            voltage = data["data"].get("voltage","-")
            humidity = data["data"].get("humidity","-")
            status = ("%s %sP %s%% %sV"%(temperature,pressure,humidity,voltage))
        else:
            return None
        return "[%s] [%s] %s"%(room,name,status)
    except:
        return None

def printme(address,devicetype,data):

    # decode data field if it exists
    if data.get("data",False):
        try:
            import json
            decoded_data = json.loads(data["data"])
            data["data"] = decoded_data
        except Exception as e:
            print ("error decoding data: %s"%str(e))
            pass
    #check if device is known
    try:
        sid = data["sid"] # will raise KeyError
        dev_info = known_devices.get(sid)
        if dev_info is None:
            dev_info = {"name": "<unknown>", "room": "<unknown>", "model": data.get("model","<unknown>")}
            known_devices[sid] = dev_info
            with open("known_devices.json","w") as kdf:
                kdf.write(json.dumps(known_devices,indent=4))
        elif dev_info.get("model") != data.get("model"):
                dev_info["model"] = data.get("model")
                known_devices[sid] = dev_info
                with open("known_devices.json","w") as kdf:
                    kdf.write(json.dumps(known_devices,indent=4))

    except KeyError as e:
        print("Error, data doesn't contain a sid")
    except IOError as e:
        print("Impossible to write to file: %s"%str(e))


    #skip heartbeats
    try:
        if data["cmd"] == "heartbeat" and data["model"] == "gateway":
            print("<3")
            return
    except:
            pass
    print("%s\t%s"%(known_devices[sid]["room"],known_devices[sid]["name"]))
    status = get_infos(data,known_devices)
    if status is not None:
        print(status)
    else:
        import json
        print(json.dumps(data,indent=4))

connector = aqara.AquaraConnector(data_callback=printme)

import time
while(True):
    #print("checking data")
    connector.check_incoming()
