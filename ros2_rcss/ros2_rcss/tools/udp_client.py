import socket


class UDPClient:

    def __init__(self, host="localhost", port=6000):
        self.server_addr = (host, port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.01)

    def send(self, msg: str):
        self.sock.sendto(msg.encode(), self.server_addr)

    def recv(self):
        try:
            data, addr = self.sock.recvfrom(8192)
            self.server_addr = addr 
            return data.decode()
        except socket.timeout:
            return None