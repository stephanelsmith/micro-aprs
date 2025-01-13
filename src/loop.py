
import sys
import asyncio
import gc

from array import array
from asyncio import Event

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25
from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK
from afsk.func import afsk_detector

import lib.upydash as _
from lib.compat import print_exc

# afsk sample frequency
_FOUT = 11_025
# _FOUT = const(22_050)
# _FOUT = const(44_100)


async def start():

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

            await afsk_mod.pad_zeros(ms = 10)
            await afsk_mod.send_flags(10)
            await afsk_mod.to_samples(afsk     = afsk, 
                                      stop_bit = stop_bit,
                                      )
            await afsk_mod.send_flags(2)
            await afsk_mod.pad_zeros(ms = 10)
            arr,siz = await afsk_mod.flush()

            # print(arr)

    except Exception as err:
        print_exc(err)

    try:
        #AFSK Demodulation - convert analog samples to bits
        #samples_q consumer
        #bits_q producer
        samples_q = Queue()
        bits_q = Queue()
        ax25_q = Queue()
        await samples_q.put((arr,len(arr)))

        async with AFSKDemodulator(sampling_rate = _FOUT,
                                   samples_in_q  = samples_q,
                                   bits_out_q    = bits_q,
                                   verbose       = False,
                                   debug_samples = False,
                                   options       = {},
                                   ) as afsk_demod:
            # AX25FromAFSK - convert bits to ax25 objects
            #bits_q consumer
            #ax25_q producer
            async with AX25FromAFSK(bits_in_q      = bits_q,
                                    ax25_q         = ax25_q,
                                    verbose        = False):
                print('wait samples')
                await samples_q.join()
                print('wait bits')
                await bits_q.join()
        while not ax25_q.empty():
            await ax25_q.get()
            ax25_q.task_done()
            print(ax25)
        await ax25_q.join()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

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
