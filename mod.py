
import sys
import asyncio
import traceback
import struct
# from pydash import py_ as _
from asyncio import Queue
from asyncio import Event

from afsk.mod import AFSKModulator
from ax25 import AX25
from ax25 import AX25_FLAG

import lib.upydash as _
from lib.utils import parse_args
from lib.utils import pretty_binary
from lib.utils import eprint

async def read_aprs_from_pipe(aprs_q, 
                              read_done_evt,
                              ):
    try:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        buf = bytearray(2048)
        idx = 0
        eol = ord('\n')
        while True:
            try:
                b = await reader.readexactly(1)
            except asyncio.IncompleteReadError:
                break #eof break
            if ord(b) == eol:
                await aprs_q.put(bytes(buf[:idx]))
                idx = 0
                continue
            buf[idx] = ord(b)
            idx = (idx+1)%2048
        if idx:
            await aprs_q.put(bytes(buf[:idx]))
    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        raise
    finally:
        read_done_evt.set()

async def afsk_out(afsk_q,
                   args,
                   ):
    try:
        while True:
            samp = await afsk_q.get()
            x = struct.pack('<h', samp)
            if not args['args']['quiet']:
                sys.stdout.buffer.write(x)
            afsk_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

async def core_coro(aprs_q,
                    afsk_q,
                    args,
                    ):
    try:
        async with AFSKModulator(sampling_rate = 22050,
                                 afsk_q        = afsk_q,
                                 verbose       = args['args']['verbose']) as afsk_mod:
            
            # initial flags
            flags = bytearray(1)
            for i in range(len(flags)):
                flags[i] = AX25_FLAG
            await afsk_mod.to_samples(afsk     = flags,
                                      stop_bit = len(flags)*8)

            while True:
                aprs = await aprs_q.get()
                try:
                    ax25 = AX25(aprs    = aprs,
                                verbose = args['args']['verbose'])
                    if args['args']['verbose']:
                        eprint('===== MOD >>>>>', ax25.to_aprs())
                        eprint('--ax25--')
                        pretty_binary(ax25.to_ax25())
                    afsk,stop_bit = ax25.to_afsk()
                    await afsk_mod.to_samples(afsk     = afsk, 
                                              stop_bit = stop_bit,
                                              # zpad_ms  = 0,
                                              )
                except:
                    continue
                finally:
                    aprs_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

async def main():
    args = parse_args(sys.argv)

    aprs_q = Queue() #aprs input queue
    afsk_q = Queue() #afsk output queue
    read_done_evt = Event()

    tasks = []
    try:
        tasks.append(asyncio.create_task(afsk_out(afsk_q,
                                                  args,
                                                  )))

        if args['in']['file'] == '-':
            tasks.append(asyncio.create_task(read_aprs_from_pipe(aprs_q         = aprs_q,
                                                                read_done_evt  = read_done_evt,
                                                                )))

        tasks.append(asyncio.create_task(core_coro(aprs_q = aprs_q,
                                                   afsk_q = afsk_q,
                                                   args   = args,
                                                   )))

        await read_done_evt.wait()
        await aprs_q.join()
        await afsk_q.join()
    except Exception as err:
        traceback.print_exc()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

