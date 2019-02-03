# Note from the author:
# This file is not my own, it was borrowed and adapted from Sarakha63 here:
# https://github.com/sarakha63/jeedom_xiaomihome/blob/master/resources/aquara.py
# some adaptations were made.

#from builtins import basestring
import socket
import binascii
import struct
import json


class AquaraConnector:
    """Connector for the Xiaomi Mi Hub and devices on multicast."""

    MULTICAST_PORT = 9898
    SERVER_PORT = 4321

    MULTICAST_ADDRESS = '224.0.0.50'
    SOCKET_BUFSIZE = 1024

    def __init__(self, data_callback=None, auto_discover=True):
        """Initialize the connector."""
        self.data_callback = data_callback
        self.last_tokens = dict()
        self.socket = self._prepare_socket()

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

    def check_incoming(self):
        """Check incoming data."""
        data, addr = self.socket.recvfrom(self.SOCKET_BUFSIZE)
        try:
            payload = json.loads(data.decode("utf-8"))
            #print('Aquara received from ' + addr[0] + ' : ' + data)
            self.handle_incoming_data(payload, addr)

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
                if self.data_callback is not None:
                    self.data_callback(addr[0],
                                       'aquara',
                                       payload)
