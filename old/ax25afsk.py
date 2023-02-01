
import random 
import sys
import math
from pydash import py_ as _
#import numpy as np #TO DO REMOVE
import struct
import binascii

from array import array

from crc16 import crc16_ccit

from utils import pretty_binary
from utils import format_bytes
from utils import format_bits
from utils import parse_args
from utils import reverse_byte
from utils import frange
from utils import assign_bit
from utils import get_bit

verbose = False


AX25_FLAG      = 0x7e
AX25_FLAG_LEN  = 1
AX25_ADDR_LEN  = 7
AX25_CONTROLPID_LEN = 2
AX25_CRC_LEN   = 2
AX25_BITSTUFF_MARGIN = 5

AFSK_SCALE     = 50

class AFSK():

    def __init__(self, sampling_rate=22050):
        self.fmark = 1200
        self.tmark = 1/self.fmark
        self.fspace = 2200
        self.tspace = 1/self.fspace
        self.fs = sampling_rate
        self.ts = 1/self.fs
        self.fbaud = 1200
        self.tbaud = 1/self.fbaud
        self.residue_size = 10000

        #pre-compute sine lookup table
        self.lookup_size = 1024

        self.sin_array = array('i', (int((2**15-1)*math.sin(x)) for x in frange(0,2*math.pi,2*math.pi/self.lookup_size)))

        #get step sizes (integer and residue)
        mark_step     = self.lookup_size / (self.tmark/self.ts)
        self.mark_step_int = int(mark_step)
        self.mark_residue  = int((mark_step%1)*self.residue_size)

        space_step     = self.lookup_size / (self.tspace/self.ts)
        self.space_step_int = int(space_step)
        self.space_residue  = int((space_step%1)*self.residue_size)

        baud_step     = self.tbaud / self.ts
        self.baud_step_int = int(baud_step)
        self.baud_residue  = int((baud_step%1)*self.residue_size)

        self.markspace_residue_accumulator = 0
        self.baud_residue_accumulator = 0

        self.ts_index = 0
        self.baud_index = 0
        self.markspace_index = 0


    def gen_bits_from_bytes(self, frame, stop_bit = None):
        if stop_bit == None:
            stop_bit = len(frame)*8
        for idx in range(stop_bit):
            # self.append_baud_period(markspace = frame[idx//8]&(0x80>>(idx%8)))
            yield frame[idx//8]&(0x80>>(idx%8))

    def gen_baud_period_samples(self, markspace):
        self.baud_index = self.ts_index + self.baud_step_int
        self.baud_residue_accumulator += self.baud_residue
        self.baud_index += self.baud_residue_accumulator // self.residue_size
        self.baud_residue_accumulator = self.baud_residue_accumulator % self.residue_size 

        #cycle one baud period
        while self.ts_index < self.baud_index:
            if markspace:
                self.markspace_index += self.mark_step_int
                self.markspace_residue_accumulator += self.mark_residue 
            else:
                self.markspace_index += self.space_step_int
                self.markspace_residue_accumulator += self.space_residue  		
            
            #mark and space share the same index and accumulator, this way the phase in continuous
            #as we switch between mark/space
            #increment by residual amount if we overflow residue size
            self.markspace_index += self.markspace_residue_accumulator // self.residue_size 
            self.markspace_residue_accumulator = self.markspace_residue_accumulator % self.residue_size
            
            #push the next point to the waveform
            yield self.sin_array[self.markspace_index%self.lookup_size]

            self.ts_index += 1 #increment one unit time step (ts = 1/fs)


    def dump_ax25_raw_samples(self, ax25,
                                    zpad_ms,
                                    out_type):
        o = []
        #zero padding
        for b in range(int(zpad_ms/self.ts+1)):
            o.append(0)

        #write data
        for bit in self.gen_bits_from_bytes(frame    = ax25.frame,
                                            stop_bit = ax25.frame_len_bits):
            for sample in self.gen_baud_period_samples(bit):
                o.append(sample//AFSK_SCALE)

        if out_type == 'raw':
            buf = bytearray(len(o)*2)
            for i,s in enumerate(o):
                x = struct.pack('<h', s)
                # x = int.to_bytes(s, 2, 'little', signed=True)
                buf[i*2]   = x[0]
                buf[i*2+1] = x[1]
            sys.stdout.buffer.write(buf)
        else:
            print('type not implemented', out_type)

class AX25():
    def __init__(self):
        self.frame = bytearray()
        self.frame_len_bits = 0

    def encode_ui_frame(self, src,       # source address
                              dst,       # destination address
                              digis,     # digipeater list
                              info,      # info
                              flags_pre   = 1,
                              flags_post  = 1,
                              debug       = False,
                              ):

        #pre-allocate entire buffer size
        frame_len = AX25_FLAG_LEN*flags_pre +\
                    AX25_ADDR_LEN +\
                    AX25_ADDR_LEN +\
                    len(digis)*AX25_ADDR_LEN+\
                    AX25_CONTROLPID_LEN+\
                    len(info)+\
                    AX25_CRC_LEN +\
                    AX25_FLAG_LEN*flags_post
        self.frame_len_bits = frame_len * 8
        self.frame = bytearray(frame_len + AX25_BITSTUFF_MARGIN)

        #create slices without copying
        mv    = memoryview(self.frame)
        idx = 0

        if debug:
            print('-FRAME-')

        #pre-flags
        for fidx in range(flags_pre):
            mv[idx] = AX25_FLAG
            idx += AX25_FLAG_LEN
        if debug:
            print('FLAGS:'.ljust(15), format_bytes(mv[:idx]))

        # destination Address  (note: opposite order in printed format)
        self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                             callsign = dst)
        if debug:
            print('DEST_ADDR:'.ljust(15),dst.ljust(15),format_bytes(mv[idx:idx+AX25_ADDR_LEN]), format_bits(mv[idx:idx+AX25_ADDR_LEN]))
        idx += AX25_ADDR_LEN

        # source Address
        self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                             callsign = src)
        if debug:
            print('SRC_ADDR:'.ljust(15),src.ljust(15),format_bytes(mv[idx:idx+AX25_ADDR_LEN]), format_bits(mv[idx:idx+AX25_ADDR_LEN]))
        idx += AX25_ADDR_LEN

        # 0-8 Digipeater Addresses
        for digi in digis[:8]:
            self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                                 callsign = digi)
            if debug:
                print('DIGI_ADDR:'.ljust(15),digi.ljust(15),format_bytes(mv[idx:idx+AX25_ADDR_LEN]), format_bits(mv[idx:idx+AX25_ADDR_LEN]))
            idx += AX25_ADDR_LEN

        #LAST BIT OF ADDRESS, SET LSB TO 1
        mv[idx-1]  |= 0x01 

        mv[idx] = 0x03 #control
        idx += 1
        mv[idx] = 0xf0 #pid
        idx += 1
        if debug:
            print('CONTROL/PID:'.ljust(15), format_bytes(mv[idx-2:idx]), format_bits(mv[idx-2:idx]))

        #payload
        mv[idx:idx+len(info)] = bytes(info,'utf')
        if debug:
            print('INFO (bin):'.ljust(15), format_bytes(mv[idx:idx+len(info)]), format_bits(mv[idx:idx+len(info)]))
            print('INFO (str):'.ljust(15), bytes(mv[idx:idx+len(info)]))
        idx += len(info)

        #crc
        crc = struct.pack('<H',crc16_ccit(mv[flags_pre*AX25_FLAG_LEN:idx]))
        mv[idx:idx+AX25_CRC_LEN] = crc
        if debug:
            print('CRC:'.ljust(15), format_bytes(mv[idx:idx+AX25_CRC_LEN]), format_bits(mv[idx:idx+AX25_CRC_LEN]))
            print('CRC:'.ljust(15), format_bytes(mv[flags_pre*AX25_FLAG_LEN:idx]))
        idx += AX25_CRC_LEN

        #post-flags
        tidx = idx 
        for fidx in range(flags_post):
            mv[idx] = AX25_FLAG
            idx += AX25_FLAG_LEN
        if debug:
            print('FLAGS:'.ljust(15), format_bytes(mv[tidx:idx]))

        if idx != frame_len:
            raise Exception('frame len error: idx ({}) != frame_len ({})'.format(idx, frame_len))

        if debug:
            print('-frame-')
            pretty_binary(mv)

        #revese bit order
        self.reverse_bit_order(mv, frame_len)
        if debug:
            print('-reversed-')
            pretty_binary(mv)

        # stuff bits in place
        # update the total number of bits
        stuff_cnt = self.do_bitstuffing(mv, 
                                        start_bit = flags_pre*AX25_FLAG_LEN*8, 
                                        stop_bit  = self.frame_len_bits - flags_post*AX25_FLAG_LEN*8)
        self.frame_len_bits += stuff_cnt
        if debug:
            print('-bit stuffed-')
            pretty_binary(mv)

        #convert to nrzi
        self.convert_nrzi(mv,
                          stop_bit = self.frame_len_bits)
        if debug:
            print('-nrzi-', self.frame_len_bits//8)
            pretty_binary(mv)

    def encode_callsign(self, b_out, callsign,):
        #split callsign from ssid, eg. KI5TOF-5
        call_ssid = callsign.split('-')
        call = call_ssid[0].upper()
        ssid = int(call_ssid[1]) if len(call_ssid)==2 else 0
        #callsign exactly 6 characters
        call = call[:6]
        call = call+' '*(6-len(call))
        #to bytes
        b_out[:6] = bytes(call, 'utf')
        #shift left in place
        for idx in range(6):
            b_out[idx] = b_out[idx]<<1
        #SSID is is the 6th bit, shift left by one
        #the right most bit is used to indicate last address
        b_out[6]  = ssid<<1
        b_out[6]  |= 0x60
    
    def reverse_bit_order(self, mv, frame_len):
        for idx in range(frame_len):
            mv[idx] = reverse_byte(mv[idx])

    def do_bitstuffing(self, mv, start_bit, stop_bit):
        #bit stuff frame in place
        idx = start_bit
        c = 0   #running count of consecutive 1s
        cnt = 0 #count of number of bits that were stuffed
        while idx < stop_bit:
            if get_bit(mv[idx//8], idx):
                c += 1
            else:
                c = 0
            idx += 1
            if c == 5:
                #stuff a bit
                #shift all bytes to the right, starting next byte
                self.insert_bit_in_array(mv, bit_idx = idx)
                c = 0
                cnt += 1 
                idx += 1
        return cnt

    def insert_bit_in_array(self, mv, bit_idx):
        #shift bytes right
        self.shift_bytes_right(mv, start_byte = bit_idx//8+1)
        #byte in question, stuff the bit
        self.split_shift_byte(mv, bit_idx)

    def shift_bytes_right(self, mv, start_byte, stop_byte=None):
        #shift bytes right by one bit
        if not stop_byte:
            stop_byte = len(mv)
        #idx iterating byte index
        for idx in range(stop_byte-1, start_byte-1, -1):
            #work from right to left
            p       = 0 if idx == 0 else (mv[idx-1]&0x01)
            q       = 0x80 if p else 0
            mv[idx] = (mv[idx]>>1) | q

    def split_shift_byte(self, mv, idx):
        #insert a 0 at bit index position
        if idx%8 == 0:
            #if we are shifting the first bit, just shift
            mv[idx//8] = mv[idx//8] >> 1
        else:
            #we need to split at specific bit index position
            #right side
            t_shift = mv[idx//8] & (0xff>>(idx%8))
            t_shift = t_shift >> 1
            #left side
            mv[idx//8] = mv[idx//8] & (0xff<<((8-idx)%8))
            #combine, 0 (stuffed bit), left in center
            mv[idx//8] = mv[idx//8] | t_shift
    
    def convert_nrzi(self, mv, stop_bit):
        #https://en.wikipedia.org/wiki/Non-return-to-zero
        #The HDLC a logical 0 is transmitted as a transition, and a logical 1 is transmitted as no transition.
        c = 0
        for idx in range(stop_bit):
            mask = (0x80)>>(idx%8)
            b = get_bit(mv[idx//8], idx)
            if b == 0:
                #toggle
                c ^= 0x01
            mv[idx//8] = assign_bit(mv[idx//8], idx, c)

args = parse_args({
    'rate' : {
        'short'   : 'r',
        'type'    : int,
        'default' : 22050,
    },
    'zpad_ms' : {
        'short'   : 'z',
        'type'    : float,
        'default' : 26.5,
    },
    'flags_pre' : {
        'short'   : 'flags_pre',
        'type'    : int,
        'default' : 1+32,
    },
    'flags_post' : {
        'short'   : 'flags_post',
        'type'    : int,
        'default' : 1+2,
    },
    'debug' : {
        'short'   : 'debug',
        'type'    : bool,
        'default' : False,
    },
    'out_type' : {
        'short'   : 't',
        'type'    : str,
        'default' : 'raw', #raw|int|list
    },
})

afsk = AFSK(sampling_rate = args['rate'])


ax25 = AX25()
ax25.encode_ui_frame(src        = 'KI5TOF',
                     dst        = 'APRS',
                     digis      = [],
                     info       = '>hello world', 
                     flags_pre  = args['flags_pre'],
                     flags_post = args['flags_post'],
                     debug      = args['debug'])
if args['debug']:
    #we are debugging, exit early
    exit()

afsk.dump_ax25_raw_samples(ax25     = ax25,
                           zpad_ms  = args['zpad_ms'],
                           out_type = args['out_type'],
                           )

