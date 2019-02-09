import socket
import sys
import threading
import Queue
import logging
log = logging.getLogger(__name__)


class DiffusionServer:
    def __init__(self, server_address = ("",10000)):
        self.active_connections = {}
        self.server_thread = None
        self.fatal_event = threading.Event()
        self.exception_queue = Queue.Queue()
        self.connections_lock = threading.Lock()


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

            try:
                sock.close()
            except:
                pass
            log.info("Exit requested: server exiting")

        self.server_thread = threading.Thread(target=server,name="server_thread")
        self.server_thread.start()

    def has_clients(self):
        return len(self.active_connections.keys()) != 0

    def stop(self):
        self.fatal_event.set()

    def is_alive(self):
        return not self.fatal_event.is_set()

    def check_and_raise(self):
        while not self.exception_queue.empty():
            raise(self.exception_queue.get())
        return True

    def send_message(self,message):
        with self.connections_lock:
            connections = self.active_connections.keys()
        for conn in connections:
            try:
                log.debug("Sending [%s] to %r",message,self.active_connections[conn])
                conn.sendall(message)
            except:
                with self.connections_lock:
                    try:
                        connection_infos = self.active_connections[conn]
                        del(self.active_connections[conn])
                        log.info("Removing connection to %r %r"%connection_infos)
                    except:
                        log.exception("removing connection")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger(__name__)
    server = DiffusionServer()
    while server.is_alive():
        try:
            text = raw_input(">")
            server.check_and_raise()
        except:
            log.exception("Main exiting")
            server.stop()
            sys.exit(1)
        server.send_message(text)
