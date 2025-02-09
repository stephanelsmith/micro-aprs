
import sys
import asyncio
import gc
from micropython import RingIO
# import time

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

from upy.afsk import in_afsk

# afsk sample frequency
_FOUT = 11_025
# _FOUT = const(22_050)
# _FOUT = const(44_100)


async def demod_core(in_rx, ax25_q):
    try:
        bits_q = Queue()
        async with AFSKDemodulator(sampling_rate = _FOUT,
                                   in_rx         = in_rx,
                                   bits_out_q    = bits_q,
                                   verbose       = False,
                                   debug_samples = False,
                                   options       = {},
                                   ) as afsk_demod:
            async with AX25FromAFSK(bits_in_q      = bits_q,
                                    ax25_q         = ax25_q,
                                    verbose        = False):
                await Event().wait()
                # await in_rx.join()
                # await bits_q.join()
    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt:
        return
    except Exception as err:
        print_exc(err)

async def consume_ax25(ax25_q, 
                       is_quite = False, # suppress stdout
                       ):
    try:
        count = 1
        while True:
            ax25 = await ax25_q.get()
            if not is_quite:
                try:
                    sys.stdout.write('[{}] {}\n'.format(count, ax25))
                except UnicodeDecodeError:
                    sys.stdout.write('[{}] ERR\n'.format(count))
                # sys.stdout.flush()
            count += 1
            ax25_q.task_done()
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt:
        return
    except Exception as err:
        print_exc(err)


async def start():

    tasks = []
    try:
        in_rx = Queue()
        ax25_q = Queue()

        #create ax25 consumer
        tasks.append(asyncio.create_task(consume_ax25(ax25_q   = ax25_q,)))
        tasks.append(asyncio.create_task(demod_core(in_rx = in_rx, 
                                                    ax25_q    = ax25_q)))
        # wait until consumer ax25 completed
        # await ax25_q.join()

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

