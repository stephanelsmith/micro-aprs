
import sys
import asyncio

async def writer():
    try:
        x = 0
        b=bytearray(1)
        while True:
            b[0]=x
            sys.stdout.write(b)
            x = (x+1)%256
            await asyncio.sleep_ms(100)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

async def reader():
    sreader = asyncio.StreamReader(sys.stdin)
    b = bytearray(1)
    try:
        while True:
            # r = await sreader.readinto(mv[:1])
            await sreader.readinto(b)
            print(b[0],b)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

async def main():
    try:
        if 'read' in sys.argv:
            await reader()
        elif 'write' in sys.argv:
            await writer()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

