import queue
import socket
import threading
from typing import Union, Dict

from NetworkLib.Utils import get_local_ip


class Server:
    def __init__(self, port: int = 1024, ip: str = None, receive_messages_timeout: float = 0.1):
        """
        :param port: The port number to bind the socket to.
        :param ip: The IP address to bind the socket to. If not provided, the local IP address is used.
        :param receive_messages_timeout: The maximum time in seconds to wait for incoming messages.
        """

        self.port: int = port
        """The port number to bind the socket to."""

        self.ip: str = get_local_ip() if ip is None else ip
        """The IP address to bind the socket to."""

        # Creating and binding our socket
        self._socket: socket.socket = socket.socket()
        """The socket object for TCP communication."""
        self._socket.bind((self.ip, self.port))

        # Where we receive and store each incoming client request
        self._receive_client_requests_thread: Union[threading.Thread, None] = None
        """The thread responsible for receiving and processing incoming client connection requests."""
        self._new_client_requests: queue.Queue = queue.Queue()
        """A queue to store the received client requests."""
        self._receive_client_requests_stop_event: threading.Event = threading.Event()
        """An event used to signal the receive client connection thread to stop."""

        # Where we receive and store our client messages
        self._receive_client_messages_thread: Union[threading.Thread, None] = None
        """The thread responsible for receiving and processing each connected client's incoming messages"""
        self._received_client_messages: Dict[str, queue.Queue] = {}
        """A dictionary of ip to queue storing received messages."""
        self._receive_client_messages_stop_event: threading.Event = threading.Event()
        """An event used to signal the receive client messages thread to stop."""

        # How long our thread should wait for messages
        self._receive_messages_timeout = receive_messages_timeout
        """The maximum time in seconds to wait for incoming messages."""

    @property
    def receiving_messages(self) -> bool:
        """
        Returns a bool indicating if the _receive_messages_thread has stopped.

        :return: True if the class instance is receiving messages, False otherwise.
        """

        return self._receive_clients_messages_threads is not None
