import queue
import socket
import threading
from ipaddress import IPv4Address
from typing import Union, Dict, List, Tuple

import select

from NetworkLib.Utils import get_local_ip


class Server:
    def __init__(self, port: int = 1024, ip: str = None, receive_messages_timeout: float = 0.1,
                 prepend_bytes_size: int = 4, client_connection_backlog: int = 5):
        """
        :param port: The port number to bind the socket to.
        :param ip: The IP address to bind the socket to. If not provided, the local IP address is used.
        :param receive_messages_timeout: The maximum time in seconds to wait for incoming messages.
        :param prepend_bytes_size: The number of bytes used to prepend the message length when preparing the message.
        This value determines the maximum message length that can be handled.
        For example, if `prepend_bytes_size` is set to 4, the maximum message length is 2^32 - 1.
        This is not enforced but will cause problems if not taken into consideration
        :param client_connection_backlog: The maximum number of pending connections to the server socket.
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
        self._new_client_requests: queue.Queue[Tuple[socket.socket, IPv4Address]] = queue.Queue()
        """A queue to store the received client requests."""
        self._receive_client_requests_stop_event: threading.Event = threading.Event()
        """An event used to signal the receive client connection thread to stop."""

        # Where we receive and store our client messages
        self._receive_clients_messages_threads: Union[Dict[IPv4Address, threading.Thread], None] = None
        """
        A dictionary of IPv4 address to thread responsible for receiving and processing client's incoming messages.
        Only exists when listening for messages.
        """
        self._ipv4_to_connection: Dict[IPv4Address, socket.socket] = {}
        """A dictionary of IPv4 address to connection for that address."""
        self._received_client_messages: Dict[IPv4Address, queue.Queue[str]] = {}
        """A dictionary of IPv4 address to queue storing received messages."""
        self._receive_client_messages_stop_event: threading.Event = threading.Event()
        """An event used to signal each thread handling client messages to stop."""

        self._receive_messages_timeout = receive_messages_timeout
        """The maximum time in seconds to wait for incoming messages."""

        self.prepend_bytes_size = prepend_bytes_size
        """The number of bytes the message length is encoded to and prepended as"""

        self.client_connection_backlog = client_connection_backlog
        """The maximum number of pending connections to the server socket."""

    @property
    def receiving_client_connections(self) -> bool:
        """
        Returns a bool indicating if the class instance is receiving any client requests.
        If the `_receive_client_requests_thread` thread is running.

        :return: True if the class instance is receiving new client requests, False otherwise.
        """

        return self._receive_client_requests_thread is not None

    def _accept_new_client_connections(self, stop_event: threading.Event) -> None:
        """
        Internal method to accept new client connections and store them for further processing.

        This method is intended to be run in a separate thread.

        :param stop_event: An event used to signal the thread to stop accepting new client connections.
        """

        # Listen for new client connections with a backlog of 5
        self._socket.listen(self.client_connection_backlog)

        while not stop_event.is_set():
            # Get the connection
            connection_address = self._socket.accept()
            # Save them
            self._new_client_requests.put(connection_address)

    def listen_for_client_connections(self) -> None:
        """
        Starts listening for incoming client connection requests.

        Does not need to be run to send messages.

        If the receiving client requests thread is not already running, this method starts it in a separate thread.
        If the receiving client requests thread is running, this method does nothing.
        """

        if self._receive_client_requests_thread is None:
            self._receive_client_requests_thread = threading.Thread(
                target=self._accept_new_client_connections,
                args=(self._receive_client_requests_stop_event,),
                name=f"NetworkLib.TCP.Server._accept_new_client_connections on port {self.port}"
            )
            self._receive_client_requests_thread.start()

    def get_new_client_connections(self) -> List[IPv4Address]:
        """
        Retrieves a list of new client connections that have been received since the last call.

        :return: A list of IPv4 addresses representing the new client connections.
        """

        new_connections: List[IPv4Address] = []

        while not self._new_client_requests.empty():
            # Get the info for the new connection
            connection, address = self._new_client_requests.get()
            # Info to return
            new_connections.append(address)
            # Saving the ip to the connection
            self._ipv4_to_connection[address] = connection

        return new_connections

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

    def listen_for_messages(self) -> None:
        """

        """

        # For each currently accepted client, start a thread listening for their messages.
        ...
