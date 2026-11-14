import socket

SERVER_HOST = "localhost"
SERVER_PORT = 6000            # rcssserver player port
BUFFER_SIZE = 65535           # largest possible UDP datagram
MESSAGE_TERMINATOR = '\0'     # rcssserver null-terminates its messages


class UDPClient:

    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.server_addr = (host, port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

    def send(self, msg: str):
        self.sock.sendto(msg.encode(), self.server_addr)

    def recv(self):
        """Return the next server message, or None if nothing is waiting."""
        try:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
        except (BlockingIOError, InterruptedError):
            return None
        # The server answers each player from a dedicated port
        self.server_addr = addr
        return data.decode(errors='replace').rstrip(MESSAGE_TERMINATOR).strip()
