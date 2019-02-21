""" Aqara device """
# coding: utf8 
from __future__ import unicode_literals
import json
import logging
log=logging.getLogger(__name__)

#################################################################################################################
class KnownDevices:
    """Handle known devices : gives a context to **sid**
    
        :param known_devices_file: (str) name of file that contains informations about sids

    """
    def __init__(self,known_devices_file = "known_devices.json"):
        self.known_devices_file = known_devices_file
        self.__load_known_devices()

    def __load_known_devices(self):
        """Load known devices from file"""
        try:
            with open(self.known_devices_file) as kdf:
                file_content=kdf.read()
                #import pdb; pdb.set_trace()

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
        """Get context information about a sid or a packet

            :param data: a dict containing parsed aqara packet or a string containing sid

        returns a dict(room = "Room", name = "Name", model = "Model")

        if data is a packet and data["sid"] is not known, room, name will be ""
        and the sid will be appended to the json file

        if data is a string (sid): the device won't be appended
        """
        if isinstance(data,str):
            #sid
            context= self.known_devices.get(data,dict(name="",room="",model="unknown"))
            log.info("context %r for %s is %r"%(context,data,context))
            return context
        else: 
            #log.error("get_context, %r type: %r"%(data, type(data)))
            pass
        try:
            sid = data["sid"]
            device_info = self.known_devices.get(sid)
            if device_info is None:
                log.info("No context for device with sid: %s. Added to %s"%(sid,self.known_devices_file))
                self.known_devices[sid] = dict(room = "", name = "", model = data["model"])
                self.__save_known_devices()
            return self.known_devices[sid]
        except KeyError:
            import pdb; pdb.set_trace()
            log.error("get_infos: Invalid packet %r"%data)
            raise

#################################################################################################################
class CallbackHandler(object):
    """A generic class to handle registering and unregistering to _events_
        
        :param event_list: a list of str that represent events one can subscribe to

    """
    def __init__(self,event_list):
        self.event_list = event_list
        self._callbacks = {}
        for event_type in self.event_list:
            self._callbacks[event_type] = {}

    def register_callback(self, callback, event_type, private_data=None):
        """Register a callback for an event

            :param callback: a callback function with signature ``func(value: dict)``
            :param event_type: (str) the event to regiter to. This must be an event in the ``event_list`` of the constructor
            :param private_data: (obj) any data that will be added to the ``data`` dict argument of the callback function
            :returns: None

            :raises: ValueError : `event_type` is not in the event list
            
            callback methods should be fault tolerant, they will be ``try/except`` ed, if they generate an exception, their subscription will be canceled
        """    
        if not event_type in self.event_list:
            log.error("register_callback: unknwown event type %s"%str(event_type))
            raise ValueError("Unknown event %s not in event list %r"%(event_type,self.event_list))
        else:
            self._callbacks[event_type][callback] = {"private_data":private_data}

    def unregister_callback(self, callback, event_type = "all_events"):
        """Unregister a callback

            :param callback: the callback function 
            :param event_type: the event type to which to unregister (defaults to ``"all_events"``
        """
        if event_type == "all_events":
            for evtype in _self._callbacks.keys():
                try:
                    del(self._callbacks[evtype][callback])
                except:
                    pass
        else:
            try:
                del(self._callbacks[event_type][callback])
            except KeyError:
                raise ValueError("event %r not in event list %r"%(event_type,self.event_list))
            except:
                pass

    def _get_callbacks_for(self,event_type):
        """Returns the list of callbacks for ``event_type``
            
            :param event_type: the event

            :returns: a ``dict(callback_function -> properties_dict)``

            :raises: ValueError (``event_type`` is not a known event)

        """
        try:
            callbacks = self._callbacks[event_type]
            return callbacks
        except KeyError:
            raise ValueError("Unknown event %r not in list %r"%(event_type,self.event_list))

    def _callback_on_event(self,event_type, data, specific_callback = None):
        """Call subscribers back

            :param event_type: the event type (must be in ``self.event_list``)
            :param data: a dict sent to the callback function
                if a ``private_data`` was specified during :meth:`register_callback`, it 
                will be added to the ``data`` dict.
                Additionnaly, the field ``"event_type"`` will be added and set to the ``event_type``
            :param specific_callback: (callback function) if set, only this specific callback 
                function will be called, by default (None), all callback functions that have registered
                to the ``event_type`` will be called with argument ``data``

            :returns: None
            :raises: ValueError (bad event_type), TypeError (``data`` is not of type dict)
        """
        if event_type not in self._callbacks:
            raise ValueError("Bad event_type %r not in event list %r"%(event_type,self.event_list))

        failed_callbacks = []

        all_callbacks = self._callbacks[event_type].keys()
        if specific_callback is not None:
            #replace the list of subscribers to the specific_callback alone
            all_callbacks = [specific_callback]

        for callback in all_callbacks:
            data_ = data.copy()
            data_["event_type"] = event_type

            #add private_data if it exists
            private_data = self._callbacks[event_type][callback].get("private_data")
            if private_data is not None:
                data_["private_data"] = private_data

            #Launch callback, unsubscribe it if it fails
            try:
                callback(data_)
            except:
                log.exception("Removing offending callback because of exception")
                failed_callbacks.append(callback)
        
        # remove all failed callbacks
        for callback in failed_callbacks:
            try:
                del(self.callbacks["data_new"][callback])
            except:
                pass

import time

# #
class Data(CallbackHandler):
    """Generic Data holder class with event generation
        
        :param quantity_name: (str) the name of the measured quantity (such as ``temperature``, ``voltage``)
        :param device: (:class:``AqaraDevice``) the instance of the :class:``AqaraDevice`` that contains this data
        :param memory_depth: (int) size of the data buffer

        :returns: None
        :raises: ValueError (bad memory_depth)

        **Events**:
            - ``data_new``: called on each :meth:`update` with the value provided
                ``{"data_obj":self, "value": new_value, "event_type": "data_new", "measurement":new_measurement, "source_device": self.device}``
            - ``data_change`` : called whenever the new data is different for the previous one
                ``{"data_obj":self, "value": new_value, "event_type": "data_change", "new_measurement":new_measurement, "old_measurement":old_measurement, "source_device": self.device}``
    """
    def __init__(self, quantity_name, device, memory_depth = 10, event_list = ["data_new","data_change"]):
        CallbackHandler.__init__(self,event_list=event_list)
        self.quantity_name = quantity_name
        self.device = device
        self.depth = int(memory_depth)
        if self.depth < 0 :
            raise ValueError("memory depth should be a positive number, %r given"%memory_depth)

        self.measurements = []
        self.update_hook = None #overload to provide a generic update hook
        self.data_change_hook = None



    def update(self,value):
        """update the :class:`Data` with a new value

            :param value: the new value
            :returns: None

            whenever a Data is updated, all clients that registered to the ``data_new`` event will get called back with the new measurement.
            Additionnaly, if the new value is different from the previous one, a ``data_change`` event is launched and all clients to the
            ``data_change`` event will be called.
        """
        timestamp = time.time()
        measurement = {"source_device":self.device, "data_type": self.quantity_name,"update_time": timestamp, "raw_value": value, "value": value}
        #insert measurement
        self.measurements.insert(0,measurement)
        self.measurements = self.measurements[0:self.depth] # pop older values

        if self.update_hook != None:
            self.update_hook(self,measurement)

        #Launch onmeasurement
        self.on_data_new(measurement)

        #Launch onchange
        if (len(self.measurements) >= 2) and ( measurement["raw_value"] != self.measurements[1]["raw_value"]):
            self.on_data_change(measurement,self.measurements[1])

    def get_measurement(self, index=0):
        """Get the last _measurement_

            :param index: (int, optionnal, default 0) access to older measurements with 0 the last one 
            
            a measurement is a ``dict`` with the following fields:
                - ``source_device``: the :class:`AqaraDevice` instance that contain this :class:`Data`
                - ``data_type`` : the **quantity_name** (e.g. ``"temperature"``)
                - ``update_time`` : the ``time.time()`` at which the event was recorded
                - ``raw_value`` : the raw value as transmitted by the device (a str)
                - ``value`` : the ``raw_value``, reinterpreted depending on the ``quantity_name``. In the raw :class:``Data`` type, this is the same as ``raw_value``
        """
        try:
            return self.measurements[index]
        except:
            return None

    def get_value(self,index=0):
        """Get the last value recorded via :meth:`update`
            
            :param index: (int, optionnal, default 0) access to older value with 0 the last one 
        """
        try:
            measurement = self.measurements[index]
            return measurement.get("value",measurement.get("raw_value"))
        except:
            return None


    def on_data_new(self,new_measurement):
        data = {"data_obj":self, "value": new_measurement["value"], "event_type": "data_new", "measurement":new_measurement, "source_device": self.device}
        self._callback_on_event("data_new",data)

    def on_data_change(self, new_measurement, old_measurement):
        if old_measurement is None:
            log.debug("%s first value is %r"%(self.quantity_name,new_measurement["raw_value"]))
            return

        log.debug("[%s] %s changed from %r to %r (%ds)\n"%(self.device.sid,self.quantity_name,new_measurement["raw_value"],old_measurement["raw_value"], int(new_measurement["update_time"] - old_measurement["update_time"])))
        data = {"data_obj":self, "value": new_measurement["value"], "event_type": "data_change", "new_measurement":new_measurement, "old_measurement":old_measurement, "source_device": self.device}
        
        self._callback_on_event("data_change",data)

        if self.data_change_hook is not None:
            self.data_change_hook(self, new_measurement, old_measurement)
# ##
class IPData(Data):
    """IP address (of the gateway) see :class:`Data` for methods and init"""
    def __init__(self, device, memory_depth = 10):
        Data.__init__(self,"ip", device, memory_depth = memory_depth)

# ##
class RGBData(Data):
    """RGB state (of the gateway) see :class:`Data` for methods and init"""
    def __init__(self, device, memory_depth = 10):
        Data.__init__(self,"rgb", device, memory_depth = memory_depth)

    def get_vrgb(self,index=0):
        """get the (v, r, g, b) tupple of the RGBData

            :param index: the index of the data to get with 0 the latest
            :returns: (v,r,g,b) tupple with v intensity value. All numbers
                are in the range [0-255]
        """
        #returns a Value, R, G ,B byte record for measurement at index index (0: last)
        measurement = self.get_measurement(index=index)
        val = int(measurement["raw_value"])
        l = (val >> 24) & 0xff
        r = (val >> 16) & 0xff
        g = (val >> 8) & 0xff
        b = val & 0xff
        return(l,r,g,b)

    def get_measurement(self,index=0):
        """ get the measurement (see :meth:`Data.get_measurement` with additional
            fields v, r, g and b
        """

        measurement = Data.get_measurement(self,index=index)
        if measurement is None:
            return None
        l,r,g,b = self.get_vrgb(index=index)
        measurement["rgb"] = dict(L=l, R=r, G=g, B=b)
        return measurement

# ##
class SwitchStatusData(Data):
    """switch events see :class:`Data` for methods and init
        
        this Data type hold string values in ``["click","double_click","long_click_press","long_click_release"]``
    """
    def __init__(self, device, memory_depth = 10):
        Data.__init__(self,"status", device, memory_depth = memory_depth)
        self.statuses=["click","double_click","long_click_press","long_click_release"]
        def update_hook(self,measurement):
            if measurement["raw_value"] not in self.statuses:
                self.statuses.append(measurement["raw_value"])
                log.warning("adding unknown status '%s'"%(measurement["raw_value"]))
        self.update_hook = update_hook

# ##
class MotionStatusData(Data):
    """Motion events see :class:`Data` for methods and init
        
        the only value is ``"motion"``
        See :class:`NoMotionData` for alternate data of the same Device
    """
    def __init__(self, device, memory_depth = 10):
        Data.__init__(self,"status", device, memory_depth = memory_depth)
        self.statuses=["motion"]
        def update_hook(self,measurement):
            if measurement["raw_value"] not in self.statuses:
                self.statuses.append(measurement["raw_value"])
                log.warning("adding unknown status '%s'"%(measurement["raw_value"]))
        self.update_hook = update_hook

# ##
class MagnetStatusData(Data):
    """Magnet events see :class:`Data` for methods and init
    
        either ``"open"`` or ``"close"``
    """
    def __init__(self, device, memory_depth = 10):
        Data.__init__(self,"status", device, memory_depth = memory_depth)
        self.statuses=["open","close"]
        def update_hook(self,measurement):
            if measurement["raw_value"] not in self.statuses:
                self.statuses.append(measurement["raw_value"])
                log.warning("adding unknown status '%s'"%(measurement["raw_value"]))
        self.update_hook = update_hook

# ##
class CubeStatusData(Data):
    """Cube status data. See :class:`Data` for methods and init
        values are in the set ``["alert","shake_air","flip90","flip180"]``
    """
    def __init__(self, device, memory_depth = 10):
        Data.__init__(self,"status", device, memory_depth = memory_depth)
        self.statuses=["alert","shake_air","flip90","flip180"]
        def update_hook(self,measurement):
            if measurement["raw_value"] not in self.statuses:
                self.statuses.append(measurement["raw_value"])
                log.warning("adding unknown status '%s'"%(measurement["raw_value"]))
        self.update_hook = update_hook

# ##
class NumericData(Data):
    """ A numeric data Holder

        Init parameters are the same as :class:`Data`

        **Events**:
            - Additionnally to ``data_new`` and ``data_change`` events defined in :class:`Data`, this
              class also provides a ``data_change_coarse`` event. Subscribers to this event can use the 
              :meth:`register_callback_with_precision` to subscribe to this event.
    """
    def __init__(self,quantity_name, device, memory_depth = 10):
        Data.__init__(self,quantity_name, device, memory_depth = memory_depth, event_list = ["data_new","data_change","data_change_coarse"])

        def update_hook(self,measurement):
            measurement["value"] = float(measurement["raw_value"])
            log.debug("NumericData update hook %r"%measurement)
        self.update_hook = update_hook

        def significant_change_hook(self,new_measurement, old_measurement):
            current_value = new_measurement["value"]
            callbacks = self._get_callbacks_for("data_change_coarse")
            
            for callback in callbacks:
                properties = callbacks[callback]
                try:
                    old_value = properties["last_value"]
                    if old_value is None:
                        #There wasn't any previous value: launch callback
                        data = {"source_device": self.device, 
                                "data_obj":self, 
                                "precision":cbvalue["precision"],
                                "value":new_measurement["value"], 
                                "new_measurement": new_measurement, 
                                "old_measurement": None}
                        self._callback_on_event("data_change_coarse",data,specific_callback=callback)
                        properties["last_value"] = current_value
                        properties["last_measurement"] = new_measurement
                    else:
                        #There was a previous value : round the old value to the precision and compare it to new value
                        precision = properties["precision"]
                        old_value_rounded = round(old_value / precision) * precision

                        if (current_value > old_value_rounded + precision) or (current_value < old_value_rounded - precision):
                            data = {"source_device": self.device, 
                                    "data_obj":self, 
                                    "precision":precision,
                                    "value":new_measurement["value"], 
                                    "new_measurement": new_measurement, 
                                    "old_measurement": properties["last_measurement"]}
                            #generate event
                            self._callback_on_event("data_change_coarse",data,specific_callback=callback)
                            properties["last_value"] = current_value
                            properties["last_measurement"] = new_measurement

                except Exception as e:
                    log.exception("Malformed callback properties")
                    raise e

    def register_callback_with_precision(self, callback, precision, private_data=None):
        """Register to ``data_change_coarse`` event

            :class:`NumericData` adds a ``data_change_coarse`` event to which
            this function subscribes. Callback functions gets called only when 
            the change from the previous call is greater than ``precision``.
            For example, a Subsriber can register a callback function with precision 0.2
            for 0.2 deg Celsius change in temperature

            :param callback: the callback function of the form `def cbfun(data)`
            :param precision: a positive float or integer
            :param private_data: any data that will be added to the `data` dict arg of the 
                callback function

            :returns: None
            :raises: ValueError: the precision is not a positive number
        """

        log.debug("Registering data_change_coarse with precision %r"%precision)
        try:
            precision = float(precision)
            if precision < 0.0:
                raise 
            if precision <= 0.01:
                #0.01 is the minimum precision
                self.register_callback(callback,"data_change", private_data = private_data)
        except:
            raise ValueError("'precision' field must be a positive value")

        self._callbacks["data_change_coarse"][callback] = { "precision": precision, "last_value": None, "last_measurement": None, "private_data": None}

# ###
class LuxData(NumericData):
    """Illumination data. See :class:`NumericData` for methods and init
        Values holds the amount of lux received by the sensor
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"lux",device,memory_depth = memory_depth)

# ###
class IlluminationData(NumericData):
    """Illumination data (reported by the gateway). See :class:`NumericData` for methods and init
        Values report the amount of illumination (units unclear) received by the sensor
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"illumination",device,memory_depth = memory_depth)

# ###
class CubeRotateData(NumericData):
    """Aqara Cube rotation data. See :class:`NumericData` for methods and init
        the amount of rotation in degrees in a :class:`CubeStatusData` ``rotate`` event
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"rotate",device,memory_depth = memory_depth)
        def update_hook(self,measurement):
            measurement["value"] = float(measurement["raw_value"].replace(",","."))
            log.debug("NumericData update hook %r"%measurement)
        self.update_hook = update_hook


# ###
class NoMotionData(NumericData):
    """Absence of motion data. See :class:`NumericData` for methods and init
        the number of seconds since the last motion was detected (only a few 
        are reported by the sensor (TODO add list)
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"no_motion",device,memory_depth = memory_depth)

# ###
class VoltageData(NumericData):
    """Voltage data. See :class:`NumericData` for methods and init
        raw_value holds the sensor battery voltage (as a str) in mV
        value holds the percentage of battery left as a float
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"voltage",device,memory_depth = memory_depth)
        def update_hook(self,measurement):
            value = int(measurement["raw_value"])
            value = 100.0 * ((value - 2700.0) / (3100.0 - 2700.0))
            measurement["value"] = value
        self.update_hook = update_hook


# ###
class WeatherData(NumericData):
    """Mother class for weather data. See :class:`NumericData` for methods and init
    """
    def __init__(self,quantity_name, device, memory_depth = 10):
        NumericData.__init__(self,quantity_name, device, memory_depth = memory_depth)
        def update_hook(self,measurement):
            measurement["value"] = float(measurement["raw_value"]) / 100.0
            log.debug("Saving value %.2f for capability %s"%(measurement["value"],self.quantity_name))
        self.update_hook = update_hook

class TemperatureUnits:
    CELSIUS = 0
    FARENHEIGHT = 1

# ####
class TemperatureData(WeatherData):
    """Temperature data in celsius. See :class:`NumericData` for methods and init
    """
    def __init__(self,device, memory_depth = 10,unit = TemperatureUnits.CELSIUS):
        WeatherData.__init__(self,"temperature", device, memory_depth = memory_depth)
    def get_celsius(self,index=0):
        """ returns the value as Celsius"""
        try:
            return self.get_value(index=index)
        except:
            return None
    def get_farenheit(self,index=0):
        """ returns the value as Farenheight"""
        try:
            val=self.get_value(index=index)
            return (val * 9.0 / 5.0) + 32.0
        except:
            return None

# ####
class PressureData(WeatherData):
    """Pressure data. See :class:`NumericData` for methods and init
        values are in mBar
    """
    def __init__(self, device, memory_depth = 10):
        WeatherData.__init__(self,"pressure", device, memory_depth = memory_depth)

# ####
class HumidityData(WeatherData):
    """Humiditydata. See :class:`NumericData` for methods and init
        values are in percent
    """
    def __init__(self,device, memory_depth = 10):
        WeatherData.__init__(self,"humidity", device, memory_depth = memory_depth)

#################################################################################################################
import time
class AqaraDevice(object):
    """Generic Aqara Device 

        :param sid: (str) the sid of the device
        :param model: (str) the model of the device
    """
    def __init__(self, sid, model):
        self.short_id = None
        self.sid      = sid
        self.model    = model
        self.context  = {}
        self.last_packet = None


    def update(self,packet):
        """Update the current state of the Device with a new packet

            :param packet: a dict as transmitted by an Aqara Gateway

            the packet should contain the following properties:
                - ``short_id``
                - ``sid``
                - ``model``
                - ``cmd``
                - ``data`` dict of additional data
            
        """
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




class AqaraSensor(AqaraDevice,CallbackHandler):
    """An :class:`AqaraDevice` with sensing capabilities
    
        :param capabilities: list of capabilities for this device
        :param event_list: events generated by this device

        **Events:**
            - ``capability_new``: a new capability was detected for this device
              ``{ "source_device": self, "capability": "temperature, "data_obj":data_object}``

    """
    def __init__(self, sid, model, capabilities = [], event_list = ["capability_new"]):
        AqaraDevice.__init__(self, sid, model)
        CallbackHandler.__init__(self,event_list=event_list)
        self.callbacks = {}
        self.capabilities_list = capabilities #known capabilities for this device
        self.capabilities = {}
        self.event_list = event_list
        for event_type in event_list:
            self.callbacks[event_type]={}
        #self.__create_capabilities(capabilities)
        

    def __create_capabilities(self,capabilities_list):
        """ create data holders based on capabilities names (such as "temperature", "pressure",...)"""

        for capability in capabilities_list:
            data_obj = self.capabilities.get(capability,None)
            if data_obj is not None:
                continue
            # capability doesn't exist yet
            #create
            if capability   == "temperature":
                data_obj = TemperatureData(self)
            elif capability == "pressure":
                data_obj = PressureData(self)
            elif capability == "humidity":
                data_obj = HumidityData(self)
            elif capability == "voltage":
                data_obj = VoltageData(self)
            elif (capability == "status"):
                if (self.model == "switch") or (self.model == "sensor_switch.aq2"):
                    data_obj = SwitchStatusData(self)
                elif (self.model == "sensor_motion.aq2"):
                    data_obj = MotionStatusData(self)
                elif (self.model == "magnet") or (self.model == "sensor_magnet.aq2"):
                    data_obj = MagnetStatusData(self)
                elif self.model == "cube":
                    data_obj = CubeStatusData(self)
                else:
                    log.warning("%s Creating default Data structure for capability [%s]"%(self.model,capability))
                    data_obj = Data(capability,self)
            elif capability == "no_motion":
                    data_obj = NoMotionData(self)
            elif capability == "rotate":
                    data_obj = CubeRotateData(self)
            elif capability == "lux":
                    data_obj = LuxData(self)
            elif capability == "illumination":
                    data_obj = IlluminationData(self)
            elif capability == "ip":
                    data_obj = IPData(self)
            elif capability == "rgb":
                    data_obj = RGBData(self)
            else:
                log.warning("%s Creating default Data structure for capability [%s]"%(self.model,capability))
                data_obj = Data(capability,self)

            self.capabilities[capability] = data_obj
            self._onnewcapability(capability,data_obj)
            
    def _onnewcapability(self,capability,data_object):
        """Internaly launched whenever a new capability was detected"""
        try:
            data = { "source_device": self, "capability": capability, "data_obj":data_object}
            self._callback_on_event("capability_new",data)
        except Exception as e:
            log.warning("_onnewcapability: error %r"%e)
        
    def update(self, packet):
        """ update the device with a new packet
            :param packet: a packet received by an Aqara Gateway
        """
        AqaraDevice.update(self,packet)
        if self.last_cmd == "report" or self.last_cmd == "heartbeat":
            for capability in self.last_data.keys():
                #Get the data object or create it if needed
                try:
                    data_obj = self.capabilities[capability]
                except:
                    log.info("Creating unknown capability [%s] for model %s with sid %s"%(capability,self.model,self.sid))
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
    """Aqara Weather station device, see :class:`AqaraSensor` for init"""
    def __init__(self,sid, model, capabilities = ["temperature","pressure","humidity","voltage"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)

class AqaraMagnet(AqaraSensor):
    """Aqara aperture detection device, see :class:`AqaraSensor` for init"""
    def __init__(self,sid, model, capabilities = ["voltage","status"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)

class AqaraMotion(AqaraSensor):
    """Aqara Motion detection device, see :class:`AqaraSensor` for init"""
    def __init__(self,sid, model, capabilities = ["lux","status","no_motion","voltage"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)

class AqaraSwitch(AqaraSensor):
    """Aqara switch device, see :class:`AqaraSensor` for init"""
    def __init__(self,sid, model, capabilities = ["voltage","status","no_motion"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)

    def __init__(self,sid, model, capabilities = ["status","voltage"]):
        AqaraSensor.__init__(self,sid,model, capabilities = capabilities)

class AqaraCube(AqaraSwitch):
    """Aqara cube device, see :class:`AqaraSensor` for init"""
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
    """Hub for Aqara devices

        :param known_devices_file: (str) name of the file that hold device context. see :class:`KnownDevices`

        To create devices and capabilities, repeatdly call :meth:`AqaraRoot.handle_packet` with aqara gateway packets
    """
    def __init__(self, known_devices_file = "known_devices.json"):
        self.KD = KnownDevices(known_devices_file = known_devices_file)
        self.dev_by_sid = {}
        self.dev_by_room = {}
        self.dev_by_model = {}
        self.dev_by_capability = {}
        self.event_list = ["device_new"]
        self.callbacks = {}
        for event_type in self.event_list:
            self.callbacks[event_type] = {}

    def register_callback(self, callback, event_type):
        """Register a callback to aqara events

            :param callback: your callback function
            :param event_type: the type of event to register to

            available events are: 
                - ``"device_new"``: a new :class:`AqaraDevice` was detected
        """
        if not event_type in self.event_list:
            log.error("AqaraRoot::register_callback: unknwown event type %s"%str(event_type))
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
                capabilities = target_device.capabilities_list
                for capability in capabilities:
                    if self.dev_by_capability.get(capability) is not None:
                        self.dev_by_capability[capability][target_device] = True
                    else:
                        self.dev_by_capability[capability] = {target_device: True}
                self.onnewdevice(target_device)
                
        except KeyError:
            log.exception("__update_device: Malformed packet")

        #target_device contains the device object
        target_device.update(packet)
        #print(str(target_device))
    def onnewdevice(self,device):
        try:
            for callback in self.callbacks["device_new"]:
                data = {"source_object": self, "event_type": "device_new", "device_object": device}
                callback(data)
        except:
            log.exception("AqaraRoot:onnewdevice")
            
    def __create_device(self,packet):
        #TODO use packet["model"] to create the right object
        model = packet["model"]
        sid   = packet["sid"]
        context = self.KD.get_context(sid)
        if (model == "weather.v1") or (model == "weather.v2"):
            device = AqaraWeather(sid,model)
        elif (model == "gateway"):
            device = AqaraGateway(sid,model)
        elif (model == "magnet") or (model == "sensor_magnet.aq2"):
            device = AqaraMagnet(sid,model)
        elif (model == "sensor_motion.aq2"):
            device = AqaraMotion(sid,model)
        elif (model == "switch") or (model == "sensor_switch.aq2"):
            device = AqaraSwitch(sid,model)
        elif (model == "cube"):
            device = AqaraCube(sid,model)
        else:
            log.warning("returning default Sensor for device type %s"%packet["model"])
            device = AqaraSensor(packet["sid"],packet["model"])
        device.context = context
        return device

    def handle_packet(self,data):
        try:
            if isinstance(data,str):
                data = json.loads(data)
            if (data.get("data") is not None) and (isinstance(data["data"],str)):
                parsed_data = json.loads(data["data"])
                data["data"] = parsed_data
        except Exception as e:
            log.error("handle_packet: Error handling packet (%r): %r"%(data,e))
            return False
        data["context"] = self.KD.get_context(data)

        #log.debug("New packet %s"%(json.dumps(data,indent=4)))
        #
        device = self.__update_device(data)
