#! env/bin/python

import sys
import io
import asyncio
import struct
from array import array
from json import dumps

from lib.compat import Queue
from asyncio import Event

from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK
from afsk.func import afsk_detector

import lib.upydash as _
from lib.parse_args import demod_parse_args
from lib.utils import eprint
import lib.defs as defs

#micropython/python compatibility
from lib.compat import IS_UPY
from lib.compat import print_exc
from lib.compat import get_stdin_streamreader

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7

async def read_raw_from_pipe(samples_q, 
                             ):
    try:
        reader = await get_stdin_streamreader()

        arr = array('i',range(defs.SAMPLES_SIZE))
        idx = 0

        while True:
            try:
                a = await reader.readexactly(2)
            except EOFError:
                break #eof break
            arr[idx] = struct.unpack('<h', a)[0]
            # arr[idx] = int.from_bytes(a,'little',signed=True)
            idx += 1
            if idx%defs.SAMPLES_SIZE == 0:
                if afsk_detector(arr,idx): #afsk signal detector
                    await samples_q.put((arr, idx))
                    arr = array('i',range(defs.SAMPLES_SIZE))
                idx = 0
        await samples_q.put((arr, idx))

    except Exception as err:
        print_exc(err)
    except asyncio.CancelledError:
        raise

async def read_samples_from_raw(samples_q, 
                                file,
                                ):
    try:
        if file[-4:] != '.raw':
            raise Exception('uknown file type', file)
        arr = array('i',range(defs.SAMPLES_SIZE))
        idx = 0
        with open(file, 'rb') as f:
            f.seek(0, 2)#SEEK_END = 2 
            size = f.tell()
            f.seek(0)
            i = 0
            while i < size:
                a = f.read(2) # TODO, USE READINTO
                if not a:
                    break
                i += 2 
                arr[idx] = struct.unpack('<h', a)[0]
                # arr[idx] = int.from_bytes(a,'little',signed=True)
                idx += 1
                if idx%defs.SAMPLES_SIZE == 0:
                    if afsk_detector(arr,idx): #afsk signal detector
                        await samples_q.put((arr, idx))
                        arr = array('i',range(defs.SAMPLES_SIZE))
                    idx = 0
            await samples_q.put((arr, idx))
    except Exception as err:
        print_exc(err)
    except asyncio.CancelledError:
        raise


async def consume_ax25(ax25_q):
    try:
        count = 1
        while True:
            ax25 = await ax25_q.get()
            sys.stdout.write('[{}] {}\n'.format(count, ax25))
            sys.stdout.flush()
            count += 1
            ax25_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

async def demod_core(samples_q,
                     bits_q,
                     ax25_q,
                     args):
    try:
        #AFSK Demodulation - convert analog samples to bits
        #samples_q consumer
        #bits_q producer
        async with AFSKDemodulator(sampling_rate = args['args']['rate'],
                                   samples_in_q  = samples_q,
                                   bits_out_q    = bits_q,
                                   verbose       = args['args']['verbose'],
                                   options       = args['args']['options'],
                                   ) as afsk_demod:
            # AX25FromAFSK - convert bits to ax25 objects
            #bits_q consumer
            #ax25_q producer
            async with AX25FromAFSK(bits_in_q      = bits_q,
                                    ax25_q         = ax25_q,
                                    verbose        = args['args']['verbose']) as bits2ax25:

                #flush afsk_demod filters
                await samples_q.put((array('i',(0 for x in range(afsk_demod.flush_size))),afsk_demod.flush_size))
                
                # just wait
                await Event().wait()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

async def main():

    args = demod_parse_args(sys.argv)
    eprint('# APRS DEMOD')
    eprint('# RATE {}'.format(args['args']['rate']))
    eprint('# IN   {} {}'.format(args['in']['type'], args['in']['file']))
    eprint('# OUT  {} {}'.format(args['out']['type'], args['out']['file']))

    samples_q = Queue()
    bits_q = Queue()
    ax25_q = Queue()

    try:
        tasks = []

        #create ax25 consumer
        tasks.append(asyncio.create_task(consume_ax25(ax25_q = ax25_q)))
        tasks.append(asyncio.create_task(demod_core(samples_q,
                                                    bits_q,
                                                    ax25_q,
                                                    args)))

        #from .raw file
        if args['in']['file'] == '-':
            await read_raw_from_pipe(samples_q)
        elif args['in']['type'] == 'raw' and args['in']['file']:
            # tasks.append(asyncio.create_task(read_samples_from_raw(samples_q     = samples_q, 
                                                                   # file          = args['in']['file'],
                                                                   # )))
            await read_samples_from_raw(samples_q = samples_q,
                                        file          = args['in']['file'],
                                        )
        else:
            raise Exception('unsupported input {} {}'.format(args['in']['type'], args['in']['file']))

        await samples_q.join()
        await bits_q.join()
        await ax25_q.join()

    except Exception as err:
        print_exc(err)
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

