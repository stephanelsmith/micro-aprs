
import sys
import asyncio

from asyncio import Event
from lib.compat import const

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25

import lib.upydash as _

_FOUT = const(22_050)

async def gc_coro():
    try:
        while True:
            gc.collect()
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

async def start():

    try:
        gc_task = asyncio.create_task(gc_coro())
        afsk_q = Queue() #afsk output queue

        async with AFSKModulator(sampling_rate = _FOUT,
                                 afsk_q        = afsk_q,
                                 signed        = False,
                                 verbose       = False) as afsk_mod:
            aprs = b'KI5TOF>APRS:>hello world!'
            ax25 = AX25(aprs    = aprs,
                        verbose = False,)
            #AFSK
            afsk,stop_bit = ax25.to_afsk()
            # print(afsk)

            await afsk_mod.send_flags(4)
            #generate samples
            await afsk_mod.to_samples(afsk     = afsk, 
                                        stop_bit = stop_bit,
                                        )
            await afsk_mod.send_flags(4)

        # all samples to an output list
        outs = []
        while not afsk_q.empty():
            a_s = await afsk_q.get() # get array,size
            outs.append(a_s)

        print(outs)

    except Exception as err:
        sys.print_exception(err)
    finally:
        gc_task.cancel()

def main():
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        sys.print_exception(err)
    finally:
        asyncio.new_event_loop()  # Clear retained state
main()
