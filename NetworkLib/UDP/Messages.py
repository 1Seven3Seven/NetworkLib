import queue
import select
import socket
import threading

from NetworkLib.Utils import get_local_ip


class Messages:
    def __init__(self, port: int = 1024, ip: str = None):
        """
        :param port: The port number to bind the socket to.
        :param ip: The IP address to bind the socket to. If not provided, the local IP address is used.
        """

        self.port: int = port
        """The port number to bind the socket to."""

        self.ip: str = get_local_ip() if ip is None else ip
        """The IP address to bind the socket to."""

        # Creating and binding our socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        """The socket object for UDP communication."""
        self._socket.bind((self.ip, self.port))

        # Where we receive and store our messages
        self._receive_messages_thread: threading.Thread = None
        """The thread responsible for receiving and processing incoming messages."""
        self._received_messages: queue.Queue = queue.Queue()
        """A queue to store the received messages."""

        # If our thread should stop
        self._stop_event = threading.Event()
        """An event used to signal the thread to stop processing messages."""

    @property
    def thread_stopped(self) -> bool:
        """
        Returns a flag indicating if the _receive_messages_thread has stopped.

        :return: True if the _receive_messages_thread has stopped, False otherwise.
        """

        return not self._receive_messages_thread.is_alive()
