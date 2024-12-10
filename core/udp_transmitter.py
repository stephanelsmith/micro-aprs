# core/udp_transmitter.py

import socket

def parse_udp_message(raw_message):
    """
    Parse the received UDP message to extract the actual content.
    """
    try:
        # Split the message at the first colon
        prefix, message = raw_message.split(":", 1)
        return message.strip()
    except ValueError:
        # If the message doesn't contain a colon, return the whole raw message
        return raw_message.strip()

def udp_transmitter(host, port, message):
    """
    Send an APRS message via UDP.
    This is a simple, synchronous transmitter function.
    If you need it to run continuously, you could implement it similarly to the listener.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Send the message
            message = parse_udp_message(message)
            sock.sendto(message.encode('utf-8'), (host, port))
            print(f"Sent UDP message to {host}:{port}: {message}")
    except Exception as e:
        print(f"Error in UDP transmitter: {e}")
