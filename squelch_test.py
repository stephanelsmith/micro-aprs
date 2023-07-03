
#! env/bin/python

import sys
import io
import asyncio
import struct
import traceback
from afsk.func import create_afsk_detector

SAMPLES_SIZE = 22050/10

async def main():
    try:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        # arr = array('i',(0 for x in range(SAMPLES_SIZE)))
        idx = 0

        sigdet = create_afsk_detector()

        while True:
            try:
                b = await reader.readexactly(2)
                idx += 2
            except asyncio.IncompleteReadError:
                # continue
                break #eof break
            v = struct.unpack('<h', b)[0]
            rst = idx%SAMPLES_SIZE == 0
            s = sigdet(v,rst)
            if rst:
                #done with array
                if s:
                    print('SIG')

    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

