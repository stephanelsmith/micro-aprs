
import sys
import asyncio

from array import array


from lib.compat import IS_UPY
from lib.compat import print_exc
from lib.compat import stdout_write
from lib.compat import get_stdin_streamreader

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

async def main():
    try:
        if 'read' in sys.argv:
            await read()
        elif 'write' in sys.argv:
            await write()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print_exc(err)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

