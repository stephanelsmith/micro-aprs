
import sys
import io
import asyncio

# python or micropython?
if sys.implementation.name == 'micropython':
    IS_UPY = True
else:
    IS_UPY = False

if IS_UPY:
    from micropython import const
else:
    const = lambda x:x


# if micropython, do we have c modules?
if IS_UPY:
    try:
        import cdsp
        HAS_C = True
    except ImportError:
        HAS_C = False
    
    # https://github.com/micropython/micropython/issues/11805#issuecomment-1598282774
    if sys.implementation._mpy >> 10 == 0:
        HAS_VIPER = False
    else:
        HAS_VIPER = True
else:
    HAS_C = False
    HAS_VIPER = False

# print_exc(err): print an exception's traceback on either runtime.
# MicroPython's sys.print_exception() requires the exception, while CPython's
# traceback.print_exc() takes none (and would misread one as its 'limit' arg),
# so always call print_exc(err) from inside an `except ... as err:` block.
if IS_UPY:
    #micropython
    def print_exc(err=None):
        if err is None and hasattr(sys, 'exc_info'):
            err = sys.exc_info()[1]
        if err is not None:
            sys.print_exception(err)
else:
    #python3
    import traceback
    def print_exc(err=None):
        if err is None:
            traceback.print_exc()
        else:
            traceback.print_exception(type(err), err, err.__traceback__)


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


