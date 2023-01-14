
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


def create_agc(sp,depth):
    bufin = array('i', (0 for x in range(depth)))
    idx = 0
    def inner(v:int)->int:
        nonlocal sp,idx,bufin,depth
        bufin[idx] = v
        m = max(bufin)
        #sp = scale*m
        try:
            scale = sp//m
        except:
            scale = 1
        idx = (idx+1)%depth
        return scale*v
    return inner

CORRELATOR_DELAY = 446e-6
def create_corr(ts, shift):
    delay = int(round(CORRELATOR_DELAY/ts)) #correlator delay (index)
    dat = array('i', (0 for x in range(delay)))
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

        self.agc = create_agc(sp = 2**12,
                              depth = int(self.tbaud/self.ts),
                              )
        self.corr = create_corr(ts    = self.ts,
                                shift = 1)

    def proc(self, arr):
        corr = self.corr
        agc  = self.agc
        self.o = array('i', (0 for x in range(len(arr))))
        o = self.o
        for i in range(len(arr)):
            o[i] = arr[i]
            o[i] = agc(o[i])
            o[i] = corr(o[i])

    def dump_raw(self, out_type):
        o   = self.o
        m   = max(o)
        sca = m//(2**15-1)+1
        #print(m)
        #print(sca)
        db = 0
        for s in self.o:
            # x = int.to_bytes(s, 2, 'little', signed=True)
            try:
                db = db if db > s//sca else s//sca
                x = struct.pack('<h', s//sca)
            except:
                print('ERROR PACKING',s,sca,s//sca,0x7fff)
                raise
            sys.stdout.buffer.write(x)
        #print('max', db)


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

    demod = AFSK_DEMOD()
    demod.proc(arr = arr)
    demod.dump_raw(out_type = 'raw')

    # tasks = []
    # tasks.append(asyncio.create_task(demod()))
    # await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
