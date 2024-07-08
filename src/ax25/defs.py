


class DecodeError(Exception):
    pass
class DecodeError(Exception):
    pass
class DecodeErrorNoFix(Exception):
    pass
class DecodeErrorFix(Exception):
    def __init__(self, ax25=None):
        self.ax25=ax25

class CallSSIDError(Exception):
    pass

