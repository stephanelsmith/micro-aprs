
import sys
import asyncio
from asyncio import Event

from lib.compat import IS_UPY
from lib.compat import print_exc
from lib.compat import stdout_write
from lib.compat import get_stdin_streamreader
from lib.compat import Queue

async def write():
    try:
        x = 0
        b=bytearray(1)
        while True:
            b[0]=x
            #sys.stdout.buffer.write(b) #err
            #sys.stdout.write(b)
            stdout_write(b)
            x = (x+1)%256
            await asyncio.sleep_ms(100)
            if x == 100:
                return
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

async def read():
    reader = await get_stdin_streamreader()
    b = bytearray(1)
    try:
        while True:
            try:
                b[0:1] = await reader.readexactly(1)
            except EOFError:
                break
            print(b[0],b)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)

def create_viper_test():
    x = 0
    @micropython.viper
    def inner(v:int) -> int:
        nonlocal x
        q : int = int(x)
        q += 1
        x = (q << 1) | 1
        return int(x)
    return inner

async def q1(q):
    try:
        for x in range(10):
            print('q1','adding',x)
            await q.put(x)
        #print('q1','wait')
        #await q.wait()
        #print('q1','join')
        await q.join()
        print('q1','done')
        #print('???')
    except Exception as err:
        raise
async def q2(q):
    for x in range(10):
        r = await q.get()
        print('q2','got',r)
        await asyncio.sleep(1)
        q.task_done()

async def main():
    try:
        if 'read' in sys.argv:
            await read()
        elif 'write' in sys.argv:
            await write()
        elif 'q' in sys.argv:
            print('start')

            q = Queue()
            ts = []
            ts.append(asyncio.create_task(q1(q)))
            await asyncio.sleep(1)
            ts.append(asyncio.create_task(q2(q)))
            await asyncio.gather(*ts, return_exceptions=True)
            #await q1(q)
            #await q2(q)
            print('Q DONE')
        
    except asyncio.CancelledError:
        raise
    except Exception as err:
        raise
        print_exc(err)

asyncio.run(main())

