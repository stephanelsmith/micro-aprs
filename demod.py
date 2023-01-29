
import sys
import io
import asyncio
import struct
import traceback
from array import array
import math
from pydash import py_ as _

import matplotlib.pyplot as plt
from scipy import signal

from asyncio import Queue

from crc16 import crc16_ccit
from utils import parse_args
from utils import frange
from utils import pretty_binary
from utils import format_bytes
from utils import format_bits
from utils import int_div_ceil
from utils import reverse_byte
from utils import assign_bit
from utils import get_bit

AX25_FLAG      = 0x7e
AX25_ADDR_LEN  = 7

async def read_pipe():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    arr = array('i',[])
    while True:
        try:
            r = await reader.readexactly(2)
        except asyncio.IncompleteReadError:
            #on eof, break
            break
        print(struct.unpack('<h', r)[0])
    return arr

async def read_file(src):
    if src[-4:] != '.raw':
        raise Exception('uknown file type', src)
    with open(src, 'rb') as o:
        b = o.read()
    mv = memoryview(b)
    arr = array('i',[])
    for i in range(0,len(mv),2):
        arr.append(struct.unpack('<h', mv[i:i+2])[0])
    return arr





async def main():
    args = parse_args({
        'rate' : {
            'short'   : 'r',
            'type'    : int,
            'default' : 22050,
        },
        'in_type' : {
            'short'   : 't',
            'type'    : int,
            'default' : 'raw',
        },
    })

    src = sys.argv[-1]

    #TODO, make arr yield results for processing as we stream in
    if src == '-':
        arr = await read_pipe()
    else:
        arr = await read_file(src = src)

    # Raw samples -> AFSKDemod input
    samples_q = Queue()

    # AFSKDemod bits -> AX25 Processor
    bits_q = Queue()

    # AX25 

    async with AFSKDemodulator(sampling_rate=22050) as afsk_demod:
        async with BitStreamToAX25() as bits2ax25:
            while True:
                #read array of data
                async for b in afsk_demod.process_samples(arr = arr):
                    async for ax25 in bits2ax25.in_q(b):
                        print(ax25)

if __name__ == '__main__':
    asyncio.run(main())


