
import random 
import sys
import math
from pydash import py_ as _
#import numpy as np #TO DO REMOVE
import struct
import binascii

from crc16 import crc16_ccit

from utils import print_binary
from utils import parse_args
from utils import reverse_byte
from utils import frange

verbose = False


AX25_FLAG      = 0x7e
AX25_FLAG_NRZI = 0xfe #preconverted to NRZI
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

        self.sin_array = array('i', int((2**15-1)*math.sin(x)) for x in frange(0,2*math.pi,2*math.pi/self.lookup_size))

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


    #TODO, DONT APPEND TO ARRAY
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

    def encode_ui_frame(self, src,
                              dst, 
                              digis,
                              info, 
                              flags_pre  = 1,
                              flags_post = 1,
                              dbg_frame = False):

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

        #pre-flags
        for fidx in range(flags_pre):
            mv[idx] = AX25_FLAG
            idx += AX25_FLAG_LEN

        # destination Address  (note: opposite order in printed format)
        self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                             callsign = dst)
        idx += AX25_ADDR_LEN
        mv[idx-1]  |= 0xe0  #last bit of the addr
        # source Address
        self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                             callsign = src)
        idx += AX25_ADDR_LEN
        mv[idx-1]  |= 0xe0  #last bit of the addr
        # 0-8 Digipeater Addresses
        for digi in digis[:8]:
            self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                                 callsign = digi)
            mv[idx-1]  |= 0x60  #last bit of the addr
            idx += AX25_ADDR_LEN
        mv[idx-1]  |= 0x01  #last bit of the addr
        mv[idx] = 0x03 #control
        idx += 1
        mv[idx] = 0xf0 #pid
        idx += 1

        #copy info
        mv[idx:idx+len(info)] = bytes(info,'utf')
        idx += len(info)

        #crc
        # print(len(mv),idx)

        crc_len = 2
        mv[idx:idx+crc_len] = bytearray(struct.pack('<H',crc16_ccit(mv[flags_pre*AX25_FLAG_LEN:idx])))
        idx += crc_len

        #post-flags
        for fidx in range(flags_post):
            mv[idx] = AX25_FLAG
            idx += AX25_FLAG_LEN

        if idx != frame_len:
            raise Exception('frame len error: idx ({}) != frame_len ({})'.format(idx, frame_len))

        if dbg_frame:
            print_binary(mv)

        #revese bit order
        self.reverse_bit_order(mv, frame_len)

        # stuff bits in place
        # update the total number of bits
        stuff_cnt = self.do_bitstuffing(mv, 
                                        start_bit = flags_pre*AX25_FLAG_LEN*8, 
                                        stop_bit  = self.frame_len_bits - flags_post*AX25_FLAG_LEN*8)
        self.frame_len_bits += stuff_cnt
        # print('-bit stiffed-')
        # print('frame_len_bits', frame_len_bits)
        # print_binary(mv)

        #convert to nrzi
        self.convert_nrzi(mv,
                          stop_bit = self.frame_len_bits)
        # print_binary(mv)

    def encode_callsign(self, b_out, callsign,):
        #split callsign from ssid
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
        # b_out[6]  = 0x60|(ssid<<1)
        b_out[6]  = ssid<<1
    
    def reverse_bit_order(self, mv, frame_len):
        for idx in range(frame_len):
            mv[idx] = reverse_byte(mv[idx])

    def do_bitstuffing(self, mv, start_bit, stop_bit):
        #bit stuff frame in place
        idx = start_bit
        cnt = 0
        stuff_cnt = 0
        while idx < stop_bit:
            if mv[idx//8] & (0x80>>(idx%8)):
                cnt += 1
            else:
                cnt = 0
            idx += 1
            if cnt == 5:
                #stuff a bit
                #shift all bytes to the right, starting next byte
                self.insert_bit_in_array(mv, bit_idx = idx)
                cnt = 0
                stuff_cnt += 1 #
                idx += 1
        return stuff_cnt

    def insert_bit_in_array(self, mv, bit_idx):
        self.shift_bytes_right(mv, start_byte = bit_idx//8+1)
        self.split_shift_byte(mv, bit_idx)

    def shift_bytes_right(self, mv, start_byte, stop_byte=None):
        if not stop_byte:
            stop_byte = len(mv)
        for idx in range(stop_byte-1, start_byte-1, -1):
            p       = 0 if idx == 0 else (mv[idx-1]&0x01)
            q       = 0x80 if p else 0
            mv[idx] = (mv[idx]>>1) | q

    def split_shift_byte(self, mv, idx):
        if idx%8 == 0:
            mv[idx//8] = mv[idx//8] >> 1
        else:
            #right side
            t_shift = mv[idx//8] & (0xff>>(idx%8))
            t_shift = t_shift >> 1
            #left side
            mv[idx//8] = mv[idx//8] & (0xff<<((8-idx)%8))
            #combine, 0 (stuffed bit), left in center
            mv[idx//8] = mv[idx//8] | t_shift
    
    def convert_nrzi(self, mv, stop_bit):
        cur = 1
        for idx in range(stop_bit):
            mask = (0x80>>(idx%8))
            b    = mv[idx//8] & mask
            if b == 0:
                cur = cur ^ 0x01  #equivalent to statement below
                # cur = 0 if cur else 1
            if cur:
                # set bit
                mv[idx//8]  = mv[idx//8] | mask
            else:
                # clear bit, no bitwise 'not' in python, xor 0xff to mimick
                mv[idx//8]  = mv[idx//8] & (mask ^ 0xff)
            #invert bit
            mv[idx//8]  = mv[idx//8] ^ mask


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
    'print_frame' : {
        'short'   : 'print_frame',
        'type'    : bool,
        'default' : False,
    },
    # 'volume' : {
    # },
    'out_type' : {
        'short'   : 't',
        'type'    : str,
        'default' : 'raw', #raw|int|list
    },
})

afsk = AFSK(sampling_rate = args['rate'])


ax25 = AX25()
ax25.encode_ui_frame(src        = 'A',
                     dst        = 'APRS',
                     digis      = [],
                     info       = '>hello', 
                     flags_pre  = args['flags_pre'],
                     flags_post = args['flags_post'],
                     dbg_frame  = args['print_frame'])
if args['print_frame']:
    #we are debugging, exit early
    exit()

afsk.dump_ax25_raw_samples(ax25     = ax25,
                           zpad_ms  = args['zpad_ms'],
                           out_type = args['out_type'],
                           )

