
import asyncio

try:
    import micropython
    IS_UPY = True
except ModuleNotFoundError:
    IS_UPY = False

import sys
import io

# Exception printing
if IS_UPY:
    #micropython
    print_exc = sys.print_exception
else:
    #python3
    import traceback
    #print_exc = traceback.print_exc
    print_exc = traceback.print_exception

# Stdout
if IS_UPY:
    #micropython
    stdout_write = sys.stdout.write
else:
    #python3, for writing bytes
    stdout_write = sys.stdout.buffer.write

# Stdin
if IS_UPY:
    if 'TextIOWrapper' in str(type(sys.stdin)):
        #micropython unix port
        async def get_stdin_streamreader():
            return asyncio.StreamReader(sys.stdin)
    if 'FileIO' in str(type(sys.stdin)):
        #micropython esp32, do not convert \r to \n
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


