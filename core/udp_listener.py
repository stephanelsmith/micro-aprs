# core/udp_listener.py

import socket

def udp_listener(host, port, message_queue, stop_event):
    """
    Listen for APRS messages over UDP and add them to the message_queue.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, port))
        sock.settimeout(0.5)
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(1024)
                aprs_message = data.decode().strip()
                print(f"Received UDP message from {addr}: {aprs_message}")
                message_queue.put(aprs_message)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error in UDP listener: {e}")
