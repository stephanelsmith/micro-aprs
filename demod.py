
import sys
import io
import asyncio
import struct
from array import array

from utils import parse_args

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

CORRELATOR_DELAY = 446e-6

def create_corr(ts, shift):
    delay = int(round(CORRELATOR_DELAY/ts)) #correlator delay (index)
    dat = array('i', (x for x in range(delay)))
    idx = 0
    def inner(v:int)->int:
        nonlocal idx,dat,delay,shift
        o = v*dat[idx]
        dat[idx] = v
        idx = (idx+1)%delay
        return o
    return inner

class AFSK_DEMOD():
    def __init__(self, sampling_rate=22050):
        self.fmark = 1200
        self.tmark = 1/self.fmark
        self.fspace = 2200
        self.tspace = 1/self.fspace
        self.fs = sampling_rate
        self.ts = 1/self.fs
        self.fbaud = 1200
        self.tbaud = 1/self.fbaud

        self.corr = create_corr(ts    = self.ts,
                                shift = 1)

    def proc(self, arr):
        corr = self.corr
        self.o = array('i', (0 for x in range(len(arr))))
        o = self.o
        for idx in range(len(arr)):
            o[idx] = corr(arr[idx])
            # o[idx] = arr[idx]

    def dump_raw(self, out_type):
        for s in self.o:
            # x = int.to_bytes(s, 2, 'little', signed=True)
            x = struct.pack('<h', s//256)
            sys.stdout.buffer.write(x)


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
    if src == '-':
        arr = await read_pipe()
    else:
        arr = await read_file(src = src)

    demod = AFSK_DEMOD()
    demod.proc(arr = arr)
    demod.dump_raw(out_type = 'raw')

    # tasks = []
    # tasks.append(asyncio.create_task(demod()))
    # await asyncio.gather(*tasks)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

