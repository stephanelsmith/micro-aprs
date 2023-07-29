
import sys
import io
import asyncio
import struct
from array import array

# from asyncio import Queue

from ax25.ax25 import AX25
from ax25.func import reverse_bit_order
from ax25.func import trim_frame
from ax25.func import unstuff
from ax25.defs import DecodeError
from ax25.defs import DecodeErrorNoFix
from ax25.defs import DecodeErrorFix

import lib.upydash as _
from lib.utils import pretty_binary
from lib.utils import int_div_ceil
from lib.utils import assign_bit
from lib.utils import eprint

from lib.compat import print_exc

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7
AX25_MIN_BITS  = 160

class AX25FromAFSK():
    def __init__(self, bits_in_q,
                       ax25_q,
                       ax25_crc_err_q = None,
                       verbose        = False):
        self.bits_q = bits_in_q
        self.ax25_q = ax25_q
        self.ax25_crc_err_q = ax25_crc_err_q
        self.verbose = verbose

        # self.frames_q = Queue()
        self.tasks = []

    async def __aenter__(self):
        self.tasks.append(asyncio.create_task(self.delimin_coro()))
        return self

    async def __aexit__(self, *args):
        _.for_each(self.tasks, lambda t: t.cancel())
        await asyncio.gather(*self.tasks, return_exceptions=True)

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
            while True:
                b = await self.bits_q.get()
                inb[idx//8] = assign_bit(inb[idx//8], idx, b)
                idx += 1
                if b == 0 and flgcnt == 6:
                    #detected ax25 frame flag
                    #a valid AX25 frame is at minimum 160 bites (20 bytes) long
                    if idx >= AX25_MIN_BITS:
                        if self.verbose:
                            eprint('frame')
                        await self.frame_to_ax25(bytearray(mv[:int_div_ceil(idx,8)]), idx)
                    mv[0] = AX25_FLAG #keep the frame flag that we detected in buffer
                    idx = 8
                flgcnt = flgcnt + 1 if b else 0
                if idx == inbsize:
                    idx = 0
                self.bits_q.task_done()
        except Exception as err:
            print_exc(err)

    async def frame_to_ax25(self, buf, stop_bit):
        mv = memoryview(buf)
        if self.verbose:
            print('===== DEMOD frame ======')
            pretty_binary(mv)

        #unstuff
        unstuff(mv, stop_bit)
        if self.verbose:
            print('-un-stuffed-')
            pretty_binary(mv)

        #reverse bit order
        reverse_bit_order(mv)
        # mv = trim_frame(mv)
        if self.verbose:
            print('-un-reversed (ax25)-')
            pretty_binary(mv)

        #decode
        try:
            ax25 = AX25(frame = mv)
            await self.ax25_q.put(ax25)
            return
        except DecodeErrorNoFix as err:
            return
        except DecodeErrorFix as err:
            _ax25 = err.ax25

        #try fixing src/dst
        ax25 = self.fixer_src_dst(mv = mv)
        if ax25:
            await self.ax25_q.put(ax25)
            return

        #no src/dst, don't bother additional fixing
        #this way we avoid trying to fix messages that have no chance of fixing
        if not (_ax25.src and _ax25.src.is_valid()) or\
           not (_ax25.dst and _ax25.dst.is_valid()):
            return

        #try fixing info/rest of message
        ax25 = self.fixer_info(mv = mv)
        if ax25:
            await self.ax25_q.put(ax25)
            return

        return

    def fixer_src_dst(self, mv):

        flip = self.flip
        lbits = 8*len(mv)

        #try fixing src/dst
        # print(1)
        for flip_a in range(8,8+8*(AX25_ADDR_LEN*2)):
            for flip_b in range(flip_a,8+8*(AX25_ADDR_LEN*2)):
                if flip_a >= lbits or flip_b >= lbits:
                    continue
                try:
                    flip(mv, flip_a, flip_b)
                    ax25 = AX25(frame = mv)
                    if ax25.src.is_valid() and ax25.dst.is_valid():
                        print('FIXED src/dst')
                        return ax25
                    else:
                        flip(mv, flip_a, flip_b)
                except DecodeErrorFix as err:
                    pass
                flip(mv, flip_a, flip_b)


    def fixer_info(self, mv):

        flip = self.flip
        lbits = 8*len(mv)

        #try fixing rest of message
        for flip_a in range(8+8*(AX25_ADDR_LEN*2), 8*(len(mv)-3)):
            for flip_b in range(flip_a,8*(len(mv)-3)):
                if flip_a >= lbits or flip_b >= lbits:
                    continue
                try:
                    flip(mv, flip_a, flip_b)
                    ax25 = AX25(frame = mv)
                    print('FIXED info')
                    return ax25
                except DecodeErrorFix as err:
                    pass
                flip(mv, flip_a, flip_b)

    def flip(self, frame, flip_a, flip_b):
        idx = flip_a//8
        bit = flip_a%8
        frame[idx] = frame[idx] ^ (0x80>>bit)
        if flip_a != flip_b:
            idx = flip_b//8
            bit = flip_b%8
            frame[idx] = frame[idx] ^ (0x80>>bit)

