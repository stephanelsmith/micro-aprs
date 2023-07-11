#! env/bin/python

import sys
import asyncio
import traceback
import struct
from asyncio import Queue
from asyncio import Event

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25

import lib.upydash as _
from lib.parse_args import mod_parse_args
from lib.utils import pretty_binary
from lib.utils import eprint

async def read_aprs_from_pipe(aprs_q, 
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
                # print('GOT', bytes(buf[:idx]))
                await aprs_q.put(bytes(buf[:idx]))
                idx = 0
                continue
            buf[idx] = ord(b)
            idx = (idx+1)%2048
        if idx:
            await aprs_q.put(bytes(buf[:idx]))
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

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
                aprs_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

async def afsk_out(afsk_q,
                   args,
                   ):
    try:
        while True:
            samp = await afsk_q.get()
            x = struct.pack('<h', samp)
            if args['out']['file'] == '-':
                sys.stdout.buffer.write(x)
            afsk_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()


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

