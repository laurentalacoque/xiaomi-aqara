# Note from the author:
# This file is not my own, it was borrowed and adapted from Sarakha63 here:
# https://github.com/sarakha63/jeedom_xiaomihome/blob/master/resources/aquara.py
# some adaptations were made see first commit of this file for original version

#from builtins import basestring
import socket
import binascii
import struct
import json
import diffusion_server as DS
import logging
log = logging.getLogger(__name__)
logging.getLogger("diffusion_server").setLevel(logging.DEBUG)



class AquaraConnector:
    """Connector for the Xiaomi Mi Hub and devices on multicast."""

    MULTICAST_PORT = 9898
    SERVER_PORT = 4321

    MULTICAST_ADDRESS = '224.0.0.50'
    SOCKET_BUFSIZE = 1024

    def __init__(self, data_callback=None, start_server=False, auto_discover=True):
        """Initialize the connector."""
        self.data_callback = data_callback
        self.last_tokens = dict()
        self.socket = self._prepare_socket()
        self.server = None
        if start_server:
           self.server = DS.DiffusionServer()

    def _prepare_socket(self):
        sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP

        sock.bind(("0.0.0.0", self.MULTICAST_PORT))

        mreq = struct.pack("=4sl", socket.inet_aton(self.MULTICAST_ADDRESS),
                           socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                        self.SOCKET_BUFSIZE)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        return sock

    def __data_callback(self,message,addr):
        log.debug("received message %r"%message)
        if self.server is not None:
            try:
                log.debug("sending message to clients")
                self.server.is_alive()
                self.server.send_message(message)
            except:
                log.exception("send")
                pass
        if self.data_callback is not None:
            payload = json.loads(message.decode("utf-8"))
            log.debug("Calling callback")
            self.data_callback(addr[0], 'aquara', payload)


    def check_incoming(self):
        """Check incoming data."""
        data, addr = self.socket.recvfrom(self.SOCKET_BUFSIZE)
        try:
            #print('Aquara received from ' + addr[0] + ' : ' + data)
            self.__data_callback(data,addr)

        except Exception as e:
            raise
            print("Can't handle message %r (%r)" % (data, e))

    def handle_incoming_data(self, payload, addr):
        """Handle an incoming payload, save related data if needed,
        and use the callback if there is one.
        """
        if isinstance(payload.get('data', None), basestring):
            cmd = payload["cmd"]
            if cmd in ["heartbeat", "report"]:
                self.__data_callback(payload, addr)
