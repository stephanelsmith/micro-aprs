
import sys
import io
import asyncio
import struct
from array import array

from scipy import signal
import math

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


def create_fir(coefs,scale):
    ncoefs = len(coefs)
    coefs = array('i', (coefs[i] for i in range(ncoefs)))
    bufin = array('i', (0 for x in range(ncoefs)))
    idx = 0
    def inner(v:int)->int:
        nonlocal ncoefs, coefs, bufin, idx, scale
        bufin[idx] = v
        o = 0
        for i in range(ncoefs):
            o += (coefs[i] * bufin[(idx-i)%ncoefs]) // scale
        idx = (idx+1)%ncoefs
        return o
    return inner
def create_lpf(ncoefs, fa, fs):
    wid = 200
    coefs = signal.firls(ncoefs,
                        (0, fa, fa+wid, fs/2),
                        (1, 1,  0,      0), 
                        fs=fs)
    coefs = [round(x*10000) for x in coefs]
    g = sum([coefs[i] for i in range(len(coefs))])
    return create_fir(coefs = coefs,
                      scale = g,
                      )
def create_bandpass(ncoefs, fmark, fspace, fs):
    wid = 200
    coefs = signal.firls(ncoefs,
                        (0, fmark-wid, fmark, fspace, fspace+wid, fs/2),
                        (0, 0,         1,     1,      0,          0), 
                        fs=fs)
    coefs = [round(x*10000) for x in coefs]
    g1 = sum([coefs[i]*math.cos(2*math.pi*fmark/fs*i) for i in range(len(coefs))])
    g2 = sum([coefs[i]*math.sin(2*math.pi*fspace/fs*i) for i in range(len(coefs))])
    g = int((abs(g1)+abs(g2))/2)
    return create_fir(coefs = coefs,
                      scale = g,
                      )


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

        nmark = int(self.tmark/self.ts)
        ncoefsbaud = 4
        ncoefs = int(nmark*ncoefsbaud) if int(nmark*ncoefsbaud)%2==1 else int(nmark*ncoefsbaud)+1
        self.band = create_bandpass(ncoefs = ncoefs,
                                    fmark  = self.fmark,
                                    fspace = self.fspace,
                                    fs     = self.fs)
        self.agc = create_agc(sp = 2**12,
                              depth = int(self.tbaud/self.ts),
                              )
        self.corr = create_corr(ts    = self.ts,
                                shift = 1)

        nmark = int(self.tmark/self.ts)
        ncoefsbaud = 2
        ncoefs = int(nmark*ncoefsbaud) if int(nmark*ncoefsbaud)%2==1 else int(nmark*ncoefsbaud)+1
        self.lpf = create_lpf(ncoefs = ncoefs,
                              fa     = 1200,
                              fs     = self.fs)

    def proc(self, arr):
        corr  = self.corr
        agc   = self.agc
        lpf   = self.lpf
        band  = self.band
        self.o = array('i', (0 for x in range(len(arr))))
        o = self.o
        for i in range(len(arr)):
            o[i] = arr[i]
            #o[i] = band(o[i])
            o[i] = agc(o[i])
            o[i] = corr(o[i])
            o[i] = lpf(o[i])

    def dump_raw(self, out_type):
        o   = self.o
        m   = max([max(o),abs(min(o))])
        m   = max(o)
        sca = m//(2**15)+1
        #print(m)
        #print(sca)
        for s in self.o:
            # x = int.to_bytes(s, 2, 'little', signed=True)
            try:
                x = struct.pack('<h', s//sca)
            except:
                #print('ERROR PACKING',s,sca,s//sca,0x7fff)
                x = struct.pack('<h', 0)
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
