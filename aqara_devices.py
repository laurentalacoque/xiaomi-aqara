""" Aqara device """
# -*- coding: utf-8 -*-
import json
import logging
log=logging.getLogger(__name__)
class KnownDevices:
    def __init__(self,known_devices_file = "known_devices.json"):
        self.known_devices_file = known_devices_file
        self.__load_known_devices()

    def __load_known_devices(self):
        """Load known devices from file"""
        try:
            with open(self.known_devices_file) as kdf:
                file_content=kdf.read()
                self.known_devices = json.loads(file_content)
                log.info("Loaded %d elements from %s"%(len(self.known_devices),self.known_devices_file))
                return True
        except Exception as e:
            self.known_devices = {}
            log.error("Could not read known_devices from %s : %r"%(self.known_devices_file,e))
            return False
            
    def __save_known_devices(self):
        """Save known devices to file"""
        try:
            with open(self.known_devices_file,"w") as kdf:
                kdf.write(json.dumps(self.known_devices,indent=4))
                log.debug("Written %d elements to %s"%(len(self.known_devices),self.known_devices_file))
                return True
        except Exception as e:
            log.error("__save_known_devices: Error: %r", e)
            return False
        
    def get_context(self,data):
        """
        data: a dict containing parsed aqara packet or a string containing sid
        
        returns a dict(room = "Room", name = "Name", model = "Model")
        
        if data is a packet and data["sid"] is not known, room, name will be "" 
        and the sid will be appended to the json file
        
        if data is a string (sid): the device won't be appended
        """
        if isinstance(data,str):
            #sid
            return self.known_devices.get(data,dict(name="",room="",model="unknown"))
        #else: must be a packet
        try:
            sid = data["sid"]
            device_info = self.known_devices.get(sid)
            if device_info is None:
                log.info("No context for device with sid: %s. Added to %s"%(sid,self.known_devices_file))
                self.known_devices[sid] = dict(room = "", name = "", model = data["model"])
                self.__save_known_devices()
            return self.known_devices[sid]
        except KeyError:
            log.error("get_infos: Invalid packet %r"%data)
            raise

            
import time            
class Data:
    def __init__(self, quantity_name, memory_depth = 10):
        self.quantity_name = quantity_name
        self.depth = int(memory_depth)
        if self.depth <= 2:
            log.warning("Data: must have a memory depth of at least 2, %d given"%memory_depth)
        self.measurements = []
        self.update_hook = None #overload to provide a generic update hook
        
        self.callbacks = dict(data_new = {} , data_change = {})
        
    
    def update(self,value):
        timestamp = time.time()
        measurement = {"update_time": timestamp, "raw_value": value}
        #insert measurement
        self.measurements.insert(0,measurement)
        self.measurements = self.measurements[0:self.depth] # pop older values
        
        if self.update_hook != None:
            self.update_hook(self,measurement)
        
        #Launch onmeasurement
        self.on_data_new(measurement)
            
        #Launch onchange
        if (len(self.measurements) >= 2) and ( measurement != self.measurements[1]):
            self.on_data_change(measurement,self.measurements[1])
            
    def get_last_measurement(self):
        try:
            return self.measurements[0]
        except:
            return None
            
    def get_last_value(self):
        try:
            measurement = self.measurements[0]
            return measurement.get("value",measurement.get("raw_value"))
        except:
            return None
    
    def register_callback(self, callback, event_type):
        if not event_type in ["data_new","data_change"]:
            log.debug("Data::register_callback: unknwown event type %s"%str(event_type))
            return False
        else:
            self.callbacks[event_type][callback] = True
            return True
    
    def unregister_callback(self, callback, event_type = "all_events"):
        if event_type == "all_events":
            for evtype in self.callbacks.keys():
                try:
                    del(self.callbacks[evtype][callback])
                except:
                    pass
        else:
            try:
                del(self.callbacks[event_type][callback])
            except:
                pass
    
    def on_data_new(self,new_measurement):
        for callback in self.callbacks["data_new"].keys():
            callback(new_measurement)
        
    def on_data_change(self, new_measurement, old_measurement):
            if old_measurement is None:
                log.debug("%s first value is %r"%(self.quantity_name,new_measurement["raw_value"]))
                return
            log.debug("%s changed from %r to %r (%ds)\n"%(self.quantity_name,new_measurement["raw_value"],old_measurement["raw_value"], int(new_measurement["update_time"] - old_measurement["update_time"])))
            for callback in self.callbacks["data_change"].keys():
                callback(new_measurement,old_measurement)
        
            
class NumericData(Data):
    def __init__(self,quantity_name,memory_depth = 10):
        Data.__init__(self,quantity_name,memory_depth = memory_depth)
    
        def update_hook(self,measurement):
            measurement["value"] = float(measurement["raw_value"])
            log.debug("NumericData update hook %r"%measurement)
        self.update_hook = update_hook


class WeatherData(NumericData):
    def __init__(self,quantity_name,memory_depth = 10):
        Data.__init__(self,quantity_name,memory_depth = memory_depth)
        
        def update_hook(self,measurement):
            measurement["value"] = float(measurement["raw_value"]) / 100.0
            log.debug("Saving value %.2f for capability %s"%(measurement["value"],self.quantity_name))
        self.update_hook = update_hook

class TemperatureUnits:
    CELSIUS = 0
    FARENHEIGHT = 1   
    
class TemperatureData(WeatherData):
    def __init__(self,memory_depth = 10, unit = TemperatureUnits.CELSIUS):
        WeatherData.__init__(self,"temperature",memory_depth = memory_depth)
        
class PressureData(WeatherData):
    def __init__(self,memory_depth = 10):
        WeatherData.__init__(self,"pressure",memory_depth = memory_depth)

class HumidityData(WeatherData):
    def __init__(self,memory_depth = 10):
        WeatherData.__init__(self,"pressure",memory_depth = memory_depth)  

        

import time
class AqaraDevice:
    def __init__(self, model = "unknown"):
        self.short_id = None
        self.sid      = None
        self.model    = model
        self.context  = {}
        self.last_packet = None
        
    def update(self,packet):
        """ update the current state of the object """
        try:
            self.short_id = packet["short_id"]
            self.sid      = packet["sid"]
            self.model    = packet["model"]
            self.context  = packet.get("context",{})
            self.last_packet = packet
            self.last_update = time.time()
            self.last_cmd    = packet["cmd"]
            self.last_data   = packet["data"]
        except KeyError as e:
            log.error("AqaraDevice.update: missing mandatory key:%s"%str(e))
            log.exception("AqaraDevice.update(%s)"%json.dumps(packet))

    def __unicode__(self):
        return (u"[%s] (%s/%s)"%(self.model,self.context["room"],self.context["name"]))
    
    def __str__(self):
        return unicode(self).encode("utf-8")

        
        

class AqaraSensor(AqaraDevice):
    def __init__(self, model= "unknown", capabilities = []):
        AqaraDevice.__init__(self,model=model)
        self.capabilities = {}
    
    def update(self, packet):
        AqaraDevice.update(self,packet)
        if self.last_cmd == "report" or self.last_cmd == "heartbeat":
            for capability in self.last_data.keys():
                try:
                    data_obj = self.capabilities.get(capability,None)
                    if data_obj is None:
                        #Doesn't exist yet
                        #create
                        if capability   == "temperature":
                            data_obj = TemperatureData()
                        elif capability == "pressure":
                            data_obj = PressureData()
                        elif capability == "humidity":
                            data_obj = HumidityData()
                        else:
                            data_obj = Data(capability)

                        self.capabilities[capability] = data_obj
                    data_obj.update(self.last_data[capability])
                    
                except KeyError:
                    log.warning("Unknown capability %s"%capability)
                    
    def __unicode__(self):
        str_ = AqaraDevice.__unicode__(self)
        for capability in self.capabilities:
            str_ += u"\n\t"
            val = self.capabilities[capability].get_last_value()
            val = str(val)
            str_ += (u"%s -> %s"%(capability,val))
        return str_
        
    def get_capabilities(self):
        return(self.capabilities.keys())

        
        
        
        
        
class AqaraWeather(AqaraSensor):
    def __init__(self,model = "weather", capabilities = ["temperature","pressure","humidity","voltage"]):
        AqaraSensor.__init__(self,model = model, capabilities = capabilities)

        
        
        
        
        
        
class AqaraRoot:
    def __init__(self, known_devices_file = "known_devices.json"):
        self.KD = KnownDevices(known_devices_file = known_devices_file)
        self.dev_by_sid = {}

    def __update_device(self,packet):
        """ packet: a dict containing a parsed aqara packet enriched with a context """
        try:
            target_device = self.dev_by_sid.get(packet["sid"])
            if target_device is None:
                log.info("Creating new device with sid %s"%packet["sid"])
                #Create the new element
                target_device = self.__create_device(packet)
                self.dev_by_sid[packet["sid"]] = target_device
        except KeyError:
            log.exception("__update_device: Malformed packet")
        
        #target_device contains the device object
        target_device.update(packet)
        print(str(target_device))
    
    def __create_device(self,packet):
        #TODO use packet["model"] to create the right object
        if packet["model"] == "weather.v1":
            return AqaraWeather(model="weather.v1")
        return AqaraSensor(model = packet["model"])
        
    def handle_packet(self,data):
        try:
            data = json.loads(data)
            if data.get("data") is not None:
                parsed_data = json.loads(data["data"])
                data["data"] = parsed_data
        except Exception as e:
            log.error("handle_packet: Error handling packet (%r): %r"%(data,e))
            return False
        data["context"] = self.KD.get_context(data)
        
        #log.debug("New packet %s"%(json.dumps(data,indent=4)))
        # 
        device = self.__update_device(data)