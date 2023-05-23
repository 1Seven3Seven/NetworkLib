import NetworkLib


def main():
    udp = NetworkLib.UDP.Messages()

    udp.listen_for_messages()


if __name__ == "__main__":
    main()
