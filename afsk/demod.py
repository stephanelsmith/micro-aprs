
import sys
import asyncio
import traceback
from array import array
import math
from pydash import py_ as _

# import matplotlib.pyplot as plt

from lib.utils import frange
import lib.defs as defs
from lib.utils import eprint

from afsk.func import create_unnrzi
from afsk.func import create_agc
from afsk.func import create_corr
from afsk.func import create_lpf
from afsk.func import create_bandpass
from afsk.func import create_sampler

class AFSKDemodulator():
    def __init__(self, samples_in_q,
                       bits_out_q,
                       sampling_rate = 22050,
                       verbose       = False):

        self.samples_q  = samples_in_q
        self.bits_q = bits_out_q
        self.verbose = verbose

        self.fmark = 1200
        self.tmark = 1/self.fmark
        self.fspace = 2200
        self.tspace = 1/self.fspace
        self.fs = sampling_rate
        self.ts = 1/self.fs
        self.fbaud = 1200
        self.tbaud = 1/self.fbaud

        nmark = int(self.tmark/self.ts)
        ncoefsbaud = 4
        band_ncoefs = int(nmark*ncoefsbaud) if int(nmark*ncoefsbaud)%2==1 else int(nmark*ncoefsbaud)+1
        self.band = create_bandpass(ncoefs = band_ncoefs,
                                    fmark  = self.fmark,
                                    fspace = self.fspace,
                                    fs     = self.fs)
        self.agc = create_agc(sp = 2**12,
                              depth = int(self.tbaud/self.ts),
                              )
        self.corr = create_corr(ts    = self.ts,
                                shift = 1)

        nmark = int(self.tmark/self.ts)
        ncoefsbaud = 2
        lpf_ncoefs = int(nmark*ncoefsbaud) if int(nmark*ncoefsbaud)%2==1 else int(nmark*ncoefsbaud)+1
        self.lpf = create_lpf(ncoefs = lpf_ncoefs,
                              fa     = 1200,
                              fs     = self.fs)
        self.sampler = create_sampler(fbaud = self.fbaud,
                                  fs    = self.fs)
        self.unnrzi = create_unnrzi()

        #how much we need to flush internal filters to process all sampled data
        self.flush_size = int((lpf_ncoefs+band_ncoefs)*(self.tbaud/self.ts))

        self.tasks = []

    async def __aenter__(self):
        self.tasks.append(asyncio.create_task(self.process_samples()))
        return self

    async def __aexit__(self, *args):
        _.for_each(self.tasks, lambda t: t.cancel())
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def process_samples(self):
        try:
            # Process a chunk of samples
            corr    = self.corr
            agc     = self.agc
            lpf     = self.lpf
            band    = self.band
            sampler = self.sampler
            unnrzi  = self.unnrzi
            self.o = array('i', (0 for x in range(defs.SAMPLES_SIZE)))
            o = self.o
            self.bs = array('i', (0 for x in range(defs.SAMPLES_SIZE)))
            bs = self.bs

            bits_q = self.bits_q
            samp_q = self.samples_q

            while True:
                #fetch next chunk of samples (array)
                arr,arr_size = await samp_q.get()

                if self.verbose:
                    eprint('processing samples',arr_size)

                for i in range(arr_size):
                    o[i] = arr[i]
                    o[i] = band(o[i])
                    # o[i] = agc(o[i])
                    o[i] = corr(o[i])
                    o[i] = lpf(o[i])
                    bs[i] = sampler(o[i])
                    if bs[i] != 2: # _NONE
                        b = unnrzi(bs[i])
                        # eprint(b,end='')
                        await bits_q.put(b) #bits_out_q
                samp_q.task_done() # done
        except Exception as err:
            traceback.print_exc()

    def analyze(self,start_from = 100e-3):
        o = self.o
        m   = max([max(o),abs(min(o))])
        sca = m//(2**8)
        st = int(start_from/self.ts)
        while o[st-1]<0 and o[st] >= 0:
            st+=1
        bstp = self.tbaud/self.ts
        ibaud = int(bstp)
        st = st - int(bstp/4) # clk sample (center of eye)
        eye     = {'l':None,'r':None,'u':None,'d':None} #TODO use array lookup
        booleye = {'l':False,'r':False,} #TODO use array lookup
        for x in frange(st, len(o)-ibaud, bstp):
            ci = round(x)
            r = int(3*ibaud/4) #eye scan range
            #plt.plot(list(range(-r,r)), [v//sca for v in o[ci-r:ci+r]])

            #eye u/d
            if o[ci] > 0:
                eye['u'] = eye['u'] if eye['u'] and eye['u'] < o[ci]//sca else o[ci]//sca
            else:
                eye['d'] = eye['d'] if eye['d'] and eye['d'] > o[ci]//sca else o[ci]//sca

            #eye l/r
            for k in booleye:
                booleye[k] = True
            for e in range(r):
                if booleye['l'] and\
                   (o[ci-e] > 0 and o[ci-e-1] <= 0 or\
                    o[ci-e] < 0 and o[ci-e-1] >= 0):
                    eye['l'] = eye['l'] if eye['l'] and eye['l'] > -e else -e
                    booleye['l'] = False
                if booleye['r'] and\
                   (o[ci+e] > 0 and o[ci+e+1] <= 0 or\
                   o[ci+e] < 0 and o[ci+e+1] >= 0):
                    eye['r'] = eye['r'] if eye['r'] and eye['r'] < +e else +e
                    booleye['r'] = False
                if not booleye['r'] and not booleye['l']:
                    break
        eprint(eye)
        # plt.show()

