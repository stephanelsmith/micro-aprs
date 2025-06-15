
import sys
import asyncio
import struct

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25

import lib.upydash as _
from lib.parse_args import mod_parse_args
from lib.utils import pretty_binary

from lib.utils import eprint # debug print to stderr, reserve stdout for pipe

#micropython/python compatibility
from lib.compat import IS_UPY
from lib.compat import print_exc
from lib.compat import get_stdin_streamreader

if not IS_UPY:
    import wave
    # from subprocess import check_output

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
            if buf[idx] == 10: # \n
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
                   rate    = 22050,
                   vox     = False, # add additiona flags to enable vox
                   verbose = False,
                   ):
    try:
        async with AFSKModulator(sampling_rate = rate,
                                 verbose       = verbose) as afsk_mod:

            while True:
                # get aprs from input
                aprs = await aprs_q.get()

                # try to process as ax25
                try:
                    ax25 = AX25(aprs    = aprs,
                                verbose = verbose,)
                except asyncio.CancelledError:
                    raise
                except Exception as err:
                    eprint('# bad aprs ax25:{}\n{}'.format(aprs,err))
                    continue

                # verbose output messaging
                if verbose:
                    _aprs = ax25.to_aprs()
                    eprint('===== MOD >>>>>', _aprs.decode())
                    eprint('--ax25--')
                    pretty_binary(ax25.to_frame())

                # AFSK
                afsk,stop_bit = ax25.to_afsk()

                await afsk_mod.pad_zeros(10)
                
				# pre-message flags
				# we need at least one since nrzi has memory and you have 50-50 chance depending on how the code intializes the nrzi
                if vox:
                    await afsk_mod.send_flags(150)
                else:
                    await afsk_mod.send_flags(4)
                # await afsk_mod.send_flags(4)

                # generate samples
                await afsk_mod.to_samples(afsk     = afsk, 
                                          stop_bit = stop_bit,
                                          )
                # send post message flags
                # multimon-ng and direwolf want one additional post flag in addition to the one at the end
                # of the message
				# we need at least one since nrzi has memory and you have 50-50 chance depending on how the code intializes the nrzi
                if vox:
                    await afsk_mod.send_flags(4)
                else:
                    await afsk_mod.send_flags(4)

                await afsk_mod.pad_zeros(10)

                # flush the output array and size and put on afsk_q
                arr,s = await afsk_mod.flush()
                await afsk_q.put((arr,s))
                # eprint('APRS mod done: {}'.format(ax25))
                # await afsk_q.put(( None, None))

                aprs_q.task_done()

    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

# async def run_in_thread(cmd):
    # print(cmd)
    # return await asyncio.to_thread(check_output, cmd.split())

def create_wav(wave_filename):
    wav = wave.open(wave_filename, 'w')
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(22050)
    return wav

async def afsk_out(afsk_q,
                   out_file = '-', # - | null | .wav | play
                   ):
    write = sys.stdout.buffer.write
    flush = sys.stdout.buffer.flush
    try:

        # set wave filename
        is_wave = False
        wav = None
        if out_file[-4:] == '.wav':# or\
           # out_file == 'play':
            if IS_UPY:
                raise Exception('wave files not supported in upy')
            is_wave = True
            if out_file[-4:] == '.wav':
                wave_filename = out_file
            else:
                wave_filename = 'temp.wav'

        while True:
            arr,siz = await afsk_q.get()
            if out_file == '-':
                if arr and siz:
                    for i in range(siz):
                        samp = struct.pack('<h', arr[i]) # little-endian signed output
                        write(samp) # buffer write binary
                    flush()
            elif out_file == 'null':
                pass
            elif is_wave:
                if not wav:
                    wav = create_wav(wave_filename)
                if arr != None and siz != None:
                    for i in range(siz):
                        samp = struct.pack('<h', arr[i])
                        wav.writeframesraw(samp)
                elif wav:
                    wav.close()
                    # if out_file == 'play':
                        # # play wav
                        # await run_in_thread('play {}'.format(wave_filename))
                    wav = None

            afsk_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)
    finally:
        if wav:
            wav.close()
            # if out_file == 'play':
                # # play wav
                # await run_in_thread('play {}'.format(wave_filename))

async def main():
    args = mod_parse_args(sys.argv)
    if args == None:
        return

    eprint('# APRS MOD')
    # eprint(args)
    eprint('# RATE {}'.format(args['args']['rate']))
    eprint('# IN   {}'.format(args['in']['file']))
    eprint('# OUT  {}'.format(args['out']['file']))

    # APRS queue, these items are queued in from stdin and out in afsk_mod
    aprs_q = Queue()

    # AFSK queue, the samples, each item is a tuple: (array['i'], size), queued in from afsk_mod and out in afsk_out
    afsk_q = Queue() # afsk output queue

    tasks = []
    try:

        # afsk_mod, convert APRS messages into AFSK samples
        tasks.append(asyncio.create_task(afsk_mod(aprs_q, 
                                                  afsk_q, 
                                                  rate    = args['args']['rate'],
                                                  vox     = args['args']['vox'],
                                                  verbose = args['args']['verbose'],
                                                  )))

        # afsk_out, output AFSK samples
        tasks.append(asyncio.create_task(afsk_out(afsk_q, 
                                                  out_file = args['out']['file'],
                                                  )))
        

        # read all items from pipe, returns EOF
        await read_aprs_from_pipe(aprs_q)

        # wait until queues are done
        await aprs_q.join()
        await afsk_q.join()

    except Exception as err:
        print_exc(err)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        sys.stdout.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

