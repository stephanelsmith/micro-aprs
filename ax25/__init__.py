
import sys
import io
import asyncio
import struct
import traceback
from array import array
# from pydash import py_ as _

from asyncio import Queue

from ax25.callssid import CallSSID
from ax25.callssid import DecodeError
from ax25.func import reverse_bit_order
from ax25.func import convert_nrzi
from ax25.func import do_bitstuffing

import lib.upydash as _
from lib.crc16 import crc16_ccit
from lib.utils import pretty_binary
from lib.utils import eprint
from lib.utils import format_bytes

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7
AX25_FLAG      = 0x7e
AX25_FLAG_LEN  = 1
AX25_ADDR_LEN  = 7
AX25_CONTROLPID_LEN = 2
AX25_CRC_LEN   = 2

class AX25():
    # __slots__ = (
        # 'src',
        # 'dst',
        # 'digis',
        # 'info',
    # )

    def __init__(self, src        = '',
                       dst        = '',
                       digis      = [],
                       info       = '',
                       aprs       = None,
                       frame      = None,
                       verbose    = False,
                       ):
        self.verbose = verbose
        # Initialize in three different ways
        #   1) The individual fields directly
        #   2) By APRS message, eg. M0XER-4>APRS64,TF3RPF,WIDE2*,qAR,TF3SUT-2:!/.(M4I^C,O `DXa/A=040849|#B>@\"v90!+|
        #   3) By ax25 frame bytes
        if frame != None:
            self.from_ax25_frame(frame = frame)
        elif aprs != None:
            self.from_aprs(aprs = aprs)
        else:
            self.src        = CallSSID(aprs = src)
            self.dst        = CallSSID(aprs = dst)
            self.digis      = [CallSSID(aprs = x) for x in digis]
            self.info       = info

    def callssid_to_str(self, callssid):
        try:
            return callssid.to_aprs()
        except:
            return ''

    def to_aprs(self):
        src = self.callssid_to_str(self.src)
        dst = self.callssid_to_str(self.dst)
        dst_digis = ','.join([dst]+[self.callssid_to_str(digi) for digi in self.digis])
        if isinstance(self.info, (bytes, bytearray)):
            info = self.info.decode().strip()
        elif isinstance(self.info, (bytes, bytearray)):
            info = self.info.strip()
        else:
            info = str(self.info).strip()
        return src+'>'+dst_digis+':'+info
    
    def from_aprs(self, aprs):
        # KI5TOF>APRS,WIDE1-1,WIDE2-1:hello world!
        if isinstance(aprs, (bytes, bytearray)):
            aprs = aprs.decode('utf')
        par = 0
        i = _.find_index(aprs,'>')
        if not i:
            raise Exception('could not find source',aprs)
        self.src = CallSSID(aprs = aprs[par:i])
        par += i + 1

        i = _.find_index(aprs,':')
        if not i:
            raise Exception('could not find digis ',aprs)
        digis = aprs[par:i].split(',')
        self.dst = CallSSID(aprs = digis.pop(0))
        self.digis = [CallSSID(aprs = digi) for digi in digis]
        par += i + 1

        self.info = aprs[i+1:]


    def from_ax25_frame(self, frame):
        # from bytearray to ax25 structure
        # this function is AFTER unNRZI, unstuffing, reversed
        # the BitStreamToAX25 handles that, this  function
        # only maps bytes to their field structure

        mv = memoryview(frame)

        try:

            idx = 0
            #flags
            while idx < len(mv) and mv[idx] == AX25_FLAG:
                idx+=1
            start_idx = idx
            if idx == len(mv):
                raise DecodeError()

            stop_idx = len(mv)-1
            while stop_idx > 0 and mv[stop_idx] != AX25_FLAG:
                stop_idx-=1

            if start_idx == stop_idx:
                raise DecodeError('no frame found')
        
            #destination
            self.dst = CallSSID(frame = mv[idx:idx+AX25_ADDR_LEN])
            idx += AX25_ADDR_LEN

            #source
            self.src = CallSSID(frame = mv[idx:idx+AX25_ADDR_LEN])
            idx += AX25_ADDR_LEN
        
            #digis
            self.digis = []
            while not mv[idx-1]&0x01 and idx<stop_idx-1:
                self.digis.append(CallSSID(frame = mv[idx:idx+AX25_ADDR_LEN]))
                idx += AX25_ADDR_LEN

            if idx==stop_idx-1:
                raise DecodeError('err decoding digis, {}'.format(frame))

            #skip control/pid
            idx += 2
            
            try:
                # self.info = bytes(mv[idx:stop_idx-2]).decode('utf')
                self.info = bytes(mv[idx:stop_idx-2])
            except UnicodeDecodeError:
                raise DecodeError('bad payload {} '.format(bytes(mv[idx:stop_idx-2])))

            crc  = bytes(mv[stop_idx-2:stop_idx])
            _crc = struct.pack('<H',crc16_ccit(mv[start_idx:stop_idx-2]))
            # eprint('{} {}'.format(format_bytes(crc),format_bytes(_crc)))
            if crc != _crc:
                eprint('crc err: {}'.format(bytes(mv[:stop_idx])))
                raise DecodeError('crc error {} != {}'.format(crc, _crc))

        except DecodeError as err:
            # eprint(err)
            raise

    def to_ax25(self, bit_stuff_margin = 0, # the number of additional bytes, placeholder for stuffing
                      flags_pre        = 1, # number of pre-flags
                      flags_post       = 1, # number of post-flags
                      ):
        #from structure to bytearray

        #pre-allocate entire buffer size
        ax25_len = AX25_FLAG_LEN*flags_pre +\
                    AX25_ADDR_LEN +\
                    AX25_ADDR_LEN +\
                    len(self.digis)*AX25_ADDR_LEN+\
                    AX25_CONTROLPID_LEN+\
                    len(self.info)+\
                    AX25_CRC_LEN +\
                    AX25_FLAG_LEN*flags_post
        ax25 = bytearray(ax25_len + bit_stuff_margin)

        #create slices without copying
        mv    = memoryview(ax25)
        idx = 0

        #pre-flags
        for fidx in range(flags_pre):
            mv[idx] = AX25_FLAG
            idx += AX25_FLAG_LEN

        # destination Address  (note: opposite order in printed format)
        self.dst.to_ax25(mv = mv[idx:idx+AX25_ADDR_LEN])
        idx += AX25_ADDR_LEN

        # source Address
        self.src.to_ax25(mv = mv[idx:idx+AX25_ADDR_LEN])
        idx += AX25_ADDR_LEN

        # 0-8 Digipeater Addresses
        for digi in self.digis[:8]:
            digi.to_ax25(mv = mv[idx:idx+AX25_ADDR_LEN])
            idx += AX25_ADDR_LEN

        #LAST BIT OF ADDRESS, SET LSB TO 1
        mv[idx-1]  |= 0x01 

        mv[idx] = 0x03 #control
        idx += 1
        mv[idx] = 0xf0 #pid
        idx += 1

        #payload
        mv[idx:idx+len(self.info)] = bytes(self.info,'utf')
        idx += len(self.info)

        #crc
        crc = struct.pack('<H',crc16_ccit(mv[flags_pre*AX25_FLAG_LEN:idx]))
        mv[idx:idx+AX25_CRC_LEN] = crc
        idx += AX25_CRC_LEN

        #post-flags
        tidx = idx 
        for fidx in range(flags_post):
            mv[idx] = AX25_FLAG
            idx += AX25_FLAG_LEN

        if idx != ax25_len:
            raise Exception('ax25 len error: idx ({}) != ax25_len ({})'.format(idx, ax25_len))

        return ax25

    def to_afsk(self, flags_pre        = 1, # number of pre-flags
                      flags_post       = 1, # number of post-flags
                      ):
        # everything in to_ax25, but also
        # reverse bit order
        # stuff bits
        # NRZI encode
        # ready to afsk out

        bit_stuff_margin = 8
        ax25 = self.to_ax25(bit_stuff_margin = bit_stuff_margin,
                            flags_pre        = flags_pre, # number of pre-flags
                            flags_post       = flags_post, # number of post-flags
                            )
        mv = memoryview(ax25)
        stop_bit = (len(ax25)-bit_stuff_margin) * 8

        #revese bit order
        reverse_bit_order(mv)
        if self.verbose:
            eprint('-reversed-')
            pretty_binary(mv)

        # stuff bits in place
        # update the total number of bits
        stuff_cnt = do_bitstuffing(mv, 
                                   start_bit = flags_pre*AX25_FLAG_LEN*8, 
                                   stop_bit  = stop_bit - flags_post*AX25_FLAG_LEN*8)
        stop_bit += stuff_cnt
        if self.verbose:
            eprint('-bit stuffed-')
            pretty_binary(mv)

        #convert to nrzi
        # convert_nrzi(mv,
                     # stop_bit = stop_bit)
        # if self.verbose:
            # eprint('-nrzi-', stop_bit)
            # pretty_binary(mv)
        return (ax25,stop_bit)

    def __repr__(self):
        return self.to_aprs()

