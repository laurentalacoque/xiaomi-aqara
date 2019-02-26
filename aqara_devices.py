# -*- coding: utf-8 -*- 
""" Aqara device """
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
                #import pdb;pdb.set_trace()

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
            #import pdb ;  pdb.set_trace()
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

            :raises: :exc:`ValueError`: `event_type` is not in the event list
            
            callback methods should be fault tolerant, they will be ``try/except`` ed, if they generate an exception, their subscription will be canceled
        """    
        log.debug("registering callback for event '%s'"%event_type)
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

            :raises: :exc:`ValueError` (``event_type`` is not a known event)

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
            :raises: :exc:`ValueError` (bad event_type), :exc:`TypeError` (``data`` is not of type dict)
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
        :param event_list: ([str,...]) list of events generated by this Data
        :param units: (str) the units name of this Data values

        :returns: None
        :raises: :exc:`ValueError` (bad memory_depth)

        **Events**:
            - ``data_new``: called on each :meth:`update` with the value provided
                ``{"data_obj":self, "value": new_value, "event_type": "data_new", "measurement":new_measurement, "source_device": self.device}``
            - ``data_change`` : called whenever the new data is different for the previous one
                ``{"data_obj":self, "value": new_value, "event_type": "data_change", "new_measurement":new_measurement, "old_measurement":old_measurement, "source_device": self.device}``
    """
    def __init__(self, quantity_name, device, memory_depth = 10, event_list = ["data_new","data_change"], units=""):
        CallbackHandler.__init__(self,event_list=event_list)
        self.quantity_name = quantity_name
        self.device = device
        self.depth = int(memory_depth)
        self.units = units
        if self.depth < 0 :
            raise ValueError("memory depth should be a positive number, %r given"%memory_depth)

        self.measurements = []



    def update(self,value):
        """update the :class:`Data` with a new value

            :param value: the new value
            :returns: None

            whenever a Data is updated, all clients that registered to the ``data_new`` event will get called back with the new measurement.
            Additionnaly, if the new value is different from the previous one, a ``data_change`` event is launched and all clients to the
            ``data_change`` event will be called.
        """
        timestamp = time.time()
        measurement = {"source_device":self.device, "data_type": self.quantity_name, "data_units": self.units, "update_time": timestamp, "raw_value": value, "value": value}
        #insert measurement
        self.measurements.insert(0,measurement)
        self.measurements = self.measurements[0:self.depth] # pop older values

        #call the update hook
        self._update_hook(measurement)

        #Launch on_data_new
        self.on_data_new(measurement)

        #Launch onchange if values differ ...
        if (len(self.measurements) >= 2) and ( measurement["raw_value"] != self.measurements[1]["raw_value"]):
            self.on_data_change(measurement,self.measurements[1])
        # ... or if it's the first measurement (it is a change)
        elif len(self.measurements) == 1: 
            self.on_data_change(measurement,None)

    def _update_hook(self,measurement):
        """Update hook
        
            this is called after Data has created a measurement and before events are launched
            overide to change the measurement in children classes
        """
        pass

    def _data_change_hook(self,new_measurement,old_measurement):
        """Data change hook
        
            this is called after Data has created a measurement and before events are launched
            overide to change the measurement in children classes
        """
        pass



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
        """Called whenever a new measurement was received

            This calls back every subscriber to ``data_new`` event
        """
        data = {"data_obj":self, "value": new_measurement["value"], "event_type": "data_new", "measurement":new_measurement, "source_device": self.device}
        self._callback_on_event("data_new",data)

    def on_data_change(self, new_measurement, old_measurement):
        """Called on data change
        
            Called whenever a new measurement was received and the measurement is
            different from the previous one

        """

        if old_measurement is None:
            log.debug("%s first value is %r"%(self.quantity_name,new_measurement["raw_value"]))
        else:
            log.debug("[%s] %s changed from %r to %r (%ds)\n"%(self.device.sid,self.quantity_name,new_measurement["raw_value"],old_measurement["raw_value"], int(new_measurement["update_time"] - old_measurement["update_time"])))


        #call the _data_change_hook before calling back functions
        self._data_change_hook(new_measurement, old_measurement)

        data = {"data_obj":self, "value": new_measurement["value"], "event_type": "data_change", "new_measurement":new_measurement, "old_measurement":old_measurement, "source_device": self.device}
        self._callback_on_event("data_change",data)

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

class StatusData(Data):
    """:class:`Data` with status type, see parentfor methods and init

        :param statuses: a list of statuses strings
        
        this Data type can have a values in a set of strings
        such as ``["click","double_click","long_click_press","long_click_release"]``
    """
    def __init__(self, device, memory_depth = 10, statuses = []):
        Data.__init__(self,"status", device, memory_depth = memory_depth)
        self.statuses=statuses

    def _update_hook(self,measurement):
        if measurement["raw_value"] not in self.statuses:
            self.statuses.append(measurement["raw_value"])
            log.warning("unknown status '%s'"%(measurement["raw_value"]))

# ##
class SwitchStatusData(StatusData):
    """switch events see :class:`Data` for methods and init
        
        this Data type hold string values in ``["click","double_click","long_click_press","long_click_release"]``
    """
    def __init__(self, device, memory_depth = 10):
        StatusData.__init__(self, device, 
                memory_depth = memory_depth,
                statuses=["click","double_click","long_click_press","long_click_release"])

# ##
class MotionStatusData(StatusData):
    """Motion events see :class:`Data` for methods and init
        
        the only value is ``"motion"``
        See :class:`NoMotionData` for alternate data of the same Device
    """
    def __init__(self, device, memory_depth = 10):
        StatusData.__init__(self, device, memory_depth = memory_depth, statuses=["motion"])

# ##
class MagnetStatusData(StatusData):
    """Magnet events see :class:`Data` for methods and init
    
        either ``"open"`` or ``"close"``
    """
    def __init__(self, device, memory_depth = 10):
        StatusData.__init__(self, device, memory_depth = memory_depth, statuses=["open","close"])

# ##
class CubeStatusData(StatusData):
    """Cube status data. See :class:`Data` for methods and init
        values are in the set ``["alert","shake_air","flip90","flip180"]``
    """
    def __init__(self, device, memory_depth = 10):
        StatusData.__init__(self, device, memory_depth = memory_depth,
                statuses=["alert","shake_air","flip90","flip180"])

# ##
class NumericData(Data):
    """ A numeric data Holder

        Init parameters are the same as :class:`Data`

        **Events**:
            - Additionnally to ``data_new`` and ``data_change`` events defined in :class:`Data`, this
              class also provides a ``data_change_coarse`` event. Subscribers to this event can use the 
              :meth:`register_callback_with_precision` to subscribe to this event.
    """
    def __init__(self,quantity_name, device, units= "", memory_depth = 10):
        Data.__init__(self,quantity_name, device, units=units, memory_depth = memory_depth, event_list = ["data_new","data_change","data_change_coarse"])

    def _update_hook(self,measurement):
        """overide update hook to change values to float"""
        measurement["value"] = float(measurement["raw_value"])
        log.debug("NumericData update hook %r"%measurement)

    def _data_change_hook(self,new_measurement, old_measurement):
        """called on every data changes, callback whenever a change greater than precision occured"""
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
            :raises: :exc:`ValueError`: the precision is not a positive number
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
        NumericData.__init__(self,"lux",device,units="lux",memory_depth = memory_depth)

# ###
class IlluminationData(NumericData):
    """Illumination data (reported by the gateway). See :class:`NumericData` for methods and init
        Values report the amount of illumination (units unclear) received by the sensor
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"illumination",device,units="ill",memory_depth = memory_depth)

# ###
class CubeRotateData(NumericData):
    """Aqara Cube rotation data. See :class:`NumericData` for methods and init
        the amount of rotation in degrees in a :class:`CubeStatusData` ``rotate`` event
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"rotate",device,units="deg",memory_depth = memory_depth)
    def _update_hook(self,measurement):
        measurement["value"] = float(measurement["raw_value"].replace(",","."))
        log.debug("NumericData update hook %r"%measurement)


# ###
class NoMotionData(NumericData):
    """Absence of motion data. See :class:`NumericData` for methods and init
        the number of seconds since the last motion was detected (only a few 
        are reported by the sensor (TODO add list)
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"no_motion",device, units="s", memory_depth = memory_depth)

# ###
class VoltageData(NumericData):
    """Voltage data. See :class:`NumericData` for methods and init
        raw_value holds the sensor battery voltage (as a str) in mV
        value holds the percentage of battery left as a float
    """
    def __init__(self,device,memory_depth = 10):
        NumericData.__init__(self,"voltage",device,units="%",memory_depth = memory_depth)
    def _update_hook(self,measurement):
        value = int(measurement["raw_value"])
        value = 100.0 * ((value - 2700.0) / (3100.0 - 2700.0))
        measurement["value"] = value


# ###
class WeatherData(NumericData):
    """Mother class for weather data. See :class:`NumericData` for methods and init
    """
    def __init__(self,quantity_name, device, units="", memory_depth = 10):
        NumericData.__init__(self,quantity_name, device, units, memory_depth = memory_depth)
    def _update_hook(self,measurement):
        measurement["value"] = float(measurement["raw_value"]) / 100.0
        log.debug("Saving value %.2f for capability %s"%(measurement["value"],self.quantity_name))


# ####
class TemperatureData(WeatherData):
    """Temperature data in celsius. See :class:`NumericData` for methods and init
    """
    def __init__(self,device, memory_depth = 10,units = "C"):
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
        WeatherData.__init__(self,"pressure", device, units="mPa", memory_depth = memory_depth)

# ####
class HumidityData(WeatherData):
    """Humiditydata. See :class:`NumericData` for methods and init
        values are in percent
    """
    def __init__(self,device, memory_depth = 10):
        WeatherData.__init__(self,"humidity", device, units="%", memory_depth = memory_depth)

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
    """AqaraDevice with controller capabilities"""
    def __init__(self,sid,model,capabilities=[]):
        AqaraSensor.__init__(self,sid,model,capabilities=capabilities)

class AqaraGateway(AqaraController):
    """Gateway device

        see :class:`AqaraSensor` for init arguments and registerable events

        You can interact with the device using the methods below.
        Before any interaction, you MUST use the :meth:`set_command_handler` to set the gateway password and pass a callback method responsible for actually sending the packet data

    """
    def __init__(self,sid, model, capabilities=["ip","illumination","rgb"]):
        AqaraController.__init__(self,sid,"gateway",capabilities=capabilities)
        self.token = None
        self.volume = 50
        self.password = None
        def raise_me(*args):
            raise ConnectionRefusedError("No callback was defined to send command")
        self.send_command_callback = raise_me
        self.last_ip = None

    def set_command_handler(self,aqara_password, send_command_callback):
        """Sets the gateway password and command handler callback
            
            :param password: a 16 character string found in the Xiaomi Home app
            :param callback: a callback function of the form 
                ``def cb_send(data: str, ip: str, port: int)``. This function is
                responsible for sending the command to the aqara gateway.
            
            :raises: :exc:`ValueError`: the ``aqara_password`` is not a
                16 characters string or the ``send_command_callback`` is not a function
        """
        try:
            aqara_password = str(aqara_password)
            assert len(aqara_password) == 16
        except:
            raise ValueError("aqara_password should be a 16 chars string")
        
        if not callable(send_command_callback):
            raise ValueError("send_command_callback is not callable") 

        self.password = aqara_password
        self.send_command_callback = send_command_callback

    def update(self,packet):
        """Update the current state of the Device with a new packet

            :param packet: a dict as transmitted by an Aqara Gateway

            the packet should contain the following properties:
                - ``short_id``
                - ``sid``
                - ``model``
                - ``cmd``
                - ``data`` dict of additional data
                - ``token`` the crypto token for commands
            
        """
        AqaraSensor.update(self,packet)
        try:
            self.last_token = packet["token"]
        except KeyError as e:
            log.error("AqaraGateway.update: missing mandatory key:%s"%str(e))
        try:
            self.last_ip = packet["data"]["ip"]
        except:
            pass

    def set_color(self,v,r,g,b):
        """sets the color of the gateway

            :param v: intensity value [0-255]
            :param r: red value [0-255]
            :param g: green value [0-255]
            :param b: blue value [0-255]

            :raises:
                - :exc:`ConnectionAbortedError`: the gateway ``token`` was not
                  yet received from the Gateway.
                - :exc:`ConnectionRefusedError`: the password was not set. Use
                  :meth:`set_command_handler` to set the Gateway password or 
                  pass it as an argument to the constructor
        """
        try:
            for val in [v,r,g,b]:
                val = int(val)
                assert val >= 0
                assert val <= 255
        except:
            raise ValueError("v,r,g,b arguments must be integer between 0 and 255")

        RGB = "%02x%02x%02x%02x"%(v,r,g,b)
        command = {'rgb': int(VRGB,16)}
        self._send_command(command)
        pass

    def set_volume(self,volume):
        """sets the volume of the gateway

            :raises:
                - :exc:`ConnectionAbortedError`: the gateway ``token`` was not
                  yet received from the Gateway.
                - :exc:`ConnectionRefusedError`: the password was not set. Use
                  :meth:`set_command_handler` to set the Gateway password or 
                  pass it as an argument to the constructor
        """
        command={'vol':int(volume)}
        self.volume = int(volume)
        pass

    def play_track(self,track_number,volume=None):
        """play a gateway prerecorded track

            The list of internal tracks is as follows:
                - 0: Sirène 1
                - 1: Sirène 2
                - 2: Accident
                - 3: Compte à rebours
                - 4: Fantôme
                - 5: Sniper
                - 6: Guerre
                - 7: Frappe aérienne
                - 8: Aboiements
                - 10: Sonnette
                - 11: Frappe
                - 12: Hilarious
                - 13: Sonnerie|
                - 20: MiMix
                - 21: Enthousiastic
                - 22: GuitarClassic
                - 23: IceWorldPiano
                - 24: LeisureTime
                - 25: Childhood
                - 26: MorningStreamlet
                - 27: MusicBox
                - 28: Orange
                - 29: Thinker 

            Use :meth:`stop_track` to stop
            
            :param track_number: the track to play
            :param volume: (opt,[0-100]) the volume
                if the volume is not used, last volume
                set with :meth:`set_volume` will be used
                defaults to 50

            :raises:
                - :exc:`ConnectionAbortedError`: the gateway ``token`` was not
                  yet received from the Gateway.
                - :exc:`ConnectionRefusedError`: the password was not set. Use
                  :meth:`set_command_handler` to set the Gateway password or 
                  pass it as an argument to the constructor
        """
        if volume is None:
            volume=self.volume
        command={'mid':int(track_number), 'vol': volume}
        self._send_command(command)

    def stop_track(self):
        """stops the currently-playing track initiated by :meth:`play_track`

            :raises:
                - :exc:`ConnectionAbortedError`: the gateway ``token`` was not
                  yet received from the Gateway.
                - :exc:`ConnectionRefusedError`: the password was not set. Use
                  :meth:`set_command_handler` to set the Gateway password or 
                  pass it as an argument to the constructor
        """
        volume=self.volume
        command={'mid': 10000, 'vol': volume}
        self._send_command(command)

    def _send_command(self,command):
        """send a command to the gateway
            
            This method computes a secret key based on the gateway
            password and the last token received and send the command
            to the gateway

            :param command: a ``dict`` containing the data for the 
                Xiaomi Aqara ``write`` cmd

            :raises:
                - :exc:`ConnectionAbortedError`: the gateway ``token`` was not
                  yet received from the Gateway.
                - :exc:`ConnectionRefusedError`: the password was not set. Use
                  :meth:`set_command_handler` to set the Gateway password or 
                  pass it as an argument to the constructor

            some code and constants borrowed from 
            https://github.com/Msmith78/jeedom_xiaomihome/
        """

        if self.token is None:
            log.error("Unable to send command: no token received from gateway")
            raise ConnectionAbortedError("Token was not yet received by Gateway, Aborting")
        
        if password is None:
            log.error("Unable to send command: password is not set")
            raise  ConnectionRefusedError("password was not set yet for Gateway, Aborting")

        from Crypto.Cipher import AES
        IV_AQUARA = bytearray([0x17, 0x99, 0x6d, 0x09, 
                               0x3d, 0x28, 0xdd, 0xb3, 
                               0xba, 0x69, 0x5a, 0x2e,
                               0x6f, 0x58, 0x56, 0x2e])

        aes = AES.new(password, AES.MODE_CBC, str(IV_AQUARA))
        #encrypt last token to determine write_key
        ciphertext = aes.encrypt(self.token)
        write_key = binascii.hexlify(ciphertext)
        command['key'] = write_key
        write_command = {
            "cmd": u"write",
            "model": self.model,
            "sid":self.sid,
            "short_id":self.short_id,
            "data":command }
        import json
        write_command = json.dumps(write_command)
        log.debug("Sending commmand to gateway %s %r"%(self.sid,write_command))

        try:
            self.send_command_callback(self.last_ip,9898,write_command)
        except:
            log.error("Unable to send command to aqara %s:%d")
            log.exception("Exception:")

#################################################################################################################
class AqaraRoot(CallbackHandler):
    """Hub for Aqara devices

        :param known_devices_file: (str) name of the file that hold device context. see :class:`KnownDevices`

        **Events**
        This class supports the registering of events of type ``device_new``. Subscribers will be called back with
        a single ``dict`` argument : 
        ``{"source_object": <this AqaraRoot instance>, "device_object": <new AqaraDevice instance>}``

        To create devices and capabilities, repeatdly call :meth:`AqaraRoot.handle_packet` with aqara gateway packets
    """
    def __init__(self, known_devices_file = "known_devices.json"):
        CallbackHandler.__init__(self,event_list=["device_new"])
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
                capabilities = target_device.capabilities_list
                for capability in capabilities:
                    if self.dev_by_capability.get(capability) is not None:
                        self.dev_by_capability[capability][target_device] = True
                    else:
                        self.dev_by_capability[capability] = {target_device: True}
                self._on_new_device(target_device)
                
        except KeyError:
            log.exception("__update_device: Malformed packet")

        #target_device contains the device object
        target_device.update(packet)
        #print(str(target_device))

    def _on_new_device(self,device):
        """Callback every subscriber of the event "device_new" """
        #callback every subscribers
        data = {"source_object": self, "device_object": device}
        self._callback_on_event("device_new",data)
            
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
        """Handle a new packet from the Aqara gateway

            :param data: the packet content. This can be either a json string or a decoded dict

            :raises: :exc:`ValueError`: ``data`` parameter is invalid
        
        """
        try:
            if isinstance(data,str):
                data = json.loads(data)
            if (data.get("data") is not None) and (isinstance(data["data"],str)):
                parsed_data = json.loads(data["data"])
                data["data"] = parsed_data
        except Exception as e:
            log.error("handle_packet: Error handling packet (%r): %r"%(data,e))
            raise ValueError("Invalid data parameter for AqaraRoot.handle_packet")

        data["context"] = self.KD.get_context(data)

        device = self.__update_device(data)
