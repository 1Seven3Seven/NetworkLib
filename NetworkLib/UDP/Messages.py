import queue
import select
import socket
import threading
from typing import Union

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
        self._receive_messages_thread: Union[threading.Thread, None] = None
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

    def listen_for_messages(self) -> None:
        """
        Starts listening for incoming messages on the specified port.

        Does not need to be run to send messages.

        If the receiving messages thread is not already running, this method starts it in a separate thread.
        If the receiving messages thread is running, this method does nothing.
        """

        # If we are not already listening
        if self._receive_messages_thread is None:
            # Start listening
            self._receive_messages_thread = threading.Thread(
                target=self._receive_messages,
                args=(self._stop_event,),
                name=f"NetworkLib.UDP.Messages listening on port {self.port}"
            )
            self._receive_messages_thread.start()

    def get_messages(self) -> list:
        """
        Retrieves the list of received messages.

        :return: A list of received messages. Each message is represented as a tuple containing the message content and
        the address from which it was received. If no messages have been received, an empty list is returned.
        """

        messages = []
        while not self._received_messages.empty():
            messages.append(self._received_messages.get())
        return messages

    def send_message(self, message: str, ip: str, port: int = None) -> None:
        """
        Sends a message to the specified IP address and port.

        :param message: The message to be sent as a string.
        :param ip: The IP address of the destination.
        :param port: The port number of the destination. If not provided, the default port number of the `Messages`
        instance is used.
        """

        self._socket.sendto(
            message.encode("utf-8"),
            (
                ip,
                self.port if port is None else port)
        )

    def stop_listening_for_messages(self) -> None:
        """
        Stops listening for incoming messages.

        Blocks until all incoming messages have been processed.

        `listen_for_messages` needs to be run again to start listening again.
        """

        # If the thread exists
        if self._receive_messages_thread is not None:
            # Set the stop event
            self._stop_event.set()

            # Wait for the thread to finish
            self._receive_messages_thread.join()

            # Remove the thread as it can not be started again
            self._receive_messages_thread = None

    def close_socket(self) -> None:
        """
        Closes the socket connection.

        Please call `stop_listening_for_messages` before calling this.

        Class instance is effectively useless after this is called and all messages have been received.

        :raises RuntimeError: If `stop_listening_for_messages` has not been called before closing the socket.
        """

        if self._receive_messages_thread is not None:
            raise RuntimeError("Please call stop_listening_for_messages before closing the socket.")

        self._socket.close()
