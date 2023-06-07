
import math
from array import array

from lib.utils import eprint
from lib.utils import frange
from lib.memoize import memoize_loads
from lib.memoize import memoize_dumps


def get_sin_table(size):
    return array('i', (int((2**15-1)*math.sin(x)) for x in frange(0,2*math.pi,2*math.pi/size)))
    # try:
        # # tbl = memoize_loads('sin_table', size)
        # return tbl
    # except:
        # tbl = array('i', (int((2**15-1)*math.sin(x)) for x in frange(0,2*math.pi,2*math.pi/size)))
        # # eprint(tbl)
        # # memoize_dumps('sin_table', tbl, size)
    # return tbl

# generator for iterating over the bits in bytearray
def gen_bits_from_bytes(mv, stop_bit = None):
    if stop_bit == None:
        stop_bit = len(mv)*8
    for idx in range(stop_bit):
        yield mv[idx//8]&(0x80>>(idx%8))

def create_nrzi():
    #process the bit stream bit-by-bit with closure
    c = 0
    def inner(b):
        nonlocal c
        if b == 0:
            c ^= 1 #toggle
        return c
    return inner

def create_unnrzi():
    #process the bit stream bit-by-bit with closure
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

def create_fir(coefs, scale):
    ncoefs = len(coefs)
    coefs = array('i', (coefs[i] for i in range(ncoefs)))
    bufin = array('i', (0 for x in range(ncoefs)))
    idx = 0
    scale = scale or 1
    def inner(v:int)->int:
        nonlocal ncoefs, coefs, bufin, idx, scale
        bufin[idx] = v
        o = 0
        for i in range(ncoefs):
            o += (coefs[i] * bufin[(idx-i)%ncoefs]) // scale
        idx = (idx+1)%ncoefs
        return o
    return inner

def create_lpf(ncoefs,       # filter size
               fa,           # cut-off f
               fs,           # fs
               width  = 400, #transition band size
               aboost = 1,   #gain at on-set of cut-off
               ):
    try:
        coefs,g = memoize_loads('lowpass', fa, fs, width, aboost)
    except:
        from scipy import signal
        coefs = signal.firls(ncoefs,
                            (0, fa,       fa+width, fs/2),
                            (1, aboost,   0,        0), 
                            fs=fs)
        coefs = [round(x*10000) for x in coefs]
        g = sum([coefs[i] for i in range(len(coefs))])
        memoize_dumps('lowpass', (coefs,g), fa, fs, width, aboost)
    return create_fir(coefs = coefs,
                      scale = g,
                      )

def create_bandpass(ncoefs,            # filter size
                    fmark, fspace,     # mark/space frequencies
                    fs,                # fs
                    width=600,         # transition freqency begin/end
                    amark=1, aspace=1, # mark/space gain
                    ):
    try:
        coefs,g = memoize_loads('bandpass', fmark, fspace, fs, width, amark, aspace)
    except:
        from scipy import signal
        coefs = signal.firls(ncoefs,
                            (0, fmark-width, fmark, fspace, fspace+width, fs/2),
                            (0, 0,           amark, aspace, 0,            0), 
                            fs=fs)

        coefs = [round(x*10000) for x in coefs]
        g1 = sum([coefs[i]*math.cos(2*math.pi*fmark/fs*i) for i in range(len(coefs))])
        g2 = sum([coefs[i]*math.sin(2*math.pi*fspace/fs*i) for i in range(len(coefs))])
        g = int((abs(g1)+abs(g2))/2)
        memoize_dumps('bandpass', (coefs,g), fmark, fspace, fs, width, amark, aspace)
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
        # if (buf[(idx-1)%buflen] > 0) and (buf[idx] < 0) or\
           # (buf[(idx-1)%buflen] < 0) and (buf[idx] > 0):
        if (buf[(idx-1)%buflen] > 0) != (buf[idx] > 0):
            #detected crossing
            if lastx > ibaud_2 and lastx < ibaud*8:
                oidx = (lastx - ibaud_2)//ibaud+1 #number of baud periods
                # o = 1 if buf[idx-1]>0 else 0
                # the correlator inverts mark/space, invert here to mark=1, space=0
                o = 0 if buf[idx-1]>0 else 1
                # print('*',''.join([str(o)]*oidx))
            else:
                oidx = 0
            lastx = 0
        else:
            lastx += 1
        idx = (idx+1)%buflen
        if oidx == 0:
            return _NONE
        oidx -= 1
        # print('&',o,end='')
        return o
    return inner


