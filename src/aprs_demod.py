#! env/bin/python

import sys
import os
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

#micropython/python compatibility
from lib.compat import IS_UPY
from lib.compat import print_exc
from lib.compat import get_stdin_streamreader

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7
SAMPLES_SIZE   = 20000

# async def read_samples_from_pipe(in_q,
                                 # type = 's16',
                                 # ):
    # unpack = struct.unpack
    # q_put = in_q.put

    # try:
        # reader = await get_stdin_streamreader()
        # readexactly = reader.readexactly

        # arr = array('i',range(SAMPLES_SIZE))
        # idx = 0

        # while True:
            # try:
                # a = await readexactly(2)
            # except EOFError:
                # break #eof break
            # if type == 'u16':
                # # unsigned little endian
                # arr[idx] = (unpack('<H', a)[0] - 32768) #//6
            # else:
                # # signed little endian (default)
                # arr[idx] = unpack('<h', a)[0]
            # # eprint(arr[idx])
            # idx += 1
            # if idx%SAMPLES_SIZE == 0:
                # if afsk_detector(arr,idx): #afsk signal detector
                    # await q_put((arr, idx))
                    # # await asyncio.sleep(0)
                    # arr = array('i',range(SAMPLES_SIZE))
                # idx = 0
        # #if afsk_detector(arr,idx): # alway process tail
        # await q_put((arr, idx))

    # except Exception as err:
        # print_exc(err)
    # except asyncio.CancelledError:
        # raise

async def read_samples_from_rtl_fm(in_q, 
                                   ):
    try:
        stderr_task = None
        try:
            cmd = 'rtl_fm -f 144.390M -s 22050 -g 10'
            proc = await asyncio.create_subprocess_exec(
                cmd.split()[0], *cmd.split()[1:], 
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # process stderr messages separately from stdout
            async def proc_stderr(stderr):
                try:
                    while True:
                        stderr = await proc.stderr.readline()
                        msg = stderr.decode().strip()
                        if msg:
                            eprint(msg)
                            #if 'Failed to open rtlsdr device' in msg:
                            #    os.system('usbreset 0bda:2838')
                except Exception as err:
                    print_exc(err)
                except asyncio.CancelledError:
                    raise
            # stderr task
            stderr_task = asyncio.create_task(proc_stderr(proc.stderr))

            arr = array('i',range(SAMPLES_SIZE))
            idx = 0
            while True:
                try:
                    a = await proc.stdout.readexactly(2)
                except EOFError:
                    eprint('eof')
                    break
                #eprint(a)
                # arr[idx] = unpack('<H', a)[0] - 32768
                arr[idx] = int.from_bytes(a,'little',signed=False) - 32768
                idx += 1
                if idx%SAMPLES_SIZE == 0:
                    if afsk_detector(arr,idx): #afsk signal detector
                        await in_q.put((arr, idx))
                        await asyncio.sleep(0)
                        arr = array('i',range(SAMPLES_SIZE))
                    idx = 0
            await in_q.put((arr, idx))
            await asyncio.sleep(0)
        finally:
            eprint('killing rtl_fm process')
            proc.kill()
            await proc.wait()

    except Exception as err:
        print_exc(err)
    except asyncio.CancelledError:
        raise
    finally:
        if stderr_task:
            stderr_task.cancel()

async def read_samples_from_file(in_q, 
                                file,
                                ):
    try:
        # if file[-4:] != '.raw':
            # raise Exception('uknown file type', file)
        arr = array('i',range(SAMPLES_SIZE))
        idx = 0

        with open(file, 'rb') as f:
            f.seek(0, 2)#SEEK_END = 2 
            size = f.tell()
            f.seek(0)
            i = 0
            while i < size:
                a = f.read(2)
                if not a:
                    break
                i += 2 
                arr[idx] = struct.unpack('<h', a)[0]
                # arr[idx] = int.from_bytes(a,'little',signed=True)
                idx += 1
                if idx%SAMPLES_SIZE == 0:
                    if afsk_detector(arr,idx): #afsk signal detector
                        await in_q.put((arr, idx))
                        await asyncio.sleep(0)
                        arr = array('i',range(SAMPLES_SIZE))
                    idx = 0
            await in_q.put((arr, idx))
            await asyncio.sleep(0)
    except Exception as err:
        print_exc(err)
    except asyncio.CancelledError:
        raise

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
                except: #UnicodeDecodeError:
                    sys.stdout.write('[{}] ERR\n'.format(count))
                sys.stdout.flush()
            count += 1
            ax25_q.task_done()
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

async def demod_core(in_q,
                     bits_q,
                     ax25_q,
                     args):
    try:
        #AFSK Demodulation - convert analog samples to bits
        #in_q consumer
        #bits_q producer
        async with AFSKDemodulator(sampling_rate = args['args']['rate'],
                                   in_q          = in_q,
                                   bits_out_q    = bits_q,
                                   verbose       = args['args']['verbose'],
                                   options       = args['args']['options'],
                                   ) as afsk_demod:
                                   # debug_samples = args['args']['debug_samples'],
            # AX25FromAFSK - convert bits to ax25 objects
            #bits_q consumer
            #ax25_q producer
            async with AX25FromAFSK(bits_in_q      = bits_q,
                                    ax25_q         = ax25_q,
                                    verbose        = args['args']['verbose']) as bits2ax25:

                #flush afsk_demod filters
                # await in_q.put((array('i',(0 for x in range(afsk_demod.flush_size))),afsk_demod.flush_size))
                
                await afsk_demod.join()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

async def main():
    # print('***',sys.argv)
    args = demod_parse_args(sys.argv)
    eprint('# APRS DEMOD')
    eprint('# RATE {}'.format(args['args']['rate']))
    eprint('# IN   {}'.format(args['in']['file']))
    eprint('# OUT  {}'.format(args['out']['file']))

    bits_q = Queue()
    ax25_q = Queue()

    try:
        tasks = []


        #create ax25 consumer
        tasks.append(asyncio.create_task(consume_ax25(ax25_q   = ax25_q,
                                                      is_quite = args['args']['debug_samples']), # no output when debugging samples
                                        ))

        #from .raw file
        if args['in']['file'] == '-':
            in_q = await get_stdin_streamreader()
            # await read_samples_from_pipe(in_q,
                                         # type = args['in']['type'],
                                         # )
        elif args['in']['file'] == 'rtl_fm':
            in_q = Queue()
            await read_samples_from_rtl_fm(in_q)
        elif args['in']['file']:
            in_q = Queue()
            await read_samples_from_file(in_q = in_q,
                                        file          = args['in']['file'],
                                        )
        else:
            raise Exception('unsupported input {}'.format(args['in']['file']))

        # DEMOD CORE
        await demod_core(in_q, bits_q, ax25_q, args)
                            
        await bits_q.join()
        await ax25_q.join()

    except Exception as err:
        raise
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

