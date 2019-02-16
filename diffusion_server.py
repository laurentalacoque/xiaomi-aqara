import socket
import sys
import threading
try:
    import Queue
except ImportError:
    import queue as Queue

import logging
log = logging.getLogger(__name__)

DEFAULT_PORT = 10001
class DiffusionClient:
    def __init__(self, callback, server_address, server_port = DEFAULT_PORT):
        self.server_address = server_address
        self.server_port = server_port
        self.callback = callback
        self.fatal_event = threading.Event()
        self.exception_queue = Queue.Queue()

        def client():
            import select
            timeout = 0.2
            log.debug("Starting client thread")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setblocking(1)
                conninfo = (self.server_address, self.server_port)
                log.info("Connecting to %s:%d"%conninfo)
                sock.connect(conninfo)
                incoming = [sock]
                while not self.fatal_event.is_set():
                    #wait timeout for the socket to be readable
                    readable, writable, exceptional = select.select(incoming,[],[],timeout)
                    if sock in readable:
                        message = sock.recv(1024)
                        if len(message) == 0:
                            continue
                        log.debug("Received %d bytes"%(len(message)))
                        try:
                            self.callback(message,"client_socket")
                        except Exception as e:
                            log.error("Error while receiving: %s"%str(e))
                            log.exception("receiving")
                            #self.exception_queue.put(e)


                log.info("Exiting client on request")

            except Exception as e:
                self.exception_queue.put(e)
                log.error("Exiting connection because of %s"%str(e))
                self.fatal_event.set()
            try:
                sock.close()
            except:
                pass
        self.client_thread = threading.Thread(target=client,name="client_thread")
        self.client_thread.start()

    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        self.fatal_event.set()

    def stop(self):
        self.fatal_event.set()
        self.check_and_raise()

    def is_alive(self):
        self.check_and_raise()
        return not self.fatal_event.is_set()

    def check_and_raise(self):
        while not self.exception_queue.empty():
            raise(self.exception_queue.get())
        return True

class DiffusionServer:
    def __init__(self, server_address = ("",DEFAULT_PORT)):
        self.active_connections = {}
        self.server_thread = None
        self.fatal_event = threading.Event()
        self.exception_queue = Queue.Queue()
        self.connections_lock = threading.Lock()
        self.server_started = threading.Event()


        def server():
            import select
            timeout = 0.2
            log.debug("Starting server thread with timeout %.2f"%timeout)

            try:
                # Create a TCP/IP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setblocking(0)
                # Bind the socket to the address given on the command line
                sock.bind(server_address)
                log.info('starting server on %s port %s' % sock.getsockname())
                sock.listen(1)
                self.server_started.set()
                incoming = [ sock ]
                while not self.fatal_event.is_set():
                    readable, writable, exceptional = select.select(incoming,[],[],timeout)
                    if sock in readable:
                        connection, client_address = sock.accept()
                        log.info("New connection %r %r"%(connection,client_address))
                        with self.connections_lock:
                            self.active_connections[connection]=client_address
            except Exception as e:
                self.fatal_event.set()
                log.error("Exception: server exiting")
                self.exception_queue.put(e)
                self.server_started.clear()

            try:
                self.server_started.clear()
                sock.close()
            except:
                pass
            log.info("Exit requested: server exiting")

        self.server_thread = threading.Thread(target=server,name="server_thread")
        self.server_thread.start()

    def __enter__(self):
        return self
    def __exit__(self, exception_type, exception_value, traceback):
        self.fatal_event.set()

    def has_clients(self):
        self.check_and_raise()
        return len(self.active_connections.keys()) != 0

    def stop(self):
        self.fatal_event.set()
        self.check_and_raise()

    def is_started(self):
        return self.server_started.is_set() and (not self.fatal_event.is_set())

    def is_alive(self):
        self.check_and_raise()
        return not self.fatal_event.is_set()

    def check_and_raise(self):
        while not self.exception_queue.empty():
            raise(self.exception_queue.get())
        return True

    def send_message(self,message):
        self.check_and_raise()
        with self.connections_lock:
            connections = self.active_connections.keys()
        for conn in connections:
            try:
                log.debug("Sending [%s] to %r",message,self.active_connections[conn])
                conn.sendall(message)
            except:
                log.exception("sending...")
                with self.connections_lock:
                    try:
                        connection_infos = self.active_connections[conn]
                        del(self.active_connections[conn])
                        log.info("Removing connection to %r %r"%connection_infos)
                        conn.close()
                    except:
                        log.exception("removing connection")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger(__name__)
    server = DiffusionServer()
    for i in range(10):
        try:
            if not server.is_started():
                import time
                time.sleep(0.1)
        except:
            server.stop()

    def print_me(message):
        log.info("Message received:[%s]"%message)
    client = DiffusionClient(print_me,"localhost")

    while server.is_alive():
        try:
            text = raw_input(">")
            server.check_and_raise()
            client.check_and_raise()
        except:
            log.exception("Main exiting")
            server.stop()
            client.stop()
            sys.exit(1)
        server.send_message(text)
