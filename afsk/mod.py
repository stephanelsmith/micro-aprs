
import sys
import math
import asyncio
from pydash import py_ as _
import struct

from array import array
from lib.utils import frange

from afsk.func import gen_bits_from_bytes

AFSK_SCALE     = 50

class AFSKModulator():

    def __init__(self, sampling_rate = 22050,
                       verbose       = False,):
        self.verbose = verbose 

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

        self.tasks = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        _.for_each(self.tasks, lambda t: t.cancel())
        await asyncio.gather(*self.tasks, return_exceptions=True)


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


    async def to_samples(self, ax25,
                         stop_bit,
                         afsk_q,
                         ):
        for bit in gen_bits_from_bytes(mv       = ax25,
                                       stop_bit = stop_bit):
            for sample in self.gen_baud_period_samples(bit):
                await afsk_q.put(sample//AFSK_SCALE)


    # def dump_ax25_raw_samples(self, ax25,
                                    # zpad_ms,
                                    # out_type):
        # o = []
        # #zero padding
        # for b in range(int(zpad_ms/self.ts+1)):
            # o.append(0)

        # #write data
        # for bit in gen_bits_from_bytes(mv       = ax25.frame,
                                       # stop_bit = ax25.frame_len_bits):
            # for sample in self.gen_baud_period_samples(bit):
                # o.append(sample//AFSK_SCALE)

        # if out_type == 'raw':
            # buf = bytearray(len(o)*2)
            # for i,s in enumerate(o):
                # x = struct.pack('<h', s)
                # # x = int.to_bytes(s, 2, 'little', signed=True)
                # buf[i*2]   = x[0]
                # buf[i*2+1] = x[1]
            # sys.stdout.buffer.write(buf)
        # else:
            # print('type not implemented', out_type)

