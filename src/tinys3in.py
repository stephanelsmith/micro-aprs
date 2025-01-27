
import sys
import asyncio
import gc
import struct
from micropython import const
from micropython import RingIO

from machine import Pin
from machine import Pin

from asyncio import Event
import lib.upydash as _

from lib.compat import Queue

# afsk sample frequency
_FOUT = const(11_025)

_AFSK_OUT_PIN = const(1)

async def gc_coro():
    try:
        while True:
            gc.collect()
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

async def rio_reader(rio):
    sreader = asyncio.StreamReader(rio)
    while True:
        d = await sreader.readexactly(4)
        # signed little endian (default)
        o,p = struct.unpack('<hh', d)
        print(o,p)

async def start():

    try:
        gc_task = asyncio.create_task(gc_coro())
        tasks = []

        rio = RingIO(_FOUT*4)

        tasks.append(asyncio.create_task(rio_reader(rio = rio)))

        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as err:
        sys.print_exception(err)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*[t for t in tasks if not t.done()], return_exceptions=True)
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
