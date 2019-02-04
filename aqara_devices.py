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
        for capability in capabilities:
            self.capabilities[capability] = { "value": None, "callbacks": {}, "timestamp": 0.0}
        
    def register_callback(self,callback,capability, tolerance = 1.0):
        cap = self.capabilities[capability] #will throw keyerror if it's not right
        cap["callbacks"][callback] = tolerance
    
    def update(self, packet):
        AqaraDevice.update(self,packet)
        if self.last_cmd == "report":
            for capability in self.last_data.keys():
                try:
                    self.capabilities[capability]["value"] = self.last_data[capability]
                    self.capabilities[capability]["timestamp"] = self.last_update
                except KeyError:
                    log.warning("Unknown capability %s"%capability)
                    
    def __unicode__(self):
        str_ = AqaraDevice.__unicode__(self)
        for capability in self.capabilities:
            str_ += u"\n\t"
            val = self.capabilities[capability]["value"]
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
        return AqaraDevice()
        
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