import threading

class Frequency:
    def __init__(self, initial_value):
        self._value = initial_value
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            return self._value

    def set(self, value):
        with self._lock:
            self._value = value

class ThreadSafeVariable:
    def __init__(self, initial_value):
        self._value = initial_value
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            return self._value

    def set(self, value):
        with self._lock:
            self._value = value

def start_receiver_thread(receiver_stop_event, received_message_queue, device_index, frequency):
    receiver_thread = threading.Thread(
        target=start_receiver,
        args=(receiver_stop_event, received_message_queue, device_index, frequency),
        daemon=True
    )
    receiver_thread.start()
    return receiver_thread

def stop_receiver(stop_event, receiver_thread):
    stop_event.set()