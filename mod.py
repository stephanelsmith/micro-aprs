
import sys
import asyncio
import traceback
import struct
from pydash import py_ as _
from asyncio import Queue

from afsk.mod import AFSKModulator
from ax25 import AX25

from lib.utils import parse_args
from lib.utils import pretty_binary
from lib.utils import eprint

async def read_pipe(ax25_q, 
                    read_done_evt):
    try:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                pass
            except asyncio.IncompleteReadError:
                # continue
                break #eof break

    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        raise
    finally:
        read_done_evt.set()


async def afsk_out(afsk_q):
    try:
        while True:
            samp = await afsk_q.get()
            x = struct.pack('<h', samp)
            sys.stdout.buffer.write(x)
            afsk_q.task_done()
    except Exception as err:
        traceback.print_exc()


async def main():
    args = parse_args(sys.argv)

    ax25_q = Queue() #ax25 input queue
    afsk_q = Queue()
    tasks = []
    tasks.append(asyncio.create_task(afsk_out(afsk_q)))

    try:
        async with AFSKModulator(sampling_rate = 22050,
                                 verbose       = args['args']['verbose']) as afsk_demod:
            ax25 = AX25(src     = 'KI5TOF',
                        dst     = 'APRS',
                        digis   = [],
                        info    = 'hello world!',
                        verbose = args['args']['verbose'],
                        )
            if args['args']['verbose']:
                pass
                eprint('===== MOD >>>>>', ax25.to_aprs())
                eprint('--ax25--')
                pretty_binary(ax25.to_ax25())
                eprint('--afsk--')
            if args['args']['quiet']:
                #just show debug output
                ax25,stop_bit = ax25.to_afsk()
                # pretty_binary(ax25)
            if not args['args']['quiet']:
                #actually output
                ax25,stop_bit = ax25.to_afsk(flags_pre  = 2,
                                             flags_post = 2)
                await afsk_demod.to_samples(ax25     = ax25, 
                                            stop_bit = stop_bit,
                                            afsk_q   = afsk_q,
                                            zpad_ms  = 1,
                                            )
                await afsk_q.join()
    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        return
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

