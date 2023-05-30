import queue
import socket
import threading
from typing import Union

import select


class Client:
    def __init__(self, port: int = 1024, receive_messages_timeout: float = 0.1, prepend_bytes_size: int = 4):
        """
        :param port: The port number to connect to the server on.
        :param receive_messages_timeout: The maximum time in seconds to wait for incoming messages.
        :param prepend_bytes_size: The number of bytes used to prepend the message length when preparing the message.
        This value determines the maximum message length that can be handled.
        For example, if `prepend_bytes_size` is set to 4, the maximum message length is 2^32 - 1.
        This is not enforced but will cause problems if not taken into consideration
        """

        self.port: int = port
        """The port number to connect to the server on."""

        self._socket: socket.socket = socket.socket()
        """Our socket to be used to connect to a server."""

        # Where we receive and store our messages
        self._receive_messages_thread: Union[threading.Thread, None] = None
        """The thread responsible for receiving and processing incoming messages."""
        self._received_messages: queue.Queue = queue.Queue()
        """A queue to store the received messages."""

        # If our thread should stop
        self._stop_event: threading.Event = threading.Event()
        """An event used to signal the thread to stop processing messages."""

        # How long our thread should wait for messages
        self._receive_messages_timeout: float = receive_messages_timeout
        """The maximum time in seconds to wait for incoming messages."""

        self.prepend_bytes_size: int = prepend_bytes_size
        """The number of bytes the message length is encoded to and prepended as"""

    @property
    def receiving_messages(self) -> bool:
        """
        Returns a bool indicating if the _receive_messages_thread has stopped.

        :return: True if the class instance is receiving messages, False otherwise.
        """

        return self._receive_messages_thread is not None

    def _receive_messages(self) -> None:
        """
        Internal method to receive and process incoming messages.

        This method is intended to be run in a separate thread.
        """

        while not self._stop_event.is_set():
            # If message to receive
            readable, _, _ = select.select([self._socket], [], [], self._receive_messages_timeout)
            if readable:
                # Length of the message
                message_length = int.from_bytes(self._socket.recv(self.prepend_bytes_size), byteorder="big")
                # Message
                message_bytes = self._socket.recv(message_length)
                # Store
                self._received_messages.put(message_bytes.decode("UTF-8"))

    def listen_for_messages(self) -> None:
        """
        Starts listening for incoming messages from the server.

        Does not need to be run to send messages.

        Client needs to be connected to the server before calling this.

        If the receiving messages thread is not already running, this method starts it in a separate thread.
        If the receiving messages thread is running, this method does nothing.
        """

        try:
            self._socket.getpeername()
        except socket.error as e:
            ...

        if self._receive_messages_thread is None:
            self._receive_messages_thread = threading.Thread(
                target=self._receive_messages,
                name=f"NetworkLib.TCP.Client._receive_messages"
            )
