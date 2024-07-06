
import sys
import math
import asyncio
import lib.upydash as _
from array import array

from array import array

from lib.utils import eprint

from afsk.sin_table import get_sin_table
from afsk.func import gen_bits_from_bytes
from afsk.func import create_nrzi

AFSK_SCALE_DOWN = 2 
AX25_FLAG       = 0x7e
AFSK_Q_SIZE     = 22050


class AFSKModulator():

    def __init__(self, sampling_rate = 22050,
                       afsk_q        = None,
                       verbose       = False,):
        self.verbose = verbose 
        self.afsk_q = afsk_q

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
        self.sintbl = get_sin_table(size = self.sintbl_sz)

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
        await self.zero_padding()
        return self

    async def __aexit__(self, *args):
        #zero-pad
        await self.zero_padding()

    async def zero_padding(self):
        zpad_ms = 1
        siz = int(zpad_ms/1000/self.ts)
        await self.afsk_q.put( (
            array('i',[0 for x in range(siz)]), 
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
            flags[i] = AX25_FLAG
        await self.to_samples(afsk     = flags,
                              stop_bit = count*8)

    async def to_samples(self, afsk, #bytes
                               stop_bit,
                               # zpad_ms = 0,
                               ):
        arr = array('i', range(AFSK_Q_SIZE))
        idx = 0

        nrzi_dbg_i = 0

        nrzi = self.nrzi
        afsk_q_put = self.afsk_q.put
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
                    arr[idx] = sample//AFSK_SCALE_DOWN
                    idx += 1
                    if idx == AFSK_Q_SIZE:
                        await afsk_q_put((arr, idx))
                        arr = array('i', range(AFSK_Q_SIZE))
                        idx = 0

            await afsk_q_put((arr, idx))

            if verbose:
                eprint('\n')
        except Exception as err:
            traceback.print_exc()

