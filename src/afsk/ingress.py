
import os
import asyncio

import struct
from array import array

from afsk.func import afsk_detector

import lib.upydash as _
from lib.utils import eprint

#micropython/python compatibility
from lib.compat import print_exc

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
