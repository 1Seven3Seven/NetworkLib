def read_message_length(prepared_message: bytes, prepend_bytes: int = 4) -> int:
    """
    Reads the message length from the prepended bytes in a prepared message.

    :param prepared_message: The prepared message containing the prepended length.
    :param prepend_bytes: The number of bytes of the prepended length. Defaults to 4.
    :return: The message length as an integer.
    """

    # length_bytes = prepared_message[:prepend_bytes]
    # message_length = int.from_bytes(length_bytes, byteorder="big")
    # return message_length

    return int.from_bytes(prepared_message[:prepend_bytes], byteorder="big")
