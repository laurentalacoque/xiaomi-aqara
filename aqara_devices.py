""" Aqara device """
# -*- coding: utf-8 -*-
import json
import logging
try:
    import basestring
except:
    pass
log=logging.getLogger(__name__)

#################################################################################################################    
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
        if isinstance(data,basestring):
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

#################################################################################################################               
import time

# #
class Data:
    def __init__(self, quantity_name, sid, memory_depth = 10):
        self.quantity_name = quantity_name
        self.sid = sid
        self.depth = int(memory_depth)
        if self.depth <= 2:
            log.warning("Data: must have a memory depth of at least 2, %d given"%memory_depth)
        self.measurements = []
        self.update_hook = None #overload to provide a generic update hook
        self.data_change_hook = None
        
        self.callbacks = dict(data_new = {} , data_change = {})
        
    
    def update(self,value):
        timestamp = time.time()
        measurement = {"sid":self.sid, "type": self.quantity_name,"update_time": timestamp, "raw_value": value, "value": value}
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
            
    def get_measurement(self, index=0):
        try:
            return self.measurements[index]
        except:
            return None
            
    def get_value(self,index=0):
        try:
            measurement = self.measurements[index]
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
        log.debug("[%s] %s changed from %r to %r (%ds)\n"%(self.sid,self.quantity_name,new_measurement["raw_value"],old_measurement["raw_value"], int(new_measurement["update_time"] - old_measurement["update_time"])))
        for callback in self.callbacks["data_change"].keys():
            callback(new_measurement,old_measurement)
        try:
            diff = float(new_measurement["value"]) - float(old_measurement["value"])
            log.debug("[%s] Difference for %s : %.2f"%(self.sid,self.quantity_name,diff))
        except:
            pass
        
        if self.data_change_hook is not None:
            self.data_change_hook(self, new_measurement, old_measurement)
        
# ##            
class NumericData(Data):
    def __init__(self,quantity_name, sid, memory_depth = 10):
        Data.__init__(self,quantity_name, sid, memory_depth = memory_depth)
        self.callbacks["data_change_coarse"] = {}
        
        def update_hook(self,measurement):
            measurement["value"] = float(measurement["raw_value"])
            log.debug("NumericData update hook %r"%measurement)
        self.update_hook = update_hook
        
        def significant_change_hook(self,new_measurement, old_measurement):
            #import pdb; pdb.set_trace()
            current_value = new_measurement["value"]
            for callback in self.callbacks["data_change_coarse"]:
                try:
                    cbvalue = self.callbacks["data_change_coarse"][callback]
                    old_value = cbvalue["last_value"]
                    if old_value is None:
                        #There wasn't any previous value: launch callback
                        callback(new_measurement, None)
                        cbvalue["last_value"] = current_value
                        cbvalue["last_measurement"] = new_measurement
                        continue
                    #There was a previous value : round the old value to the precision and compare it to new value
                    precision = cbvalue["precision"]
                    old_value_rounded = round(old_value / precision) * precision
                    if (current_value > old_value_rounded + precision) or (current_value < old_value_rounded - precision):
                        #generate event
                        callback(new_measurement,cbvalue["last_measurement"])
                    
                except Exception as e:
                    log.debug("NumericData: Significant change hook: %r"%e)
                    pass
        self.data_change_hook = significant_change_hook
        
    def register_callback_on_significant_change(self, callback, precision):
        log.debug("Registering on_change with precision %r"%precision)
        try:
            precision = float(precision)
            if precision < 0.0: 
                raise
            if precision <= 0.01:
                self.register_callback(callback,"data_change")
        except:
            raise ValueError("precision must be a positive number")
        
        self.callbacks["data_change_coarse"][callback] = { "precision": precision, "last_value": None, "last_measurement": None}

# ###
class VoltageData(NumericData):
    def __init__(self,sid,memory_depth = 10):
        NumericData.__init__(self,"voltage",sid,memory_depth = memory_depth)


# ###   
class WeatherData(NumericData):
    def __init__(self,quantity_name, sid, memory_depth = 10):
        NumericData.__init__(self,quantity_name, sid, memory_depth = memory_depth)
        
        def update_hook(self,measurement):
            measurement["value"] = float(measurement["raw_value"]) / 100.0
            log.debug("Saving value %.2f for capability %s"%(measurement["value"],self.quantity_name))
        self.update_hook = update_hook

class TemperatureUnits:
    CELSIUS = 0
    FARENHEIGHT = 1   

# ####
class TemperatureData(WeatherData):
    def __init__(self,sid, memory_depth = 10,unit = TemperatureUnits.CELSIUS):
        WeatherData.__init__(self,"temperature", sid, memory_depth = memory_depth)
        
# ####        
class PressureData(WeatherData):
    def __init__(self, sid, memory_depth = 10):
        WeatherData.__init__(self,"pressure", sid, memory_depth = memory_depth)

# ####
class HumidityData(WeatherData):
    def __init__(self,sid, memory_depth = 10):
        WeatherData.__init__(self,"humidity", sid, memory_depth = memory_depth)  

#################################################################################################################    
import time
class AqaraDevice:
    def __init__(self, sid, model):
        self.short_id = None
        self.sid      = sid
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
    def __init__(self, sid, model, capabilities = []):
        AqaraDevice.__init__(self, sid, model)
        self.capabilities = {}
        self.__create_capabilities(capabilities)
        
    def __create_capabilities(self,capabilities_list):
        """ create data holders based on capabilities names (such as "temperature", "pressure",...)"""
        def onchange(new_measurement,old_measurement):
            return
            log.info("ONCHANGE new %r, old %r"%(new_measurement,old_measurement))
        def onsigchange(new_measurement,old_measurement):
            return
            if old_measurement is not None:
                #import pdb; pdb.set_trace()
                log.critical("SIGNIFICANT CHANGE for %s : %.2f (%ds)\nnew %r\nold %r"%(new_measurement["type"], new_measurement["value"] - old_measurement["value"], int(new_measurement["update_time"]-old_measurement["update_time"]),new_measurement,old_measurement))

        for capability in capabilities_list:
            data_obj = self.capabilities.get(capability,None)
            if data_obj is not None:
                continue
            # capability doesn't exist yet
            #create
            if capability   == "temperature":
                data_obj = TemperatureData(self.sid)
                data_obj.register_callback(onchange,"data_change")
                data_obj.register_callback_on_significant_change(onsigchange,0.5)
            elif capability == "pressure":
                data_obj = PressureData(self.sid)
                data_obj.register_callback(onchange,"data_change")
                data_obj.register_callback_on_significant_change(onsigchange,10)
            elif capability == "humidity":
                data_obj = HumidityData(self.sid)
            elif capability == "voltage":
                data_obj = VoltageData(self.sid)
            else:
                data_obj = Data(capability,self.sid)

            self.capabilities[capability] = data_obj

    def update(self, packet):
        AqaraDevice.update(self,packet)
        if self.last_cmd == "report" or self.last_cmd == "heartbeat":
            for capability in self.last_data.keys():
                #Get the data object or create it if needed
                try:
                    data_obj = self.capabilities[capability]
                except:
                    log.warning("Creating unknown capability [%s] for model %s with sid %s"%(capability,self.model,self.sid))
                    self.__create_capabilities([capability])
                    data_obj = self.capabilities[capability]
                #Update the data value
                data_obj.update(self.last_data[capability])

    def __unicode__(self):
        str_ = AqaraDevice.__unicode__(self)
        for capability in self.capabilities:
            str_ += u"\n\t"
            val = self.capabilities[capability].get_value()
            val = str(val)
            str_ += (u"%s -> %s"%(capability,val))
        return str_

    def get_capabilities(self):
        return(self.capabilities.keys())

class AqaraWeather(AqaraSensor):
    def __init__(self,sid, model, capabilities = ["temperature","pressure","humidity","voltage"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)

class AqaraMagnet(AqaraSensor):
    def __init__(self,sid, model, capabilities = ["voltage","status"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)

class AqaraMotion(AqaraSensor):
    def __init__(self,sid, model, capabilities = ["lux","status","no_motion","voltage"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)    

class AqaraSwitch(AqaraSensor):
    def __init__(self,sid, model, capabilities = ["status","voltage"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)

class AqaraCube(AqaraSwitch):
    def __init__(self,sid, model, capabilities = ["status","voltage","rotate"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)
        
#####################
class AqaraController(AqaraSensor): #Every controller reports events, hence inheritance to Sensor
    def __init__(self,sid,model,capabilities=[]):
        AqaraSensor.__init__(self,sid,model,capabilities=capabilities)

class AqaraGateway(AqaraController):
    def __init__(self,sid, model, capabilities=["ip","illumination","rgb"]):
        AqaraController.__init__(self,sid,"gateway",capabilities=capabilities)

#################################################################################################################    
class AqaraRoot:
    def __init__(self, known_devices_file = "known_devices.json"):
        self.KD = KnownDevices(known_devices_file = known_devices_file)
        self.dev_by_sid = {}
        self.dev_by_room = {}
        self.dev_by_model = {}
        self.dev_by_capability = {}


    def __update_device(self,packet):
        """ packet: a dict containing a parsed aqara packet enriched with a context """
        try:
            sid = packet["sid"]
            target_device = self.dev_by_sid.get(sid)
            if target_device is None:
                log.info("Creating new device with sid %s"%sid)
                #Create the new element
                target_device = self.__create_device(packet)
                #Update lists
                self.dev_by_sid[sid] = target_device
                #by room
                room = packet["context"]["room"]
                if self.dev_by_room.get(room) is not None:
                    self.dev_by_room[room][target_device] = True
                else:
                    #room doesn't exist yet
                    self.dev_by_room[room] = {target_device: True}
                #by model
                model = packet["model"]
                if self.dev_by_model.get(model) is not None:
                    self.dev_by_model[model][target_device] = True
                else:
                    self.dev_by_model[model] = {target_device:True}
                #by capability
                capabilities = target_device.capabilities.keys()
                for capability in capabilities:
                    if self.dev_by_capability.get(capability) is not None:
                        self.dev_by_capability[capability][target_device] = True
                    else:
                        self.dev_by_capability[capability] = {target_device: True}
        except KeyError:
            log.exception("__update_device: Malformed packet")

        #target_device contains the device object
        target_device.update(packet)
        #print(str(target_device))

    def __create_device(self,packet):
        #TODO use packet["model"] to create the right object
        model = packet["model"]
        sid   = packet["sid"]
        
        if (model == "weather.v1") or (model == "weather.v2"):
            return AqaraWeather(sid,model)
        elif (model == "gateway"):
            return AqaraGateway(sid,model)
        elif (model == "magnet") or (model == "sensor_magnet.aq2"):
            return AqaraMagnet(sid,model)
        elif (model == "sensor_motion.aq2"):
            return AqaraMotion(sid,model)
        elif (model == "switch") or (model == "sensor_switch.aq2"):
            return AqaraSwitch(sid,model)
        elif (model == "cube"):
            return AqaraCube(sid,model)
        else:
            log.warning("returning default Sensor for device type %s"%packet["model"])
        return AqaraSensor(packet["sid"],packet["model"])

    def handle_packet(self,data):
        try:
            if isinstance(data,basestring):
                data = json.loads(data)
            if (data.get("data") is not None) and (isinstance(data["data"],basestring)):
                parsed_data = json.loads(data["data"])
                data["data"] = parsed_data
        except Exception as e:
            log.error("handle_packet: Error handling packet (%r): %r"%(data,e))
            return False
        data["context"] = self.KD.get_context(data)

        #log.debug("New packet %s"%(json.dumps(data,indent=4)))
        #
        device = self.__update_device(data)
