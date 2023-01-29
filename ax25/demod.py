
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


class BitStreamToAX25():
    def __init__(self, ):
        self.tasks = []

    async def delimin_coro(self):
        # We receive a stream of 1s and 0s from bits_q, this function
        # will find/chunk the bitstream delminiated by the AX25 flags
        # output: (bytearray, num_bits) is sent to frame_q
        try:
            inbsize = 2024
            inb = bytearray(inbsize)
            mv = memoryview(inb)
            idx = 0
            flgcnt = 0
            unnrzi = self.create_unnrzi()
            while True:
                _b = await self.bits_q.get()
                #UN NRZI, it's better to do it here since
                # - easy to detect the AX25 flags decoded (they can be flipped in NRZI)
                # - ideally done with closure
                b = unnrzi(_b)
                # print(b,end='')
                inb[idx//8] = assign_bit(inb[idx//8], idx, b)
                idx += 1
                if b == 0 and flgcnt == 6:
                    #detected ax25 frame flag
                    if idx//8 > 2: 
                        await self.frame_q.put((bytearray(mv[:int_div_ceil(idx,8)]), idx))
                    mv[0] = AX25_FLAG #keep the frame flag that we detected in buffer
                    idx = 8
                flgcnt = flgcnt + 1 if b else 0
                if idx == inbsize:
                    idx = 0
        except Exception as err:
            traceback.print_exc()

    def create_unnrzi(self):
        c = 1
        def inner(b):
            nonlocal c
            if b != c:
                c = b
                return 0
            else:
                c = b
                return 1
        return inner

    def unstuff(self, mv, stop_bit):
        #look for 111110, remove the 0
        c = 0
        for idx in range(stop_bit):
            mask = (0x80>>(idx%8))
            b = (mv[idx//8] & mask) >> ((8-idx-1)%8) #pick bit
            if b == 0 and c == 5:
                #detected stuffed bit, remove it
                shift_in = self.shift_bytes_left(mv, idx//8+1)
                self.remove_bit_shift_from_right(mv, idx, shift_in)
                c = 0
            c = c+b if b==1 else 0

    def remove_bit_shift_from_right(self, mv, idx, shift_in=0):
        if idx%8 == 7:
            #the bit is far right, just apply shift_in
            pass
        else:
            #we need to split at specific bit index position
            #get the portion that's getting shifted
            rmask = 0xff >> (idx%8)
            lmask = rmask ^ 0xff
            mv[idx//8] = (lmask & mv[idx//8]) | (((mv[idx//8]&rmask)<<1)&0xff)
        if shift_in:
            mv[idx//8] |= 0x01
        else:
            mv[idx//8] &= (0x01 ^ 0xff)

    def shift_bytes_left(self, mv, start_byte):
        l = 0x00
        #idx iterating byte index
        for idx in range(len(mv)-1,start_byte-1, -1):
            #work from right to left
            t = 0x80 & mv[idx] #save bit shifted out
            mv[idx] = (mv[idx]<<1)&0xff
            mv[idx] = mv[idx] | 0x01 if l else mv[idx] #shift l
            l = t # store shifted bit for next iteration
        return l

    def reverse_bit_order(self, mv):
        for idx in range(len(mv)):
            mv[idx] = reverse_byte(mv[idx])

    async def frame_coro(self, debug = True):
        try:
            while True:
                buf,stop_bit = await self.frame_q.get()
                mv = memoryview(buf)
                if debug:
                    print('-afsk ax25 deliminated bits-')
                    pretty_binary(mv)

                #unstuff
                self.unstuff(mv, stop_bit)
                if debug:
                    print('-un-stuffed-')
                    pretty_binary(mv)

                #reverse bit order
                self.reverse_bit_order(mv)
                if debug:
                    print('-un-reversed-')
                    pretty_binary(mv)

                #decode
                ax25 = AX25(ax25 = mv)
                if debug:
                    print('-ax25 decoded-')
                    print(ax25)

        except Exception as err:
            traceback.print_exc()

