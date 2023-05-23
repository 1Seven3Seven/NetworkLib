import queue
import select
import socket
import threading

from Utils import get_local_ip


class Messages:
    def __init__(self, port: int = 1024, ip: str = None):
        """
        :param port: ...
        :param ip: ...
        """

        self.port: int = port
        """..."""

        self.ip: str = get_local_ip() if ip is None else ip
        """..."""

        # Creating and binding our socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        """..."""
        self._socket.bind((self.ip, self.port))

        # Where we receive and store our messages
        self._receive_messages_thread: threading.Thread = None
        """..."""
        self._received_messages: queue.Queue = queue.Queue()
        """..."""

        # If our thread should stop
        self._stop_event = threading.Event()
        """..."""

    @property
    def thread_stopped(self) -> bool:
        """
        ...
        :return: ...
        """

        return not self._receive_messages_thread.is_alive()
