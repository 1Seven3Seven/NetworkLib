import socket
from ipaddress import IPv4Address


def get_local_ip() -> IPv4Address:
    """
    This function attempts to obtain the local IP address of the machine by creating a temporary socket and connecting
    it to a known external IP address and port.

    If successful, it returns the local IP address associated with the socket.

    If the connection fails or encounters an error, it falls back to an alternative method by using
    `socket.gethostbyname(socket.gethostname())` to retrieve the local IP address.

    :return: The local IP address of the machine.
    """

    try:
        # Create a temporary socket
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Use a known external IP address and port
        temp_socket.connect(("8.8.8.8", 80))
        # Extract the local ip
        local_ip_address = temp_socket.getsockname()[0]
        # Close our socket
        temp_socket.close()
        # Done
        return IPv4Address(local_ip_address)
    except socket.error:
        # Fallback: try an alternative method to retrieve the local IP address
        return IPv4Address(socket.gethostbyname(socket.gethostname()))
