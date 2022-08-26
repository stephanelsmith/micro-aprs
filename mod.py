
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

    def encode_ui_frame(self, _from,
                              to, 
                              digipeaters,
                              info):
        b =  bytearray()
        _from = _form.split('-')

    def decode_frame(self, bytes_in)
        pass

    def encode_bytes(self, bytes_in):
        # print('encode_bytes')

        # print(' '.join(_.map(bytes_in,hex)))

        #revese bit order
        # print('reverse_bit_order')
        bytes_in = self.reverse_bit_order(bytes_in)
        # print(' '.join(_.map(bytes_in,hex)))

        #crc
        crc = bytearray(struct.pack('>H',crc16_ccit(bytes_in)))
        # print('crc',' '.join(_.map(crc,hex)))

        #create bit array from input bits + CRC
        self.bitarray = bytearray(len(bytes_in)*8 + 2*8)

        for idx in range(len(self.bitarray)):
            if idx < len(bytes_in)*8:
                #input bytes
                # self.bitarray[idx] = bytes_in[idx//8] & (0x01<<(idx%8))
                self.bitarray[idx] = 1 if bytes_in[idx//8] & (0x80>>(idx%8)) else 0
            else:
                #crc
                crc_idx = idx - len(bytes_in)*8
                self.bitarray[idx] = 1 if crc[crc_idx//8] & (0x80>>(crc_idx%8)) else 0
        # print(self.bitarray)

        #stuff bits
        self.bitarray = self.do_bitstuffing(self.bitarray)

        #add flags
        flag = bytearray([0,1,1,1,1,1,1,0])
        self.bitarray = flag + self.bitarray + flag

        # self.print_bytes(self.bitarray)

        #convert to nrzi
        self.bitarray = self.convert_nrzi(self.bitarray)

    # def print_bytes(self, bitarray):
        # if len(bitarray)%8 != 0:
            # return
        # _bytes = bytearray(len(bitarray)//8)
        # for byteidx in range(len(bitarray)//8):
            # for bitidx in range(8):
                # _bytes[byteidx] += (0x80>>bitidx) if bitarray[byteidx*8+bitidx] else 0
        # print(' '.join(_.map(_bytes,hex)))

    def reverse_byte(self, _byte):
        #xor reverse bit technique
        _byte = ((_byte & 0x55) << 1) | ((_byte & 0xAA) >> 1);
        _byte = ((_byte & 0x33) << 2) | ((_byte & 0xCC) >> 2);
        _byte = ((_byte & 0x0F) << 4) | ((_byte & 0xF0) >> 4);
        return _byte

    def reverse_bit_order(self, _bytes):
        idx = 0
        while idx < len(_bytes):
            _bytes[idx] = self.reverse_byte(_bytes[idx])
            idx += 1
        return _bytes

    def do_bitstuffing(self, bitarray):
        # print('do_bitstuffing')
        idx = 0
        bitstuff_counter = 0
        while idx < len(bitarray):
            if bitarray[idx]:
                bitstuff_counter += 1
            else:
                bitstuff_counter = 0
            idx += 1
            if bitstuff_counter == 5:
                bitarray.insert(idx,0)
                bitstuff_counter = 0
                idx += 1
        # print(bitarray)
        return bitarray
    
    def convert_nrzi(self, bitarray):
        # print('convert_nrzi')
        # print(bitarray)
        current = 1
        for idx in range(0,len(bitarray)):
            # prev = bitarray[idx-1]
            if bitarray[idx]:
                bitarray[idx] = current
            else:
                bitarray[idx] = 0 if current else 1
            current = bitarray[idx]
        # print(bitarray)
        return bitarray

ax25 = AX25()

h = encode_frame(aprs = 'W2FS-4>CQ,RELAY:Test')
#"KI5TOF>WORLD:>hello"
#'FROMCALL>TOCALL:>status text'
exit()

afsk = AFSK(sampling_rate = args.rate)

for _b in range(int(0.0265/(1.0/args.rate))+1):
    if not verbose:
        sys.stdout.buffer.write(b'\x00\x00')

afsk.encode_bit_array(bit_array = bytearray(33*8))
for b in afsk.afsk_out:
    _b = struct.pack('<h', (b//12))
    if not verbose:
        sys.stdout.buffer.write(_b)

afsk.afsk_out = []

ax25.encode_bytes(bytes_in=[0xAE,0x9E,0xA4,0x98,0x88,0x40,0xE0,0x96,0x92,0x6A,0xA8,0x9E,0x8C,0x61,0x03,0xF0,0x3A,0x68,0x65,0x6C,0x6C,0x6F,0x20,0x77,0x6F,0x72,0x6C,0x64])
afsk.encode_bit_array(bit_array = ax25.bitarray)
for b in afsk.afsk_out:
    _b = struct.pack('<h', (b//8))
    if not verbose:
        sys.stdout.buffer.write(_b)
