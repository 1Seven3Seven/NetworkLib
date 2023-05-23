import queue
import select
import socket
import threading


class Messages:
    def __init__(self, port: int = 1024, ip: str = None):
        """
        :param port: ...
        :param ip: ...
        """

        self.port: int = port
        """..."""

        self.ip: str = socket.gethostbyname(socket.gethostname())
        """..."""

