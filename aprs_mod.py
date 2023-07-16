#! env/bin/python

import sys
import asyncio
import struct

from lib.compat import Queue
#from asyncio import Queue
#from upy.primitives.queue import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25

import lib.upydash as _
from lib.parse_args import mod_parse_args
from lib.utils import pretty_binary
from lib.utils import eprint

#micropython/python compatibility
from lib.compat import IS_UPY
from lib.compat import print_exc
from lib.compat import stdout_write
from lib.compat import get_stdin_streamreader

async def read_aprs_from_pipe(aprs_q, 
                              ):
    try:
        reader = await get_stdin_streamreader()
        buf = bytearray(2048)
        idx = 0
        while True:
            try:
                buf[idx:idx+1] = await reader.readexactly(1)
            except EOFError:
                break #eof break
            if buf[idx] == 10:#\n
                await aprs_q.put(bytes(buf[:idx]))
                idx = 0
                continue
            idx = (idx+1)%2048
        if idx:
            await aprs_q.put(bytes(buf[:idx]))
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

async def afsk_mod(aprs_q,
                   afsk_q,
                   args,
                   ):
    try:
        async with AFSKModulator(sampling_rate = args['args']['rate'],
                                 afsk_q        = afsk_q,
                                 verbose       = args['args']['verbose']) as afsk_mod:

            while True:
                #get aprs from input
                aprs = await aprs_q.get()

                #try to process as ax25
                try:
                    ax25 = AX25(aprs    = aprs,
                                verbose = args['args']['verbose'])
                except asyncio.CancelledError:
                    raise
                except:
                    eprint('# bad aprs ax25:{}'.format(aprs))
                    continue

                #verbose output messaging
                if args['args']['verbose']:
                    eprint('===== MOD >>>>>', ax25.to_aprs())
                    eprint('--ax25--')
                    pretty_binary(ax25.to_frame())

                #AFSK
                afsk,stop_bit = ax25.to_afsk()
                
				#pre-message flags
				#we need at least one since nrzi has memory and you have 50-50 chance depending on how the code intializes the nrzi
				#increasing this number for vox
                await afsk_mod.send_flags(4)

                #generate samples
                await afsk_mod.to_samples(afsk     = afsk, 
                                          stop_bit = stop_bit,
                                          )
                #send post message flags
                #multimon-ng and direwolf want one additional post flag in addition to the one at the end
                #of the message
                await afsk_mod.send_flags(4)
                #aprs_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

async def afsk_out(afsk_q,
                   args,
                   ):
    try:
        while True:
            samp = await afsk_q.get()
            x = struct.pack('<h', samp)
            if args['out']['file'] == '-':
                stdout_write(x)
            #afsk_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)


async def main():
    args = mod_parse_args(sys.argv)

    eprint('# APRS MOD')
    eprint('# RATE {}'.format(args['args']['rate']))
    eprint('# IN   {} {}'.format(args['in']['type'], args['in']['file']))
    eprint('# OUT  {} {}'.format(args['out']['type'], args['out']['file']))

    aprs_q = Queue() #aprs input queue
    afsk_q = Queue() #afsk output queue
    tasks = []
    try:
        tasks.append(asyncio.create_task(afsk_out(afsk_q, args,)))
        tasks.append(asyncio.create_task(afsk_mod(aprs_q, afsk_q, args,)))
        await read_aprs_from_pipe(aprs_q)
        #await aprs_q.join()
        #await afsk_q.join()
    except Exception as err:
        print_exc(err)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

