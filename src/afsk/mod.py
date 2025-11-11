
import sys
import math
import asyncio

from array import array

import lib.upydash as _
from lib.compat import Queue

from lib.utils import eprint
from lib.compat import const

from afsk.func import create_afsk_tone_gen
from afsk.func import gen_bits_from_bytes
from afsk.func import create_nrzi

# _AFSK_SCALE_DOWN = const(1)
_AX25_FLAG       = const(0x7e)
_AFSK_Q_SIZE     = const(22050//10) # internal q size


class AFSKModulator():

    def __init__(self, sampling_rate = 22050,
                       signed        = True,
                       amplitude     = 0x7fff,
                       is_square     = False,  # generate a square instead of sine
                       verbose       = False,
                       ):

        self.verbose = verbose 
        self.signed  = signed
        self._q      = Queue() # internal queue
        self.arr_t  = 'h' if signed else 'H'

        self.fs = sampling_rate
        self.ts = 1/self.fs
        self.afsk_tone_gen = create_afsk_tone_gen(fs     = self.fs,
                                                  afsks  = [2200, 1200],
                                                  signed = self.signed,
                                                  ampli  = amplitude,
                                                  baud   = 1200,
                                                  )
        #nrzi converter
        self.nrzi = create_nrzi()

    async def __aenter__(self):
        #zero-pad
        return self

    async def __aexit__(self, *args):
        pass

    async def pad_zeros(self, ms=1, bias=None):
        siz = int(ms/1000/self.ts)
        v = 0
        if not self.signed:
            v = 0x7FFF
        if bias != None:
            v = bias
        await self._q.put( (
            array(self.arr_t,[v for x in range(siz)]), 
            siz
        ))

    async def send_flags(self, count):
        # initial flags
        flags = bytearray(count)
        for i in range(count):
            flags[i] = _AX25_FLAG
        await self.to_samples(afsk     = flags,
                              stop_bit = count*8)

    async def to_samples(self, afsk, #bytes
                               stop_bit,
                               ):
        arr = array(self.arr_t, (0 for i in range(_AFSK_Q_SIZE)))
        idx = 0

        nrzi_dbg_i = 0

        nrzi = self.nrzi
        _q_put = self._q.put
        # gen_samples = self.gen_baud_period_samples
        gen_samples = self.afsk_tone_gen
        verbose = self.verbose

        try:

            if verbose:
                eprint('--nrzi--', 'bits',stop_bit, 'bytes',stop_bit//8,'remain',stop_bit%8)

            for b in gen_bits_from_bytes(mv       = afsk,
                                        stop_bit = stop_bit):

                #convert nrzi
                b = nrzi(b)

                if verbose:
                    nrzi_dbg_i += 1
                    eprint(b,end=' ' if nrzi_dbg_i%8==0 else '')
                    if nrzi_dbg_i%80==0:
                        eprint('')

                for sample in gen_samples(b):
                    arr[idx] = sample#//_AFSK_SCALE_DOWN
                    idx += 1
                    if idx == _AFSK_Q_SIZE:
                        await _q_put((arr, idx))
                        arr = array(self.arr_t, (0 for i in range(_AFSK_Q_SIZE)))
                        idx = 0

            await _q_put((arr, idx))

            if verbose:
                eprint('\n')
        except Exception as err:
            traceback.print_exc()

    # return the array and size
    async def flush(self):
        ls = []
        s = 0
        while not self._q.empty():
            a_s = await self._q.get() # array,size
            ls.append(a_s)
            s += a_s[1]
        arr = array(self.arr_t, range(s))
        s = 0
        for a_s in ls:
            arr[s:s+a_s[1]] = a_s[0]
            s += a_s[1]
        return arr,s

