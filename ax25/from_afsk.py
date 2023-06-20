
import sys
import io
import asyncio
import struct
import traceback
from array import array

from asyncio import Queue

from ax25.ax25 import AX25
from ax25.func import reverse_bit_order
from ax25.func import unstuff
from ax25.defs import DecodeError
from ax25.defs import CRCError

import lib.upydash as _
from lib.utils import pretty_binary
from lib.utils import int_div_ceil
from lib.utils import assign_bit
from lib.utils import eprint

AX25_FLAG      = 0x7e
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

        self.frames_q = Queue()
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
            traceback.print_exc()


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
        if self.verbose:
            print('-un-reversed-')
            pretty_binary(mv)

        #decode
        try:
            ax25 = AX25(frame = mv)
        except DecodeError as err:
            if self.verbose:
                eprint(str(err))
            return
        except CRCError as err:
            await self.ax25_crc_err_q.put(err.ax25)
            return
        except:
            traceback.print_exc()
            return
