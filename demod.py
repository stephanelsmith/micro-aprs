
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
from lib.utils import eprint
import lib.defs as defs

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7

async def read_pipe_raw(samples_q, 
                        read_done_evt):
    try:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        arr = array('i',(0 for x in range(defs.SAMPLES_SIZE)))
        idx = 0

        while True:
            try:
                b = await reader.readexactly(2)
            except asyncio.IncompleteReadError:
                # continue
                break #eof break
            arr[idx] = struct.unpack('<h', b)[0]
            idx += 1
            if idx%defs.SAMPLES_SIZE == 0:
                await samples_q.put((arr, idx))
                arr = array('i',(0 for x in range(defs.SAMPLES_SIZE)))
                idx = 0
        await samples_q.put((arr, idx))

    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        raise
    finally:
        read_done_evt.set()

async def read_samples_from_raw(samples_q, 
                                file,
                                read_done_evt):
    try:
        if file[-4:] != '.raw':
            raise Exception('uknown file type', file)
        arr = array('i',(0 for x in range(defs.SAMPLES_SIZE)))
        idx = 0
        with open(file, 'rb') as o:
            while True:
                b = o.read(2) # TODO, READ INTO
                if not b:
                    break
                arr[idx] = struct.unpack('<h', b)[0]
                idx += 1
                if idx%defs.SAMPLES_SIZE == 0:
                    await samples_q.put((arr, idx))
                    arr = array('i',(0 for x in range(defs.SAMPLES_SIZE)))
                    idx = 0
            await samples_q.put((arr, idx))
    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        raise
    finally:
        read_done_evt.set()

async def consume_ax25(ax25_q):
    try:
        while True:
            ax25 = await ax25_q.get()
            print(ax25)
            ax25_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

async def main():
    args = parse_args(sys.argv)

    read_done_evt = Event()
    samples_q = Queue()
    bits_q = Queue()
    ax25_q = Queue()

    try:
        tasks = []

        #from .raw file
        if args['in']['file'] == '-':
            tasks.append(asyncio.create_task(read_pipe_raw(samples_q      = samples_q,
                                                           read_done_evt  = read_done_evt,
                                                           )))
        elif args['in']['type'] == 'raw' and args['in']['file']:
            tasks.append(asyncio.create_task(read_samples_from_raw(samples_q     = samples_q, 
                                                                   file          = args['in']['file'],
                                                                   read_done_evt = read_done_evt,
                                                                   )))
        else:
            raise Exception('unsupported input {} {}'.format(args['in']['type'], args['in']['file']))

        #create ax25 consumer
        tasks.append(asyncio.create_task(consume_ax25(ax25_q = ax25_q)))

        #samples_q consumer
        #bits_q producer
        async with AFSKDemodulator(sampling_rate = 22050,
                                   samples_in_q  = samples_q,
                                   bits_out_q    = bits_q,
                                   verbose       = args['args']['verbose']) as afsk_demod:
            #bits_q consumer
            #ax25_q producer
            async with AX25FromAFSK(bits_in_q = bits_q,
                                    ax25_q    = ax25_q,
                                    verbose   = args['args']['verbose']) as bits2ax25:
                #wait for data for work through the system
                await read_done_evt.wait()
                await samples_q.join()
                await bits_q.join()
                await ax25_q.join()
    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        raise
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*[t for t in tasks if not t.done()], return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

