# -*- coding: utf-8 -*-
import tkinter as tk
import tkinter.ttk as ttk
import aqara_devices as ad
import logging
log = logging.getLogger(__name__)

from tkinter import LabelFrame
class TkGateway(LabelFrame):
    """Control for a gateway

        :param aqara_gateway_instance: the AqaraGateway instance
        :param tk_root: root widget for this control

    """

    def __init__(self, aqara_gateway_instance, tk_root=None):
        LabelFrame.__init__(self,text="Gateway",padx=5, pady=5)

        self.aqara_gateway_instance = aqara_gateway_instance
        if tk_root is None:
            self.tk_root = tk.Tk()
        else:
            self.tk_root = tk_root

        #color choose callback function
        from tkinter import colorchooser
        def getColor():
            color = colorchooser.askcolor() 
            print(color)
        
        
        ttk.Button(self.tk_root,text='Color', command=getColor).pack(side=tk.LEFT)
        
        control_variable = tk.StringVar(self.tk_root)
        sound_options={
            u"None":10000,
            u"Sirene 1":0,
            u"Sirene 2":1,         
            u"Accident":2,      
            u"Compte a rebours":3,
            u"Fantome":4,
            u"Sniper":5,
            u"Guerre":6,
            u"Frappe aérienne":7,
            u"Aboiements":8,
            u"Sonnette":10,
            u"Frappe":11,
            u"Hilarious":12,
            u"Sonnerie":13,
            u"MiMix":20,
            u"Enthousiastic":21,
            u"GuitarClassic":22,
            u"IceWorldPiano":23,
            u"LeisureTime":24,
            u"Childhood":25,
            u"MorningStreamlet":26,
            u"MusicBox":27,
            u"Orange":28,
            u"Thinker ":29,
        }
        
        def play():
            key = control_variable.get()
            val = sound_options[key]
            print ("playing sound %d (%s)"%(val,key))
        
        sound_list = sorted(sound_options.keys(), key=lambda kv: sound_options[kv])
        
        optionmenu_widget = ttk.OptionMenu(self.tk_root, control_variable, *sound_list).pack(side=tk.LEFT)
        ttk.Button(self.tk_root,text='play', command=play).pack(side=tk.LEFT)


class TkAqara(object):
    """A Tk representation of AqaraRoot
    
        :param known_devices: (str) the known_devices file
        :param tk_root: (obj) the Tk root. If ``None``, a
            new TkRoot will be created
    """
    def __init__(self, known_devices = "known_devices.json", tk_root=None):
        self.ad_root = ad.AqaraRoot()

        if tk_root is None:
            self.tk_root = tk.Tk()
        else:
            self.tk_root = tk_root

        #Create the treeview
        self.tree = ttk.Treeview(self.tk_root, columns = ('value'))
        self.tree.heading("value", text="State")
        self.tree.pack(fill=tk.BOTH, expand=1)

        #Create classes
        self.tree.tag_configure("room",background="black",foreground="white")
        self.tree.tag_configure("device",background="#333",foreground="white")

        self.tree.tag_configure("n3",background="#FF9933")
        self.tree.tag_configure("n2",background="#FFCC99")
        self.tree.tag_configure("n1",background="#FCF2E7")
        self.recurrent_job_id = self.tk_root.after(500, self._refresh_tags)
        
        #register callback and launch eventloop
        self.ad_root.register_callback(self._on_new_device,"device_new")

    def _refresh_tags(self):
        """refresh tags colors"""
        n3iids = self.tree.tag_has('n3')
        n2iids = self.tree.tag_has('n2')
        n1iids = self.tree.tag_has('n1')

        for iid in n3iids:
            self.tree.item(iid,tags='n2')
        for iid in n2iids:
            self.tree.item(iid,tags='n1')
        for iid in n1iids:
            self.tree.item(iid,tags='')
        #call me again
        self.recurrent_job_id = self.tk_root.after(5000, self._refresh_tags)
        
    def start(self):
        """starts tk eventloop"""
        self.tk_root.mainloop()

    def update(self,data):
        """update internal AqaraRoot state
            :param data: an Aqara data packet
        """
        self.ad_root.handle_packet(data)

    def _on_new_device(self,data):
        """Called on device creation"""
        log.info("new device %r"%data)
        try:
            device = data["device_object"]
            sid = device.sid
            model = device.model
            context = device.context
            room = context["room"]
            name = context["name"]
            roomid = "room.%s"%room

            #Add the room if it doesn't exist
            if not self.tree.exists(roomid):
                self.tree.insert("",0,text=room, tags="room",iid=roomid)

            #Add the device
            self.tree.insert(roomid,0,text=name, tags="device", values=(model),iid=sid)
            self.tree.see(sid)

            #register for new capabilities
            device.register_callback(self._on_new_capability,"capability_new")

        except:
            log.exception("_on_new_device")
            pass
            
            
    def _on_new_capability(self,data):
        """Called whenever a new capability is detected"""
        log.info("new capability %r"%data)
        try:
            device = data["source_device"]
            name   = data["capability"]
            data_obj = data["data_obj"]
            sid = device.sid
            fullname = "%s.%s"%(sid,name)

            #Add the capability
            self.tree.insert(sid,0,text=name,tags="capability",iid=fullname)
            self.tree.see(fullname)
            data_obj.register_callback(self._on_data_change,"data_change")
        except:
            log.exception("_on_new_capability")
            pass

    def _on_data_change(self,data):
        """Called whenever a sensor value has changed"""
        log.info("new value %r"%data)
        try:
            device = data["source_device"]
            new_measurement = data["new_measurement"]
            name = new_measurement["data_type"]
            sid = device.sid
            fullname = "%s.%s"%(sid,name)
            value = "%s\\ %s"%(str(new_measurement["value"]),new_measurement.get("data_units",""))
            self.tree.item(fullname,values=(value),tags="n3")
            self.tree.see(fullname)
        except:
            log.exception("_on_data_change")
            pass



if __name__ == '__main__':
    
    import threading
    import time
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('aqara_devices').setLevel(logging.WARNING)

    import sys
    root=tk.Tk()
    frame = tk.Frame(root)
    tkgateway = TkGateway(None,tk_root=frame).pack(fill=tk.X,side=tk.TOP)
    tkgateway2 = TkGateway(None,tk_root=frame).pack(fill=tk.X,side=tk.BOTTOM)
    frame.pack()
    root.mainloop()
    sys.exit(1)
    tkroot = TkAqara()

    def replay():
        import json
        speed=None
        record_file = "event_recording.log"

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

            time.sleep(0.5)
            tkroot.update(line)
    replaythread = threading.Thread(target=replay,name="read")
    replaythread.start()
    tkroot.start()
