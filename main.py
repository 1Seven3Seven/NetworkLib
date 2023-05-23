import NetworkLib


def main():
    # Ask for port to send on
    print("Please specify a port to send on")
    port = int(input("Port: "))

    # Create our object
    udp = NetworkLib.UDP.Messages(port=port)
    udp.listen_for_messages()

    # Displaying our ip
    print(f"Your up: {udp.ip}")

    # Ask where to send messages to
    print("Please specify an ip and port to send to")
    send_to_ip = input("Ip: ")
    send_to_port = int(input("Port: "))

    # Ask for either sending or receiving
    while True:
        # Get our choice
        print("1 to send message\n2 to receive messages\n0 to exit")
        choice = input("> ")
        while choice not in ["0", "1", "2"]:
            choice = input("> ")

        # Exiting
        if choice == "0":
            break

        # Sending a message
        if choice == "1":
            message = input("Message: ")

            udp.send_message(message, send_to_ip, send_to_port)

        # Receiving messages
        if choice == "2":
            messages = udp.get_messages()
            if messages:
                for message, _ in udp.get_messages():
                    print(f"Received: {message}")
            else:
                print("No messages received")

    # We are finished
    udp.shutdown()


if __name__ == "__main__":
    main()
