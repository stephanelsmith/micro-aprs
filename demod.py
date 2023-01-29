
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
    wid = 400
    coefs = signal.firls(ncoefs,
                        (0, fa-wid, fa+wid, fs/2),
                        (1, 1,  0,      0), 
                        fs=fs)
    coefs = [round(x*10000) for x in coefs]
    g = sum([coefs[i] for i in range(len(coefs))])
    return create_fir(coefs = coefs,
                      scale = g,
                      )

def create_bandpass(ncoefs, fmark, fspace, fs):
    wid = 600
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

def create_sampler(fbaud, 
               fs, ):
    tbaud = fs/fbaud #inverted for t
    ibaud = round(tbaud) #integer step
    ibaud_2 = round(tbaud/2)
    buf = array('i', (0 for x in range(2)))
    buflen = 2
    idx = 0
    lastx = 0 #last crossing
    o = 0
    oidx = 0
    _NONE = 2
    def inner(v:int)->int:
        nonlocal idx,buf,lastx
        nonlocal o,oidx
        buf[idx] = v
        if (buf[(idx-1)%buflen] > 0) != (buf[idx] > 0):
            #detected crossing
            if lastx > ibaud_2 and lastx < ibaud*8:
                oidx = (lastx - ibaud_2)//ibaud+1 #number of baud periods
                # o = 1 if buf[idx-1]>0 else 0
                # the correlator inverts mark/space, invert here to mark=1, space=0
                o = 0 if buf[idx-1]>0 else 1
                # print(''.join([str(o)]*oidx))
            else:
                oidx = 0
            lastx = 0
        else:
            lastx += 1
        idx = (idx+1)%buflen
        if oidx == 0:
            return _NONE
        oidx -= 1
        #print(o,end='')
        return o
    return inner


class CallSSID():
    __slots__ = (
        'call',
        'ssid',
    )
    def __init__(self, call = None, ssid = None,
                       aprs = None,
                       ax25 = None,
                       ):
        # Initialize a callsign ssid in three ways
        #   1) By specifying call and ssid explicitly
        #   2) By specifying aprs formatted string/bytes, eg. KI5TOF-5
        #   3) By specifying ax25 bytes to be decoded
        self.call = call 
        self.ssid = ssid
        if ax25:
            self.from_ax25(ax25)
        elif aprs:
            self.from_aprs(aprs)

    def from_aprs(self, call_ssid):
        #read in formats like KI5TOF-5
        if isinstance(call_ssid, str):
            call_ssid = callsign.split('-')
        elif isinstance(call_ssid, (bytes, bytearray)):
            call_ssid = callsign.decode('utf').split('-')
        else:
            raise Exception('unknown format '+str(call_ssid))
        self.call = call_ssid[0].upper()
        self.ssid = int(call_ssid[1]) if len(call_ssid)==2 else 0

    def to_aprs(self):
        if self.ssid:
            return str(self.call)+'-'+str(self.ssid)
        else:
            return str(self.call)

    def from_ax25(self, mv):
        #read from encoded ax25 format 
        if len(mv) != 7:
            raise Exception('callsign unable to read from bytes, bad length ' +str(len(mv)))
        for call_len in range(6):
            if mv[call_len] == 0x40: #searching for ' ' character (still left shifted one)
                break
            call_len += 1
        self.call = bytearray(mv[:call_len]) #make bytearray copy, don't modify in place
        for i in range(call_len):
            self.call[i] = self.call[i]>>1
        self.call = self.call.decode('utf')
        self.ssid = (mv[6] & 0x17)>>1

    def to_ax25(self):
        return b''

    def __repr__(self):
        return self.to_aprs()

class AX25():
    __slots__ = (
        'src',
        'dst',
        'digis',
        'info',
    )

    def __init__(self, src        = '',
                       dst        = '',
                       digis      = [],
                       info       = '',
                       aprs       = None,
                       ax25       = None,
                       ):
        # Initialize in three different ways
        #   1) The individual fields directly
        #   2) By APRS message, eg. M0XER-4>APRS64,TF3RPF,WIDE2*,qAR,TF3SUT-2:!/.(M4I^C,O `DXa/A=040849|#B>@\"v90!+|
        #   3) By AX25 bytes
        self.src        = src
        self.dst        = dst
        self.digis      = digis
        self.info       = info
        if ax25:
            self.from_ax25(ax25 = ax25)
        elif aprs:
            self.from_aprs(aprs = aprs)

    def callssid_to_str(self, callssid):
        try:
            return callssid.to_aprs()
        except:
            return ''

    def to_aprs(self):
        src = self.callssid_to_str(self.src)
        dst = self.callssid_to_str(self.dst)
        dst_digis = ','.join([dst]+[self.callssid_to_str(digi) for digi in self.digis])
        return src+'>'+dst_digis+':'+self.info
    
    def from_aprs(self, aprs):
        pass

    def from_ax25(self, ax25):
        mv = memoryview(ax25)

        idx = 0
        #flags
        while mv[idx] == AX25_FLAG and idx < len(mv):
            idx+=1
        start_idx = idx

        stop_idx = idx
        while mv[stop_idx] != AX25_FLAG and stop_idx < len(mv):
            stop_idx+=1

        #destination
        self.dst = CallSSID(ax25 = mv[idx:idx+AX25_ADDR_LEN])
        idx += AX25_ADDR_LEN

        #source
        self.src = CallSSID(ax25 = mv[idx:idx+AX25_ADDR_LEN])
        idx += AX25_ADDR_LEN
       
        #digis
        while not mv[idx-1]&0x01:
            self.digis.append(CallSSID(ax25 = mv[idx:idx+AX25_ADDR_LEN]))
            idx += AX25_ADDR_LEN

        #skip control/pid
        idx += 2

        self.info = bytes(mv[idx:stop_idx-2]).decode('utf')
        crc  = bytes(mv[stop_idx-2:stop_idx])
        _crc = struct.pack('<H',crc16_ccit(mv[start_idx:stop_idx-2]))
        if crc != _crc:
            raise Exception('crc error '+str(crc)+' != '+str(_crc))

    def __repr__(self):
        return self.to_aprs()


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
        self.eye = create_sampler(fbaud = self.fbaud,
                                  fs    = self.fs)

        self.tasks = []
        self.bits_q = Queue()
        self.frame_q = Queue()

    async def __aenter__(self):
        self.tasks.append(asyncio.create_task(self.delimin_coro()))
        self.tasks.append(asyncio.create_task(self.frame_coro()))
        return self

    async def __aexit__(self, *args):
        _.for_each(self.tasks, lambda t: t.cancel())
        await asyncio.gather(*self.tasks, return_exceptions=True)

    def analyze(self,start_from = 100e-3):
        o = self.o
        m   = max([max(o),abs(min(o))])
        sca = m//(2**8)
        st = int(start_from/self.ts)
        while o[st-1]<0 and o[st] >= 0:
            st+=1
        bstp = self.tbaud/self.ts
        ibaud = int(bstp)
        st = st - int(bstp/4) # clk sample (center of eye)
        eye     = {'l':None,'r':None,'u':None,'d':None} #TODO use array lookup
        booleye = {'l':False,'r':False,} #TODO use array lookup
        for x in frange(st, len(o)-ibaud, bstp):
            ci = round(x)
            r = int(3*ibaud/4) #eye scan range
            #plt.plot(list(range(-r,r)), [v//sca for v in o[ci-r:ci+r]])

            #eye u/d
            if o[ci] > 0:
                eye['u'] = eye['u'] if eye['u'] and eye['u'] < o[ci]//sca else o[ci]//sca
            else:
                eye['d'] = eye['d'] if eye['d'] and eye['d'] > o[ci]//sca else o[ci]//sca

            #eye l/r
            for k in booleye:
                booleye[k] = True
            for e in range(r):
                if booleye['l'] and\
                   (o[ci-e] > 0 and o[ci-e-1] <= 0 or\
                    o[ci-e] < 0 and o[ci-e-1] >= 0):
                    eye['l'] = eye['l'] if eye['l'] and eye['l'] > -e else -e
                    booleye['l'] = False
                if booleye['r'] and\
                   (o[ci+e] > 0 and o[ci+e+1] <= 0 or\
                   o[ci+e] < 0 and o[ci+e+1] >= 0):
                    eye['r'] = eye['r'] if eye['r'] and eye['r'] < +e else +e
                    booleye['r'] = False
                if not booleye['r'] and not booleye['l']:
                    break
        print(eye)
        # plt.show()

    async def afsk_arr_in(self, arr):
        # Process a chunk of samples
        # input is arr, an integer array
        # output is bits_q, this bit stream is delminiated in delimin_coro task
        corr  = self.corr
        agc   = self.agc
        lpf   = self.lpf
        band  = self.band
        eye  = self.eye
        self.o = array('i', (0 for x in range(len(arr))))
        o = self.o
        self.bs = array('i', (0 for x in range(len(arr))))
        bs = self.bs

        for i in range(len(arr)):
            o[i] = arr[i]
            # o[i] = band(o[i])
            # o[i] = agc(o[i])
            o[i] = corr(o[i])
            o[i] = lpf(o[i])
            bs[i] = eye(o[i])
        for b in bs:
            if b == 1 or b == 0:
                await self.bits_q.put(b)

    async def delimin_coro(self):
        # We receive a stream of 1s and 0s from bits_q, this function
        # will find/chunk the bitstream delminiated by the AX25 flags
        # output: (bytearray, num_bits) is sent to frame_q
        try:
            inbsize = 2024
            inb = bytearray(inbsize)
            mv = memoryview(inb)
            idx = 0
            flgcnt = 0
            unnrzi = self.create_unnrzi()
            while True:
                _b = await self.bits_q.get()
                #UN NRZI, it's better to do it here since
                # - easy to detect the AX25 flags decoded (they can be flipped in NRZI)
                # - ideally done with closure
                b = unnrzi(_b)
                # print(b,end='')
                inb[idx//8] = assign_bit(inb[idx//8], idx, b)
                idx += 1
                if b == 0 and flgcnt == 6:
                    #detected ax25 frame flag
                    if idx//8 > 2: 
                        await self.frame_q.put((bytearray(mv[:int_div_ceil(idx,8)]), idx))
                    mv[0] = AX25_FLAG #keep the frame flag that we detected in buffer
                    idx = 8
                flgcnt = flgcnt + 1 if b else 0
                if idx == inbsize:
                    idx = 0
        except Exception as err:
            traceback.print_exc()

    def create_unnrzi(self):
        c = 1
        def inner(b):
            nonlocal c
            if b != c:
                c = b
                return 0
            else:
                c = b
                return 1
        return inner

    def unstuff(self, mv, stop_bit):
        #look for 111110, remove the 0
        c = 0
        for idx in range(stop_bit):
            mask = (0x80>>(idx%8))
            b = (mv[idx//8] & mask) >> ((8-idx-1)%8) #pick bit
            if b == 0 and c == 5:
                #detected stuffed bit, remove it
                shift_in = self.shift_bytes_left(mv, idx//8+1)
                self.remove_bit_shift_from_right(mv, idx, shift_in)
                c = 0
            c = c+b if b==1 else 0

    def remove_bit_shift_from_right(self, mv, idx, shift_in=0):
        if idx%8 == 7:
            #the bit is far right, just apply shift_in
            pass
        else:
            #we need to split at specific bit index position
            #get the portion that's getting shifted
            rmask = 0xff >> (idx%8)
            lmask = rmask ^ 0xff
            mv[idx//8] = (lmask & mv[idx//8]) | (((mv[idx//8]&rmask)<<1)&0xff)
        if shift_in:
            mv[idx//8] |= 0x01
        else:
            mv[idx//8] &= (0x01 ^ 0xff)

    def shift_bytes_left(self, mv, start_byte):
        l = 0x00
        #idx iterating byte index
        for idx in range(len(mv)-1,start_byte-1, -1):
            #work from right to left
            t = 0x80 & mv[idx] #save bit shifted out
            mv[idx] = (mv[idx]<<1)&0xff
            mv[idx] = mv[idx] | 0x01 if l else mv[idx] #shift l
            l = t # store shifted bit for next iteration
        return l

    def reverse_bit_order(self, mv):
        for idx in range(len(mv)):
            mv[idx] = reverse_byte(mv[idx])

    async def frame_coro(self, debug = True):
        try:
            while True:
                buf,stop_bit = await self.frame_q.get()
                mv = memoryview(buf)
                if debug:
                    print('-afsk ax25 deliminated bits-')
                    pretty_binary(mv)

                #unstuff
                self.unstuff(mv, stop_bit)
                if debug:
                    print('-un-stuffed-')
                    pretty_binary(mv)

                #reverse bit order
                self.reverse_bit_order(mv)
                if debug:
                    print('-un-reversed-')
                    pretty_binary(mv)

                #decode
                ax25 = AX25(ax25 = mv)
                if debug:
                    print('-ax25 decoded-')
                    print(ax25)

        except Exception as err:
            traceback.print_exc()



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

    async with AFSK_DEMOD() as demod:
        await demod.afsk_arr_in(arr = arr)
        await asyncio.sleep(1)

    #demod.analyze()

if __name__ == '__main__':
    asyncio.run(main())


