import queue
import socket
import threading
from ipaddress import IPv4Address
from typing import Union, Dict, List, Tuple

import select

from NetworkLib.Utils import get_local_ip


class Server:
    def __init__(self, port: int = 1024, ip: IPv4Address = None, connection_accept_timeout: float = 1,
                 receive_messages_timeout: float = 0.1, prepend_bytes_size: int = 4,
                 client_connection_backlog: int = 5):
        """
        :param port: The port number to bind the socket to.
        :param ip: The IP address to bind the socket to. If not provided, the local IP address is used.
        :param connection_accept_timeout: The maximum time in seconds to wait for incoming client connection requests.
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

        self.connection_accept_timeout: float = connection_accept_timeout
        """The maximum time in seconds to wait for incoming client connection requests."""

        self._receive_messages_timeout: float = receive_messages_timeout
        """The maximum time in seconds to wait for incoming messages."""

        self.prepend_bytes_size: int = prepend_bytes_size
        """The number of bytes the message length is encoded to and prepended as"""

        self.client_connection_backlog: int = client_connection_backlog
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
            # Check if there is a connection to accept
            readable, _, _ = select.select([self._socket], [], [], self.connection_accept_timeout)
            if readable:
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

        # Make sure we are running
        self._receive_client_messages_stop_event.clear()

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

    def stop_listening_for_client_connections(self) -> None:
        """
        Stops listening for incoming client connection requests.

        Blocks until either the current incoming connection request has finished processing or until the timeout has
        been reached.

        `listen_for_client_connections` needs to be run again to start listening again.
        """

        if self._receive_client_requests_thread is not None:
            self._receive_client_requests_stop_event.set()
            self._receive_client_requests_thread.join()

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

    def _setup_listening_thread_for(self, ip: IPv4Address, connection: socket.socket) -> threading.Thread:
        """
        Set up a listening thread for a specific client connection.

        This method creates a new thread responsible for receiving and processing incoming messages from a client.
        The thread will be associated with the specified IPv4 address and the corresponding socket connection.

        The returned thread needs to be started.

        :param ip: The IPv4 address of the client.
        :param connection: The socket connection for the client.
        :return: The created thread for receiving messages from the client.
        """

        self._receive_clients_messages_threads[ip] = threading.Thread(
            target=self._receive_messages_from_client,
            args=(self._receive_client_messages_stop_event, connection, ip),
            name=f"NetworkLib.TCP.Server._receive_messages_from_client for client '{ip}' on port {self.port}"

        )

        return self._receive_clients_messages_threads[ip]

    def listen_for_messages(self) -> None:
        """
        Starts listening for incoming message for each currently accepted client.

        Does not need to be run to send messages.
        
        If the receiving messages threads are not already running, this method starts them.
        If there are running receiving messages threads, then this will check for new clients and begin listening.
        """

        # Make sure we are running
        self._receive_client_messages_stop_event.clear()

        # If we are currently not listening
        if self._receive_clients_messages_threads is None:
            # Set up the dictionary
            self._receive_clients_messages_threads = {}

            # For each currently accepted client, start a thread listening for their messages.
            for ip, connection in self._ipv4_to_connection.items():
                # Threads
                self._setup_listening_thread_for(ip, connection).start()
                # BEGIN
                self._receive_clients_messages_threads[ip].start()

        else:
            # If we are currently listening
            # Start listening for any clients we are not listening for
            for ip, connection in self._ipv4_to_connection.items():
                if ip not in self._receive_clients_messages_threads:
                    # Threads time
                    self._setup_listening_thread_for(ip, connection).start()

    def get_messages_from(self, ip: IPv4Address) -> List[str]:
        """
        Retrieves the messages received from a specific client IP address.

        :param ip: The IPv4 address of the client.
        :return: A list of messages received from the specified client IP address.
        """

        messages = []
        while not self._received_client_messages[ip].empty():
            messages.append(self._received_client_messages[ip].get())
        return messages

    def get_all_messages(self) -> Dict[IPv4Address, List[str]]:
        """
        Retrieves all the messages received from all connected clients.

        :return: A dictionary of client IPv4 addresses to lists of messages received from each client.
        """

        all_messages: Dict[IPv4Address, List[str]] = {}
        for ip in self._received_client_messages:
            all_messages[ip] = self.get_messages_from(ip)
        return all_messages

    def send_message_to(self, ip: IPv4Address, message: str) -> None:
        """
        Sends a message to the specified IP address.

        :param ip: The IP address to send the message to.
        :param message: The message to be sent.
        """

        self._ipv4_to_connection[ip].sendall(message.encode("UTF-8"))

    def send_message_to_all(self, message) -> None:
        """
        Sends a message to all connected clients.

        :param message: The message to be sent.
        """

        for ip in self._ipv4_to_connection:
            self.send_message_to(ip, message)

    def stop_listening_for_messages(self) -> None:
        """
        Stops listening for incoming messages.

        Blocks until all incoming messages have been processed.

        `listen_for_messages` needs to be run again to start listening again.
        """

        # If the threads exist
        if self._receive_clients_messages_threads is not None:
            # HALT IN THE NAME OF THE LAW
            self._receive_client_messages_stop_event.set()
            # Make sure all have finished
            for _, thread in self._receive_clients_messages_threads.items():
                thread.join()
            # Remove the dict as the threads have all stopped
            self._receive_clients_messages_threads = None
