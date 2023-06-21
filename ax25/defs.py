


class DecodeError(Exception):
    pass

class CRCError(Exception):
    def __init__(self, ax25=None):
        self.ax25=ax25

class CallSSIDError(Exception):
    pass

