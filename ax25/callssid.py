
from ax25.defs import CallSSIDError

AX25_ADDR_LEN  = 7

ORD_0 = 48
ORD_9 = 57
ORD_A = 65
ORD_Z = 90
ORD_COLON = 58

class CallSSID():
    __slots__ = (
        'call',
        'ssid',
        #'_frame',
    )
    def __init__(self, call = None, # bytes/bytearray
                       ssid = None, # bytes/bytearry
                       aprs = None, # str/bytes/bytearray
                       frame = None,
                       ):
        # Initialize a callsign ssid in three ways
        #   1) By specifying call and ssid explicitly
        #   2) By specifying aprs formatted string/bytes, eg. KI5TOF-5
        #   3) By specifying frame bytes to be decoded
        self.call = call 
        self.ssid = ssid
        #self._frame = None
        if frame:
            #self._frame = bytes(frame)
            self.from_ax25_frame(frame)
        elif aprs:
            self.from_aprs(aprs)

    def from_aprs(self, call_ssid):
        #read in formats like KI5TOF-5
        if isinstance(call_ssid, str):
            call_ssid = call_ssid.encode()
        elif isinstance(call_ssid, (bytes, bytearray)):
            pass
        else:
            raise Exception('unknown format '+str(call_ssid))
        call_ssid = call_ssid.split(b'-')
        self.call = call_ssid[0].upper()
        self.ssid = int(call_ssid[1]) if len(call_ssid)==2 else 0

    def to_aprs(self):
        if self.ssid:
            return self.call+b'-'+self.ssid
            # return str(self.call)+'-'+str(self.ssid)
        else:
            return self.call
            # return str(self.call)

    def from_ax25_frame(self, mv):
        #read from encoded ax25 format 
        if len(mv) != 7:
            raise CallSSIDError('callsign bad len {} != {}'.format(len(mv),7))
        for call_len in range(6):
            if mv[call_len] == 0x40: #searching for ' ' character (still left shifted one)
                break
            call_len += 1
        self.call = bytearray(mv[:call_len]) #make bytearray copy, don't modify in place
        for i in range(call_len):
            self.call[i] = self.call[i]>>1

        # self.call = self.call.decode()
        self.ssid = (mv[6] & 0x17)>>1

    def is_valid(self):
        if not self.call:
            return False
        for x in self.call:
            # x = ord(x)
            if x >= ORD_0 and x <= ORD_9 or\
               x >= ORD_A and x <= ORD_Z:
                pass
            else:
                return False
        return True

    def to_bytes(self, mv = None,):
        #optional mv, write in place if provided
        #callsign exactly 6 characters
        if not mv:
            ax25 = bytearray(7)# AX25_ADDR_LEN
            mv = memoryview(ax25)
        for i in range(len(self.call)):
            mv[i] = self.call[i]
            if i == 6:
                break
        for i in range(6):
            mv[i] = self.call[i] if i < len(self.call) else ord(' ')
            #shift left in place
            mv[i] = mv[i]<<1
        #SSID is is the 6th bit, shift left by one
        #the right most bit is used to indicate last address
        mv[6] = self.ssid<<1
        mv[6] |= 0x60
        return mv

    def __repr__(self):
        return self.to_aprs()


