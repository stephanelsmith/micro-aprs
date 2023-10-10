
import traceback
import sys
import io
import os
from datetime import datetime
from subprocess import check_output
from array import array
import struct
import tempfile

import asyncio
from asyncio import Event
from asyncio import Queue
import json
import wave
# import pyaudio 

from ax25.ax25 import AX25
from ax25.callssid import CallSSID
import lib.defs as defs
from lib.compat import get_stdin_streamreader

CALL = 'KI5TOF'
PASSCODE = '17081'

async def run(cmd):
    return await asyncio.to_thread(check_output, cmd.split())

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
            idx += 1
            if idx%defs.SAMPLES_SIZE == 0:
                await samples_q.put((arr, idx))
                await asyncio.sleep(0)
                arr = array('i',range(defs.SAMPLES_SIZE))
                idx = 0
        await samples_q.put((arr, idx))
        await asyncio.sleep(0)

    except Exception as err:
        print(err)
        traceback.print_exc()
    except asyncio.CancelledError:
        raise

async def play_samples(samples_q):
    try:
        f_name = 'play.wav'
        while True:
            try:
                a = array('i', [])
                while True:
                    try:
                        _a,idx = await asyncio.wait_for(samples_q.get(), 1)
                        a = a + _a[:idx]
                        samples_q.task_done()
                    except asyncio.CancelledError:
                        raise
                    except asyncio.TimeoutError:
                        break
            except asyncio.CancelledError:
                raise
            except Exception as err:
                traceback.print_exc()
            finally:
                if a:
                    # play the samples
                    try:
                        print('write wav')
                        obj = wave.open(f_name,'w')
                        obj.setnchannels(1)
                        obj.setsampwidth(2)
                        obj.setframerate(22050)
                        for h in a:
                            obj.writeframesraw(struct.pack('<h', h))
                        obj.close()
                        print('play {}'.format(f_name))
                        await run('play {}'.format(f_name))
                    finally:
                        os.remove(f_name)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

# async def play_samples(samples_q):
    # try:
        # p = pyaudio.PyAudio()
        # stream = p.open(format=pyaudio.paInt16,
                        # channels=1,
                        # rate=22050,
                        # output=True)
        # while True:
            # a = array('i', [])
            # while True:
                # try:
                    # _a,idx = await asyncio.wait_for(samples_q.get(), 1)
                    # a = a + _a[:idx]
                    # samples_q.task_done()
                # except asyncio.TimeoutError:
                    # break
            # if len(a):
                # # play the samples
                # stream.write(bytes(a))
    # except asyncio.CancelledError:
        # raise
    # except Exception as err:
        # traceback.print_exc()
    # finally:
        # stream.close()
        # p.terminate()

async def main():

    samples_q = Queue()
    tasks = []

    try:
        tasks.append(asyncio.create_task(play_samples(samples_q)))
        await read_raw_from_pipe(samples_q)
        await samples_q.join()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
