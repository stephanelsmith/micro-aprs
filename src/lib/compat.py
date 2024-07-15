
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

# import sign, isqrt
if IS_UPY:
    try:
        # try c module
        from cvec import csign
        def sign(a:int)->int:
            return csign(a)
    except ImportError:
        def sign(a:int)->int:
            return (a > 0) - (a < 0)
    try:
        # try c module
        from cvec import cisqrt as isqrt
    except ImportError:
        # TODO viper implemtnation on isqrt
        raise
else:
    def sign(a:int)->int:
        return (a > 0) - (a < 0)
    from math import isqrt

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


