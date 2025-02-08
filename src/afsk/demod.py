
import sys
import struct
import asyncio
from array import array
import math
import lib.upydash as _
from asyncio import Event

from lib.utils import eprint
from lib.memoize import memoize_loads
from lib.memoize import memoize_dumps
from lib.compat import Queue

from afsk.func import create_unnrzi
from afsk.func import create_corr
from afsk.func import lpf_fir_design
from afsk.func import bandpass_fir_design
from afsk.func import create_sampler
from afsk.func import create_fir
from afsk.func import create_power_meter
from afsk.func import clamps16
from afsk.fir_options import fir_options
from afsk.func import bu16toi, bs16toi

from lib.compat import print_exc

_FMARK  = 1200
_FSPACE = 2200
_TMARK  = 0.0008333333333333334
_FBAUD  = 1200
_TBAUD  = 0.0008333333333333334

class AFSKDemodulator():
    def __init__(self, in_rx, # array or tuple (array, size) OR a stream (with 'readexactly' method)
                       bits_out_q,
                       sampling_rate = 11_025,
                       verbose       = False, # output intermediate steps to stderr
                       stream_type   = 's16', # if in_rx is a stream, u16 or s16?
                       options       = {},
                       ):
                       # debug_samples = False, # output intermediate samples to stderr

        self.in_rx  = in_rx
        self.bits_q = bits_out_q
        self.verbose = verbose
        self.stream_type = stream_type
        # self.debug_samples = debug_samples
        self.stream_done = Event()

        self.fs = sampling_rate
        self.ts = 1/self.fs
        
        do_memoize = True
        options = dict(fir_options,  **options)
        nmark = int(_TMARK/self.ts)

        bandpass_ncoefsbaud = options['bandpass_ncoefsbaud']
        bandpass_ncoefs = int(nmark*bandpass_ncoefsbaud) if int(nmark*bandpass_ncoefsbaud)%2==1 else int(nmark*bandpass_ncoefsbaud)+1
        bandpass_width = options['bandpass_width']
        bandpass_amark = options['bandpass_amark']
        bandpass_aspace = options['bandpass_aspace']
        coefs_g = memoize_loads('bpf', _FMARK, _FSPACE, self.fs, 
                                       bandpass_ncoefs,
                                       bandpass_width, 
                                       bandpass_amark, 
                                       bandpass_aspace)
        if coefs_g:
            coefs,g = coefs_g
        else: 
            coefs,g = bandpass_fir_design(ncoefs = bandpass_ncoefs,
                                          fmark  = _FMARK,
                                          fspace = _FSPACE,
                                          fs     = self.fs,
                                          width  = bandpass_width,
                                          amark  = bandpass_amark,
                                          aspace = bandpass_aspace,
                                          )
            memoize_dumps('bpf', (coefs,g), _FMARK, _FSPACE, self.fs,
                                        bandpass_ncoefs,
                                        bandpass_width, 
                                        bandpass_amark, 
                                        bandpass_aspace)
        self.bpf = create_fir(coefs = coefs, scale = g)

        self.corr = create_corr(ts    = self.ts,)

        # nmark = int(_TMARK/self.ts)
        lpf_ncoefsbaud = options['lpf_ncoefsbaud']
        lpf_ncoefs = int(nmark*lpf_ncoefsbaud) if int(nmark*lpf_ncoefsbaud)%2==1 else int(nmark*lpf_ncoefsbaud)+1
        lpf_width = options['lpf_width']
        lpf_aboost = options['lpf_aboost']
        lpf_f = options['lpf_f']
        if do_memoize:
            coefs_g = memoize_loads('lpf', lpf_f, self.fs, 
                                           lpf_ncoefs, 
                                           lpf_width, 
                                           lpf_aboost)
        else:
            coefs_g = None
        if coefs_g:
            coefs,g = coefs_g
        else: 
            coefs,g = lpf_fir_design(ncoefs = lpf_ncoefs,
                                     fa     = lpf_f,
                                     fs     = self.fs,
                                     width  = lpf_width,
                                     aboost = lpf_aboost,
                                     )
            if do_memoize:
                memoize_dumps('lpf', (coefs,g), lpf_f, self.fs,
                                            lpf_ncoefs, 
                                            lpf_width, 
                                            lpf_aboost)
        self.lpf = create_fir(coefs = coefs, scale = g)

        self.sampler = create_sampler(fbaud = _FBAUD,
                                      fs    = self.fs)
        self.unnrzi = create_unnrzi()

        self.pwrmtr = create_power_meter(siz = nmark*2)
        self.squelch = options['squelch']

        #how much we need to flush internal filters to process all sampled data
        self.flush_size = int((lpf_ncoefs+bandpass_ncoefs)*(_TBAUD/self.ts))

        self.tasks = []

    async def __aenter__(self):
        if isinstance(self.in_rx, Queue):
            self.tasks.append(asyncio.create_task(self.q_core()))
        elif hasattr(self.in_rx, 'readexactly') or hasattr(self.in_rx, 'read'):
            self.tasks.append(asyncio.create_task(self.stream_core()))
        else:
            raise Exception('unknown in_rx format')
        return self

    async def __aexit__(self, *args):
        # _.for_each(self.tasks, lambda t: t.cancel())
        map(lambda t: t.cancel(), self.tasks)
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def join(self):
        if isinstance(self.in_rx, Queue):
            await self.in_rx.join()
        else:
            await self.stream_done.wait()

    # directly access from a stream with readexactly method
    async def stream_core(self):
        try:
            # Process a chunk of samples
            corr     = self.corr
            lpf      = self.lpf
            bpf      = self.bpf

            sampler  = self.sampler
            unnrzi   = self.unnrzi

            pwrmtr   = self.pwrmtr

            bits_q = self.bits_q   # output stream
            is_sync = False

            if hasattr(self.in_rx, 'readexactly'):
                # probably stdin stream
                readexactly = self.in_rx.readexactly
                is_sync = False
            elif hasattr(self.in_rx, 'read'):
                # probably a file
                readexactly = self.in_rx.read
                is_sync = True
            else:
                raise Exception('unknown stream')

            sql = self.squelch

            # bytes to integer converter
            btoi = bs16toi if self.stream_type=='s16' else bu16toi

            while True:
                try:
                    if is_sync:
                        b = readexactly(2)
                        await asyncio.sleep(0)
                    else:
                        b = await readexactly(2)
                except EOFError:
                    break
                if not b:
                    break
                o = btoi(b) # convert bytes to integer
                o = bpf(o)
                p = pwrmtr(o)
                if p < sql:
                    continue
                # eprint(p,o)
                o = corr(o)
                o = lpf(o)
                bs = sampler(o)
                if bs != 2: # _NONE
                    b = unnrzi(bs)
                    # eprint(b,end='')
                    await bits_q.put(b) #bits_out_q
        except Exception as err:
            print_exc(err)
        finally:
            self.stream_done.set()


    async def q_core(self):
        try:
            # Process a chunk of samples
            corr     = self.corr
            lpf      = self.lpf
            bpf      = self.bpf
            sampler  = self.sampler
            unnrzi   = self.unnrzi
            pwrmtr   = self.pwrmtr

            in_rx = self.in_rx     # input stream
            bits_q = self.bits_q   # output stream

            while True:
                #fetch next chunk of samples (array)
                arr_siz = await in_rx.get()
                if isinstance(arr_siz, tuple) and len(arr_siz)==2:
                    # if we specified an array and a size...
                    arr = arr_siz[0]
                    siz = arr_siz[1]
                else:
                    # if we just have an array, use it
                    arr = arr_siz
                    siz = len(arr)

                for i in range(siz):
                    o = arr[i]
                    o = bpf(o)
                    p = pwrmtr(o)
                    if p < sql:
                        continue
                    o = corr(o)
                    o = lpf(o)
                    bs = sampler(o)
                    if bs != 2: # _NONE
                        b = unnrzi(bs)
                        # eprint(b,end='')
                        await bits_q.put(b) #bits_out_q

                in_rx.task_done() # done
        except Exception as err:
            print_exc(err)


##############################
######### OLD STUFF ##########
##############################
                # # loop where we allow for inner-loop output
                # for i in range(siz):
                    # o = arr[i]
                    # # print(o)
                    # if self.debug_samples == 'in':
                        # s = struct.pack('<h',clamps16(o)) # little-endian signed output
                        # sys.stdout.buffer.write(s)
                    # o = bpf(o)
                    # if self.debug_samples == 'bpf':
                        # s = struct.pack('<h',clamps16(o)) # little-endian signed output
                        # sys.stdout.buffer.write(s)
                    # o = corr(o)
                    # if self.debug_samples == 'cor':
                        # s = struct.pack('<h',clamps16(o)) # little-endian signed output
                        # sys.stdout.buffer.write(s)
                    # o = lpf(o)
                    # if self.debug_samples == 'lpf':
                        # s = struct.pack('<h',clamps16(o)) # little-endian signed output
                        # sys.stdout.buffer.write(s)
                    # bs = sampler(o)
                    # if bs != 2: # _NONE
                        # b = unnrzi(bs)
                        # # eprint(b,end='')
                        # await bits_q.put(b) #bits_out_q
                # if self.debug_samples:
                    # sys.stdout.buffer.flush()

    # def analyze(self,start_from = 100e-3):
        # o = self.o
        # m   = max([max(o),abs(min(o))])
        # sca = m//(2**8)
        # st = int(start_from/self.ts)
        # while o[st-1]<0 and o[st] >= 0:
            # st+=1
        # bstp = self.tbaud/self.ts
        # ibaud = int(bstp)
        # st = st - int(bstp/4) # clk sample (center of eye)
        # eye     = {'l':None,'r':None,'u':None,'d':None} #TODO use array lookup
        # booleye = {'l':False,'r':False,} #TODO use array lookup
        # for x in frange(st, len(o)-ibaud, bstp):
            # ci = round(x)
            # r = int(3*ibaud/4) #eye scan range
            # #plt.plot(list(range(-r,r)), [v//sca for v in o[ci-r:ci+r]])

            # #eye u/d
            # if o[ci] > 0:
                # eye['u'] = eye['u'] if eye['u'] and eye['u'] < o[ci]//sca else o[ci]//sca
            # else:
                # eye['d'] = eye['d'] if eye['d'] and eye['d'] > o[ci]//sca else o[ci]//sca

            # #eye l/r
            # for k in booleye:
                # booleye[k] = True
            # for e in range(r):
                # if booleye['l'] and\
                   # (o[ci-e] > 0 and o[ci-e-1] <= 0 or\
                    # o[ci-e] < 0 and o[ci-e-1] >= 0):
                    # eye['l'] = eye['l'] if eye['l'] and eye['l'] > -e else -e
                    # booleye['l'] = False
                # if booleye['r'] and\
                   # (o[ci+e] > 0 and o[ci+e+1] <= 0 or\
                   # o[ci+e] < 0 and o[ci+e+1] >= 0):
                    # eye['r'] = eye['r'] if eye['r'] and eye['r'] < +e else +e
                    # booleye['r'] = False
                # if not booleye['r'] and not booleye['l']:
                    # break
        # eprint(eye)
        # # plt.show()

