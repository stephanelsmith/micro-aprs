
import sys
import asyncio
import gc
# import time

from array import array
from asyncio import Event
from micropython import RingIO

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25
from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK
from afsk.func import afsk_detector
from cdsp import i16tobs
from afsk.func import bu16toi, bs16toi

import lib.upydash as _
from lib.compat import print_exc

from afsk.fir_options import fir_options

# afsk sample frequency
_FOUT = 11_025
# _FOUT = const(22_050)
# _FOUT = const(44_100)

# Fake "adc" for testing on unix port
async def gen_adc( ):
    rio = RingIO(500000)
    try:
        async with AFSKModulator(sampling_rate = _FOUT,
                                 signed        = False,
                                 verbose       = False) as afsk_mod:
            aprs = b'KI5TOF>APRS:>hello world!'
            ax25 = AX25(aprs    = aprs,
                        verbose = False,)
            #AFSK
            afsk,stop_bit = ax25.to_afsk()
            # print(afsk)

            for x in range(5):
                await afsk_mod.pad_zeros(ms = 20)
                await afsk_mod.send_flags(10)
                await afsk_mod.to_samples(afsk     = afsk, 
                                        stop_bit = stop_bit,
                                        )
                await afsk_mod.send_flags(4)
                await afsk_mod.pad_zeros(ms = 20)

            arr,siz = await afsk_mod.flush()

            # add afsk array to the in_rx for processing
            while True:
                await asyncio.sleep_ms(0)
                for i in range(siz):
                    # await in_rx.put(arr)
                    rio.write(i16tobs(arr[i]))
                    # await asyncio.sleep_ms(0)
                    # if i%10==0:
                        # await asyncio.sleep_ms(0)
                return rio
    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt:
        return
    except Exception as err:
        print_exc(err)

# @micropython.native
# def in_afsk(adc, rio, demod):
    # bpf = demod.bpf
    # pwrmtr = demod.pwrmtr
    # isin = False
    # read = adc.read
    # write = rio.write
    # while True:
        # b = read(2)
        # if not b:
            # return
        # o = bu16toi(b)
        # o = bpf(o)
        # p = pwrmtr(o)
        # if p > 100  and not isin:
            # isin = True
        # elif p < 100 and isin:
            # return
        # write(b)

@micropython.viper
def in_afsk_vip(adc, rio, demod):
    bpf = demod.bpf
    pwrmtr = demod.pwrmtr
    _sql:int = int(demod.squelch)
    _isin:int = int(0)
    read = adc.read
    write = rio.write
    while True:
        b = read(2)
        if not b:
            return 
        _o:int = int(bu16toi(b))
        _p:int = int(pwrmtr(bpf(_o)))
        if _p > _sql  and not _isin:
            _isin = 1
        elif _p < _sql and _isin:
            return 
        write(b)

async def start():

    tasks = []
    try:
        ax25_q = Queue()
        rio = RingIO(500000)

        # create fake dac
        adc = await gen_adc()
        # print('ADC:{}'.format(adc.any()))

        bits_q = Queue()
        async with AFSKDemodulator(sampling_rate = _FOUT,
                                   in_rx         = None,   # don't launch core task
                                   stream_type   = 'u16',
                                   bits_out_q    = bits_q,
                                   is_embedded   = True,
                                   options       = {},
                                   verbose       = False,
                                   ) as demod:
            async with AX25FromAFSK(bits_in_q      = bits_q,
                                    ax25_q         = ax25_q,
                                    verbose        = False):
                while True:
                    # synchronous read from ADC
                    # print('Start')
                    in_afsk_vip(adc, rio, demod)
                    # print('READ: {}'.format(rio.any()))

                    if rio.any() == 0:
                        break

                    # process results
                    # print('core')
                    await demod.stream_core(in_rx = rio)
                    
                    # process all bits in queue
                    await bits_q.join()

                    # process ax25
                    # effectively ax25_q.join()
                    # print('ax25')
                    while not ax25_q.empty():
                        ax25 = await ax25_q.get()
                        print(ax25)

                    # clean up
                    # print('gc')
                    gc.collect()

        await asyncio.gather(*tasks, return_exceptions=True)

    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt:
        return
    except Exception as err:
        print_exc(err)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*[t for t in tasks if not t.done()], return_exceptions=True)

def main():
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        print_exc(err)
    finally:
        asyncio.new_event_loop()  # Clear retained state
main()
