
import asyncio

import sys
import io

if sys.implementation.name == 'micropython':
    IS_UPY = True
else:
    IS_UPY = False

if IS_UPY:
    #micropython
    print_exc = sys.print_exception
else:
    #python3
    import traceback
    #print_exc = traceback.print_exc
    print_exc = traceback.print_exception

# Stdin
if IS_UPY:
    async def get_stdin_streamreader():
        return asyncio.StreamReader(sys.stdin.buffer)
else:
    #python3
    async def get_stdin_streamreader():
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        return reader


# asyncio synchronization primitives
if IS_UPY:
    #micropython
    import upy.primitives
    Queue = upy.primitives.Queue
else:
    #python3
    Queue = asyncio.Queue


