import queue
import select
import socket
import threading

from NetworkLib.Utils import get_local_ip


class Messages:
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

        # How long our thread should wait for messages
        self._receive_messages_timeout = receive_messages_timeout
        """The maximum time in seconds to wait for incoming messages."""

    @property
    def thread_stopped(self) -> bool:
        """
        Returns a flag indicating if the _receive_messages_thread has stopped.

        :return: True if the _receive_messages_thread has stopped, False otherwise.
        """

        return not self._receive_messages_thread.is_alive()

    def _receive_messages(self, stop_event: threading.Event) -> None:
        """
        Internal method to receive and process incoming messages.

        This method is intended to be run in a separate thread.

        :param stop_event: An event used to signal the thread to stop processing messages.
        """

        # While we are not to stop
        while not stop_event.is_set():
            # Check if there is a message to receive for the next x seconds
            readable, _, _ = select.select([self._socket], [], [], self._receive_messages_timeout)
            if len(readable) > 0:  # If there is a message
                # Get the message, decode it, store it
                message_bytes, address = self._socket.recvfrom(self.port)
                message = message_bytes.decode("utf-8")
                self._received_messages.put((message, address))
