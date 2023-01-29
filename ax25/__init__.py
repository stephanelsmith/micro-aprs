
import sys
import io
import asyncio
import struct
import traceback
from array import array
import math
from pydash import py_ as _

import matplotlib.pyplot as plt
from scipy import signal

from asyncio import Queue

from crc16 import crc16_ccit
from utils import parse_args
from utils import frange
from utils import pretty_binary
from utils import format_bytes
from utils import format_bits
from utils import int_div_ceil
from utils import reverse_byte
from utils import assign_bit
from utils import get_bit

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7


class CallSSID():
    __slots__ = (
        'call',
        'ssid',
    )
    def __init__(self, call = None, ssid = None,
                       aprs = None,
                       ax25 = None,
                       ):
        # Initialize a callsign ssid in three ways
        #   1) By specifying call and ssid explicitly
        #   2) By specifying aprs formatted string/bytes, eg. KI5TOF-5
        #   3) By specifying ax25 bytes to be decoded
        self.call = call 
        self.ssid = ssid
        if ax25:
            self.from_ax25(ax25)
        elif aprs:
            self.from_aprs(aprs)

    def from_aprs(self, call_ssid):
        #read in formats like KI5TOF-5
        if isinstance(call_ssid, str):
            call_ssid = callsign.split('-')
        elif isinstance(call_ssid, (bytes, bytearray)):
            call_ssid = callsign.decode('utf').split('-')
        else:
            raise Exception('unknown format '+str(call_ssid))
        self.call = call_ssid[0].upper()
        self.ssid = int(call_ssid[1]) if len(call_ssid)==2 else 0

    def to_aprs(self):
        if self.ssid:
            return str(self.call)+'-'+str(self.ssid)
        else:
            return str(self.call)

    def from_ax25(self, mv):
        #read from encoded ax25 format 
        if len(mv) != 7:
            raise Exception('callsign unable to read from bytes, bad length ' +str(len(mv)))
        for call_len in range(6):
            if mv[call_len] == 0x40: #searching for ' ' character (still left shifted one)
                break
            call_len += 1
        self.call = bytearray(mv[:call_len]) #make bytearray copy, don't modify in place
        for i in range(call_len):
            self.call[i] = self.call[i]>>1
        self.call = self.call.decode('utf')
        self.ssid = (mv[6] & 0x17)>>1

    def to_ax25(self):
        return b''

    def __repr__(self):
        return self.to_aprs()







class AX25():
    __slots__ = (
        'src',
        'dst',
        'digis',
        'info',
    )

    def __init__(self, src        = '',
                       dst        = '',
                       digis      = [],
                       info       = '',
                       aprs       = None,
                       ax25       = None,
                       ):
        # Initialize in three different ways
        #   1) The individual fields directly
        #   2) By APRS message, eg. M0XER-4>APRS64,TF3RPF,WIDE2*,qAR,TF3SUT-2:!/.(M4I^C,O `DXa/A=040849|#B>@\"v90!+|
        #   3) By AX25 bytes
        self.src        = src
        self.dst        = dst
        self.digis      = digis
        self.info       = info
        if ax25:
            self.from_ax25(ax25 = ax25)
        elif aprs:
            self.from_aprs(aprs = aprs)

    def callssid_to_str(self, callssid):
        try:
            return callssid.to_aprs()
        except:
            return ''

    def to_aprs(self):
        src = self.callssid_to_str(self.src)
        dst = self.callssid_to_str(self.dst)
        dst_digis = ','.join([dst]+[self.callssid_to_str(digi) for digi in self.digis])
        return src+'>'+dst_digis+':'+self.info
    
    def from_aprs(self, aprs):
        pass

    def from_ax25(self, ax25):
        mv = memoryview(ax25)

        idx = 0
        #flags
        while mv[idx] == AX25_FLAG and idx < len(mv):
            idx+=1
        start_idx = idx

        stop_idx = idx
        while mv[stop_idx] != AX25_FLAG and stop_idx < len(mv):
            stop_idx+=1

        #destination
        self.dst = CallSSID(ax25 = mv[idx:idx+AX25_ADDR_LEN])
        idx += AX25_ADDR_LEN

        #source
        self.src = CallSSID(ax25 = mv[idx:idx+AX25_ADDR_LEN])
        idx += AX25_ADDR_LEN
       
        #digis
        while not mv[idx-1]&0x01:
            self.digis.append(CallSSID(ax25 = mv[idx:idx+AX25_ADDR_LEN]))
            idx += AX25_ADDR_LEN

        #skip control/pid
        idx += 2

        self.info = bytes(mv[idx:stop_idx-2]).decode('utf')
        crc  = bytes(mv[stop_idx-2:stop_idx])
        _crc = struct.pack('<H',crc16_ccit(mv[start_idx:stop_idx-2]))
        if crc != _crc:
            raise Exception('crc error '+str(crc)+' != '+str(_crc))

    def __repr__(self):
        return self.to_aprs()



