import tkinter as tk
import tkinter.ttk as ttk
import aqara_devices as ad
import logging
log = logging.getLogger(__name__)

class TkAqara:
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

        self.tree.tag_configure("n3",background="#F00")
        self.tree.tag_configure("n2",background="green")
        self.tree.tag_configure("n1",background="blue")
        self.recurrent_job_id = self.tk_root.after(500, self._refresh_tags)
        
        #register callback and launch eventloop
        self.ad_root.register_callback(self._on_new_device,"device_new")

    def _refresh_tags(self):
        """refresh tags colors"""
        for i in range(3):
            #n3->n2
            #n2->n1
            #n1->delete
            tagname = "n%d"%(3-i)
            newtagname ="n%d"%(2-i)
            iids = self.tree.tag_has(tagname)
            if tagname == "n1":
                for iid in iids:
                    self.tree.item(iid,tags=())
            else:
                for iid in iids:
                    self.tree.item(iid,tags=newtagname)
            self.tree.update()
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
            self.tree.item(fullname,values=(str(new_measurement["value"])),tags="n3")
            self.tree.see(fullname)
        except:
            log.exception("_on_data_change")
            pass



if __name__ == '__main__':
    
    import threading
    import time
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('aqara_devices').setLevel(logging.WARNING)
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
