#! env/bin/python

import sys
import asyncio

from lib.compat import Queue

from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK

import lib.upydash as _
from lib.parse_args import demod_parse_args
from lib.utils import eprint

#micropython/python compatibility
from lib.compat import print_exc
from lib.compat import get_stdin_streamreader

from afsk.ingress import read_samples_from_rtl_fm
# from afsk.ingress import read_samples_from_file

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

async def demod_core(in_rx,
                     bits_q,
                     ax25_q,
                     args,
                     ):
    try:
        #AFSK Demodulation - convert analog samples to bits
        #in_rx consumer
        #bits_q producer
        async with AFSKDemodulator(sampling_rate = args['args']['rate'],
                                   in_rx         = in_rx,
                                   bits_out_q    = bits_q,
                                   stream_type   = args['in']['type'],
                                   verbose       = args['args']['verbose'],
                                   options       = args['args']['options'],
                                   ) as afsk_demod:
                                   # debug_samples = args['args']['debug_samples'],
            # AX25FromAFSK - convert bits to ax25 objects
            #bits_q consumer
            #ax25_q producer
            async with AX25FromAFSK(bits_in_q   = bits_q,
                                    ax25_q      = ax25_q,
                                    verbose     = args['args']['verbose']) as bits2ax25:

                #flush afsk_demod filters
                # await in_rx.put((array('i',(0 for x in range(afsk_demod.flush_size))),afsk_demod.flush_size))
                
                await afsk_demod.join()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

async def main():
    args = demod_parse_args(sys.argv)
    eprint('# APRS DEMOD')
    eprint('# RATE {}'.format(args['args']['rate']))
    eprint('# IN   {} ({})'.format(args['in']['file'], args['in']['type']))
    eprint('# OUT  {} (ax25)'.format(args['out']['file']))
    # eprint(sys.argv)

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
            in_rx = await get_stdin_streamreader()
        elif args['in']['file']:
            in_rx = open(args['in']['file'], 'rb')
        elif args['in']['file'] == 'rtl_fm':
            in_rx = Queue()
            await read_samples_from_rtl_fm(in_rx)
        else:
            raise Exception('unsupported input {}'.format(args['in']['file']))

        # DEMOD CORE
        await demod_core(in_rx, bits_q, ax25_q, args)
                            
        # wait until queues are done
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

