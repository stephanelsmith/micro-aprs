
import sys
import io
import asyncio
import struct

async def reader():
    # stream reader in py
    # https://stackoverflow.com/questions/64303607/python-asyncio-how-to-read-stdin-and-write-to-stdout?noredirect=1&lq=1
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    while True:
        try:
            r = await reader.readexactly(2)
        except asyncio.IncompleteReadError:
            #on eof, break
            break
        print(struct.unpack('<h', r)[0])


async def main():
    tasks = []
    tasks.append(asyncio.create_task(reader()))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

