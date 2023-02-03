
import sys
import io
import asyncio
import struct
import traceback
from array import array
import signal
from pydash import py_ as _

import matplotlib.pyplot as plt

from asyncio import Queue
from asyncio import Event

from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK

from lib.utils import parse_args
import lib.defs as defs

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7

async def read_pipe():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    arr = array('i',[])
    while True:
        try:
            r = await reader.readexactly(2)
        except asyncio.IncompleteReadError:
            #on eof, break
            break
        print(struct.unpack('<h', r)[0])
    return arr

async def read_samples_from_raw(samples_q, src):
    try:
        if src[-4:] != '.raw':
            raise Exception('uknown file type', src)
        arr = array('i',(0 for x in range(defs.SAMPLES_SIZE)))
        idx = 0
        with open(src, 'rb') as o:
            while True:
                b = o.read(2) # TODO, READ INTO
                if not b:
                    break
                arr[idx] = struct.unpack('<h', b)[0]
                arr[idx]
                idx += 1
                if idx%defs.SAMPLES_SIZE == 0:
                    await samples_q.put((arr, idx))
                    arr = array('i',(0 for x in range(defs.SAMPLES_SIZE)))
                    idx = 0
            await samples_q.put((arr, idx))
    except Exception as err:
        traceback.print_exc()
    await asyncio.sleep(.1)
    sys.exit()

async def consume_ax25(ax25_q):
    try:
        while True:
            ax25 = await ax25_q.get()
            print(ax25)
            ax25_q.task_done()
    except Exception as err:
        traceback.print_exc()

# async def shutdown():
    # tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    # [task.cancel() for task in tasks]
    # await asyncio.gather(*tasks, return_exceptions=True)

async def main():
    # loop = asyncio.get_running_loop()
    # signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    # for s in signals:
        # loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown()))

    args = parse_args({
        'rate' : {
            'short'   : 'r',
            'type'    : int,
            'default' : 22050,
        },
        'in_type' : {
            'short'   : 't',
            'type'    : int,
            'default' : 'raw',
        },
        'verbose' : {
            'short'   : 'v',
            'type'    : bool,
            'default' : False,
        },
    })

    src = sys.argv[-1]

    samples_q = Queue()
    bits_q = Queue()
    ax25_q = Queue()

    try:
        tasks = []

        #from .raw file
        tasks.append(asyncio.create_task(read_samples_from_raw(samples_q = samples_q, 
                                                                src       = src)))

        #create ax25 consumer
        tasks.append(asyncio.create_task(consume_ax25(ax25_q = ax25_q)))

        #samples_q consumer
        #bits_q producer
        async with AFSKDemodulator(sampling_rate = 22050,
                                   samples_in_q  = samples_q,
                                   bits_out_q    = bits_q,
                                   verbose       = args['verbose']) as afsk_demod:
            #bits_q consumer
            #ax25_q producer
            async with AX25FromAFSK(bits_in_q = bits_q,
                                    ax25_q    = ax25_q,
                                    verbose   = args['verbose']) as bits2ax25:
                await asyncio.sleep(0)
                await ax25_q.join()
    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        return
    finally:
        _.for_each(tasks, lambda t: t.cancel())
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


