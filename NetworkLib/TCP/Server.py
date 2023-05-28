import queue
import socket
import threading
from ipaddress import IPv4Address
from typing import Union, Dict

import select

from NetworkLib.Utils import get_local_ip


class Server:
    def __init__(self, port: int = 1024, ip: str = None, receive_messages_timeout: float = 0.1,
                 prepend_bytes_size: int = 4):
        """
        :param port: The port number to bind the socket to.
        :param ip: The IP address to bind the socket to. If not provided, the local IP address is used.
        :param receive_messages_timeout: The maximum time in seconds to wait for incoming messages.
        :param prepend_bytes_size: The number of bytes used to prepend the message length when preparing the message.
        This value determines the maximum message length that can be handled.
        For example, if `prepend_bytes_size` is set to 4, the maximum message length is 2^32 - 1.
        This is not enforced but will cause problems if not taken into consideration
        """

        self.port: int = port
        """The port number to bind the socket to."""

        self.ip: IPv4Address = get_local_ip() if ip is None else ip
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
        self._receive_clients_messages_threads: Union[Dict[IPv4Address, threading.Thread], None] = None
        """
        A dictionary of IPv4 address to thread responsible for receiving and processing client's incoming messages.
        Only exists when listening for messages.
        """
        self._received_client_messages: Dict[IPv4Address, queue.Queue] = {}
        """A dictionary of IPv4 address to queue storing received messages."""
        self._receive_client_messages_stop_event: threading.Event = threading.Event()
        """An event used to signal each thread handling client messages to stop."""

        # How long our thread should wait for messages
        self._receive_messages_timeout = receive_messages_timeout
        """The maximum time in seconds to wait for incoming messages."""

        # The amount of bytes to use when preparing messages
        self.prepend_bytes_size = prepend_bytes_size
        """The number of bytes the message length is encoded to and prepended as"""

    @property
    def receiving_messages(self) -> bool:
        """
        Returns a bool indicating if the class instance is receiving client messages.
        If the `_receive_messages_thread` thread is running.

        :return: True if the class instance is receiving messages, False otherwise.
        """

        return self._receive_clients_messages_threads is not None

    def _receive_messages_from_client(self, stop_event: threading.Event, connection: socket.socket,
                                      ip: IPv4Address) -> None:
        """
        Internal method to receive and process incoming messages from a client.

        This method is intended to be run in a separate thread.

        :param stop_event: An event used to signal the thread to stop processing messages.
        """

        while not stop_event.is_set():
            # Check each client for messages and if any are found then store them
            readable, _, _ = select.select([connection], [], [], self._receive_messages_timeout)
            if len(readable) > 0:  # If there is a message
                # Get the length
                message_length = int.from_bytes(connection.recv(self.prepend_bytes_size), byteorder="big")
                # Read the length
                message_bytes = connection.recv(message_length)
                # Store them
                self._received_client_messages[ip].put(message_bytes.decode("UTF-8"))
