
import random 
import sys
import math
from pydash import py_ as _
import numpy as np
import struct
import binascii
import argparse

from crc16 import crc16_ccit

verbose = False

parser = argparse.ArgumentParser()
parser.add_argument('-r','--rate',
                    help='sampling rate',
                    nargs='?',
                    default=22050, 
                    type=int,
                    )
args = parser.parse_args()

def reverse_byte(_byte):
    #xor reverse bit technique
    _byte = ((_byte & 0x55) << 1) | ((_byte & 0xAA) >> 1);
    _byte = ((_byte & 0x33) << 2) | ((_byte & 0xCC) >> 2);
    _byte = ((_byte & 0x0F) << 4) | ((_byte & 0xF0) >> 4);
    return _byte

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

        self.lookup_size = 1024
        s16_sin = [(2**15-1)*math.sin(x) for x in np.arange(0,2*math.pi,2*math.pi/self.lookup_size)]
        self.sin_array = _.map(s16_sin, round)

        self.mark_step     = self.lookup_size / (self.tmark/self.ts)
        self.mark_step_int = int(self.mark_step)
        self.mark_residue  = int((self.mark_step%1)*self.residue_size)

        self.space_step     = self.lookup_size / (self.tspace/self.ts)
        self.space_step_int = int(self.space_step)
        self.space_residue  = int((self.space_step%1)*self.residue_size)

        self.baud_step     = self.tbaud / self.ts
        self.baud_step_int = int(self.baud_step)
        self.baud_residue  = int((self.baud_step%1)*self.residue_size)

        self.markspace_residue_accumulator = 0
        self.baud_residue_accumulator = 0

        self.ts_index = 0
        self.baud_index = 0
        self.markspace_index = 0

        self.afsk_out = []

    def encode_bit_array(self, bit_array):
        for bit in bit_array:
            self.append_baud_period(markspace = bit)
    def encode_byte_array(self, byte_array):
        for idx in range(len(byte_array)*8):
            self.append_baud_period(markspace = byte_array[idx//8]&(0x80>>(idx%8)))

    def append_baud_period(self, markspace):
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
            self.afsk_out.append(self.sin_array[self.markspace_index%self.lookup_size])

            self.ts_index += 1 #increment one unit time step (ts = 1/fs)

class AX25():
    def __init__(self):
        self.bitarray = None

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

    def encode_ui_frame(self, src,
                              dst, 
                              digis,
                              info):

        #pre-allocate entire buffer size
        frame_len = AX25_ADDR_LEN +\
                    AX25_ADDR_LEN +\
                    len(digis)*AX25_ADDR_LEN+\
                    AX25_CONTROLPID_LEN+\
                    len(info)+\
                    AX25_CRC_LEN
        framebits_len = frame_len * 8
        frame = bytearray(frame_len + AX25_BITSTUFF_MARGIN)

        #create slices without copying
        mv    = memoryview(frame)

        #flags
        # frame[0] = 0x7e
        # frame[-1] = 0x7e

        idx = 0
        # destination Address  (note: opposite order in printed format)
        self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                             callsign = dst)
        idx += AX25_ADDR_LEN
        frame[idx-1]  |= 0xe0  #last bit of the addr
        # source Address
        self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                             callsign = src)
        idx += AX25_ADDR_LEN
        frame[idx-1]  |= 0xe0  #last bit of the addr
        # 0-8 Digipeater Addresses
        for digi in digis[:8]:
            self.encode_callsign(b_out    = mv[idx:idx+AX25_ADDR_LEN],
                                 callsign = digi)
            frame[idx-1]  |= 0x60  #last bit of the addr
            idx += AX25_ADDR_LEN
        frame[idx-1]  |= 0x01  #last bit of the addr
        frame[idx] = 0x03 #control
        idx += 1
        frame[idx] = 0xf0 #pid
        idx += 1

        #copy info
        frame[idx:idx+len(info)] = bytes(info,'utf')
        idx += len(info)

        #crc
        # print(len(frame),idx)
        crc_len = 2
        frame[idx:idx+crc_len] = bytearray(struct.pack('<H',crc16_ccit(mv[0:idx])))
        idx += crc_len

        # print(_.map(frame, lambda x: hex(x)))

        #revese bit order
        # print('reverse_bit_order')
        for idx in range(frame_len):
            frame[idx] = reverse_byte(frame[idx])
        # print(_.map(frame, lambda x: hex(x)))

        #create bit array from input bits + CRC
        self.bitarray = bytearray(len(frame)*8)

        # for idx in range(len(self.bitarray)):
            # if idx < len(frame)*8:
                # #input bytes
                # self.bitarray[idx] = 1 if frame[idx//8] & (0x80>>(idx%8)) else 0

        # stuff bits in place
        # update the total number of bits
        framebits_len = self.do_bitstuffing(mv, 
                                            start_bit = 0, 
                                            stop_bit = framebits_len):
        # self.bitarray = self.do_bitstuffing(self.bitarray)

        #convert to nrzi
        self.bitarray = self.convert_nrzi(self.bitarray)

    def do_bitstuffing(self, mv, start_bit, stop_bit):
        #bit stuff frame in place
        idx = start_bit
        cnt = 0
        while idx < stop_bit:
            if mv[idx//8] & (0x80>>(idx%8)):
                cnt += 1
            else:
                cnt = 0
            idx += 1
            if cnt == 5:
                #stuff a bit
                #shift all bytes to the right, starting next byte
                self.shift_bytes_right(mv, start_bit = idx//8+1)
                self.split_shift_byte(mv, idx)
                cnt = 0
                stop_bit += 1 #
                idx += 1
        return stop_bit

    def shift_bytes_right(self, mv, start_byte, stop_byte=None):
        if not stop_byte:
            stop_byte = len(mv)
        for idx in range(stop_byte-1, start_byte-1, -1):
            mv[idx] = mv[idx]>>1 | (mv[idx-1]&0x80)

    def split_shift_byte(self, mv, idx):
        #right side
        t_shift = mv[idx//8] & (0xff>>(idx%8))
        t_shift = t_shift >> 1
        #left side
        mv[idx//8] = mv[idx//8] & (0xff<<((8-idx)%8))
        #combine, 0 (stuffed bit), left in center
        mv[idx//8] = mv[idx//8] | t_shift


    # def do_bitstuffing(self, bitarray):
        # # print('do_bitstuffing')
        # idx = 0
        # bitstuff_counter = 0
        # while idx < len(bitarray):
            # if bitarray[idx]:
                # bitstuff_counter += 1
            # else:
                # bitstuff_counter = 0
            # idx += 1
            # if bitstuff_counter == 5:
                # bitarray.insert(idx,0)
                # bitstuff_counter = 0
                # idx += 1
        # # print(bitarray)
        # return bitarray
    
    def convert_nrzi(self, bitarray):
        current = 1
        for idx in range(len(bitarray)):
            if bitarray[idx] == 0:
                bitarray[idx] = 0 if current else 1
                current = bitarray[idx]
            else:
                bitarray[idx] = current
            bitarray[idx] = 0 if bitarray[idx] else 1 
        return bitarray


afsk = AFSK(sampling_rate = args.rate)

# bit_array = []
# byte_array = b'Hello'
# for idx in range(len(byte_array)*8):
    # bit_array.append(byte_array[idx//8]&(0x80>>(idx%8)))
# afsk.encode_bit_array(bit_array = bit_array)
# for b in afsk.afsk_out:
    # print('{},'.format(b//10),end='')
# print('')
# exit()


ax25 = AX25()
#"KI5TOF>WORLD:>hello"
#'FROMCALL>TOCALL:>status text'
frame = ax25.encode_ui_frame(src   = 'KI5TOF',
                             dst   = 'WORLD',
                             digis = [],
                             info  = '>hello sara')
# 0.236
#bit 55 is where gold/test mismatch
# exit()

for _b in range(int(0.0265/(1.0/args.rate))+1):
    if not verbose:
        sys.stdout.buffer.write(b'\x00\x00')

afsk.encode_byte_array(byte_array = bytearray([AX25_FLAG_NRZI]*32))
# afsk.encode_bit_array(bit_array = b'\x01\x01\x01\x01\x01\x01\x01\x00')
for b in afsk.afsk_out:
    _b = struct.pack('<h', (b//AFSK_SCALE))
    if not verbose:
        sys.stdout.buffer.write(_b)
afsk.afsk_out = []

# afsk.encode_bit_array(bit_array = b'\x01\x01\x01\x01\x01\x01\x01\x00')
afsk.encode_byte_array(byte_array = bytearray([AX25_FLAG_NRZI]))
for b in afsk.afsk_out:
    _b = struct.pack('<h', (b//AFSK_SCALE))
    if not verbose:
        sys.stdout.buffer.write(_b)
afsk.afsk_out = []

afsk.encode_bit_array(bit_array = ax25.bitarray)
for b in afsk.afsk_out:
    _b = struct.pack('<h', (b//AFSK_SCALE))
    if not verbose:
        sys.stdout.buffer.write(_b)
afsk.afsk_out = []

# afsk.encode_bit_array(bit_array = b'\x01\x01\x01\x01\x01\x01\x01\x00')
afsk.encode_byte_array(byte_array = bytearray([AX25_FLAG_NRZI]))
for b in afsk.afsk_out:
    _b = struct.pack('<h', (b//AFSK_SCALE))
    if not verbose:
        sys.stdout.buffer.write(_b)
afsk.afsk_out = []

# afsk.encode_bit_array(bit_array = b'\x01\x01\x01\x01\x01\x01\x01\x00'*1)
afsk.encode_byte_array(byte_array = bytearray([AX25_FLAG_NRZI]))
for b in afsk.afsk_out:
    _b = struct.pack('<h', (b//AFSK_SCALE))
    if not verbose:
        sys.stdout.buffer.write(_b)
afsk.afsk_out = []

