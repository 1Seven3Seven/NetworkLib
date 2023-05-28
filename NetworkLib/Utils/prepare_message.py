def prepare_message(message: str, prepend_bytes: int = 4) -> bytes:
    """
    Prepares a string message by converting it to UTF-8 bytes and prepending it with the specified number of bytes.

    :param message: The message to prepare.
    :param prepend_bytes: The number of bytes to prepend. Defaults to 4.
    :return: The prepared message as bytes with the length prepended.
    """

    message_bytes = message.encode("UTF-8")
    message_length = len(message_bytes).to_bytes(prepend_bytes, byteorder="big")
    return message_length + message_bytes
