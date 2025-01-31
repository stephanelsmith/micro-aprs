
import sys
import math
import asyncio

from array import array

import lib.upydash as _
from lib.compat import Queue

from lib.utils import eprint
from lib.compat import const

from afsk.sin_table import get_sin_table
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

        self.fmark = 1200
        self.tmark = 1/self.fmark
        self.fspace = 2200
        self.tspace = 1/self.fspace
        self.fs = sampling_rate
        self.ts = 1/self.fs
        self.fbaud = 1200
        self.tbaud = 1/self.fbaud
        self.residue_size = 10000

        #pre-compute sine table
        self.sintbl_sz = 1024
        self.sintbl = get_sin_table(size    = self.sintbl_sz,
                                    signed  = signed,
                                    ampli   = amplitude,
                                    square  = is_square,
                                    )

        #get step sizes (integer and residue)
        mark_step     = self.sintbl_sz / (self.tmark/self.ts)
        self.mark_step_int = int(mark_step)
        self.mark_residue  = int((mark_step%1)*self.residue_size)

        space_step     = self.sintbl_sz / (self.tspace/self.ts)
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
            self.markspace_residue_accumulator %= self.markspace_residue_accumulator
            
            #push the next point to the waveform
            yield self.sintbl[self.markspace_index%self.sintbl_sz]

            self.ts_index += 1 #increment one unit time step (ts = 1/fs)

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
        gen_samples = self.gen_baud_period_samples
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

