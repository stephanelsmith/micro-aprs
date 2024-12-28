
import math
from array import array

from lib.utils import eprint
from lib.compat import IS_UPY, HAS_C

if IS_UPY:
    import micropython
    if HAS_C:
        from cvec import isqrt
        from cvec import sign
        from cvec import uint_to_int
else:
    try:
        from math import isqrt
    except ImportError:
        from math import sqrt
        def isqrt(x):
            return int(sqrt(x))
    def sign(a:int)->int:
        return (a > 0) - (a < 0)

if IS_UPY:
    @micropython.viper
    def clamps16(o:int) -> int:
        if o > 32767:
            return 32767
        if o < -32768:
            return -32768
        return o
else:
    def clamps16(o):
        if o > 32767:
            return 32767
        if o < -32768:
            return -32768
        return o

def frange(start, stop, step, rnd=None):
    n = int(math.ceil((stop - start) / step))
    if isinstance(rnd,int):
        for i in range(n):
            yield round(start+i*step,rnd)
    else:
        for i in range(n):
            yield start+i*step

# generator for iterating over the bits in bytearray
def gen_bits_from_bytes(mv, stop_bit = None):
    if stop_bit == None:
        stop_bit = len(mv)*8
    for idx in range(stop_bit):
        yield mv[idx//8]&(0x80>>(idx%8))

if IS_UPY:
    @micropython.viper
    def afsk_detector(arr:ptr32, size:int)->bool:
        pol:int = 1 #polarity of the run we are currently tracking
        run:int = 0 #current run count (number of consecutive pos/neg samples)
        act:int = 0 #count of the number of runs we've seen above a threshold
        for i in range(size):
            # v:int = arr[i] # WARN, THIS IS ALWAYS U32 (POSITIVE VALUE)
            # v:int = int(uint_to_int(arr[i]))
            # we are only checking polarity, so we can HACK a bit and assume any
            # number < 2**31-1 is positive, anything > 2**31 is suppose to be a negative
            # v:int = 1 if arr[i] <= 2147483647 else -1
            v:int = arr[i]
            if v > int(2147483647):
                v *= -1
            # eprint(arr[i],v)
            if pol==1 and v > 0:
                run += 1
            elif pol==1 and v <= 0:
                if run > 6:  ## single run length constant
                    act += 1
                pol ^= 1 # no pol
                run = 1
            elif pol==0 and v < 0:
                run += 1
            elif pol==0 and v >= 0:
                if run > 6: ## single run length constant
                    act += 1
                pol ^= 1 # no pol
                run = 1
        return True if act > 10 else False # 10 - minimum number of run we need to declare signal detected
else:
    def afsk_detector(arr, size:int)->bool:
        pol = True #polarity of the run we are currently tracking
        run = 0    #current run count (number of consecutive pos/neg samples)
        act = 0   #count of the number of runs we've seen above a threshold
        for i in range(size):
            v = arr[i]
            if pol and v > 0:
                run += 1
            elif pol and v <= 0:
                if run > 6:  ## single run length constant
                    act += 1
                pol = not pol
                run = 1
            elif not pol and v < 0:
                run += 1
            elif not pol and v >= 0:
                if run > 6: ## single run length constant
                    act += 1
                pol = not pol
                run = 1
        return True if act > 10 else False # 10 - minimum number of run we need to declare signal detected

def create_outlier_fixer():
    # PYTHON
    delay = 3
    dat = array('i', (0 for x in range(delay)))
    idx = 0
    def inner(v:int)->int:
        nonlocal idx,dat,delay
        dat[idx] = v
        o = dat[idx]
        idx = (idx+1)%delay
        if sign(dat[(idx)%delay]) == sign(dat[(idx+1)%delay]) and\
           sign(dat[(idx)%delay]) != sign(dat[idx-1]):
            return dat[idx-1] * -1
        else:
            return dat[idx-1]
    return inner

def create_nrzi():
    #process the bit stream bit-by-bit with closure
    if IS_UPY:
        c = 0
        nl = array('B', [c])
        @micropython.viper
        def inner(b:int) -> int:
            nonlocal nl
            _nl = ptr8(nl)
            c:int      = _nl[0]
            if b == 0:
                c = 1 if c == 0 else 0
            _nl[0] = c
            return c
    else:
        c = 0
        def inner(b:int) -> int:
            nonlocal c
            if b == 0:
                c ^= 1 #toggle
            return c
    return inner

def create_unnrzi():
    #process the bit stream bit-by-bit with closure
    if IS_UPY:
        c = 1
        nl = array('B', [c])
        @micropython.viper
        def inner(b:int) -> int:
            nonlocal nl
            _nl = ptr8(nl)
            c:int      = _nl[0]
            r:int      = 0
            if b == c:
                r = 1
            _nl[0] = b # c = b
            return r
    else:
        c = 1
        def inner(b):
            nonlocal c
            r = 0
            if b == c:
                r = 1
            c = b
            return r
    return inner

CORRELATOR_DELAY = 446e-6
def create_corr(ts,):
    if IS_UPY:
        delay = int(round(CORRELATOR_DELAY/ts)) #correlator delay (index)
        idx = 0
        _dat = array('i', (0 for x in range(delay)))
        _c = array('i',[idx, delay])

        if HAS_C and False:
            # C OPTIMIZED
            @micropython.viper
            def inner(v:int)->int:
                nonlocal _dat, _c
                dat = ptr32(_dat) # indexing ALWAYS return UINT
                c = ptr32(_c)
                idx:int = c[0]
                delay:int = c[1]
                # o = v*dat[idx] # !!!! DOES NOT work, dat[idx] is always uint32
                d:int = int(uint_to_int(dat[idx])) # cast to int32
                o:int = int(isqrt(abs(v*d))) * int(sign(v)) * int(sign(d))
                dat[idx] = v
                c[0] = (idx+1)%delay # c[0] = idx
                return o
        else:
            # VIPER OPTIMIZED
            @micropython.viper
            def inner(v:int)->int:
                nonlocal _dat, _c
                dat = ptr32(_dat) # indexing ALWAYS return UINT
                c = ptr32(_c)
                idx:int = c[0]
                delay:int = c[1]
                v >>= 2 # shift to prevent overflow, do this as we don't have a isqrt viper yet TODO!
                # o = v*dat[idx]       # !!!! DOES NOT work, dat[idx] is always uint32
                d:int = int(_dat[idx]) # get int value from array
                o:int = v*d 
                dat[idx] = v
                c[0] = (idx+1)%delay # c[0] = idx
                return o
    else:
        # PYTHON
        delay = int(round(CORRELATOR_DELAY/ts)) #correlator delay (index)
        dat = array('i', (0 for x in range(delay)))
        idx = 0
        def inner(v:int)->int:
            nonlocal idx,dat,delay
            # o = v*dat[idx]
            o = isqrt(abs(v*dat[idx])) * sign(v) * sign(dat[idx])
            dat[idx] = v
            idx = (idx+1)%delay
            return o
    return inner

def create_fir(coefs, scale):
    if IS_UPY:
        if HAS_C and False:
            # C OPTIMIZED
            from cvec import fir_core
            ncoefs = len(coefs)
            coefs = array('i', (coefs[i] for i in range(ncoefs)))
            buf = array('i', (0 for x in range(ncoefs)))
            idx = 0
            scale = scale or 1
            def inner(v:int)->int:
                nonlocal ncoefs, coefs, buf, idx, scale
                idx, o = fir_core(coefs, buf, v, idx, scale) # CALL C
                # eprint(o)
                return o
        else:
            # VIPER OPTIMIZED
            ncoefs = len(coefs)
            _coefs = array('i', (coefs[i] for i in range(ncoefs)))
            _buf = array('i', (0 for x in range(ncoefs)))
            idx = 0
            scale = scale or 1
            _c = array('i',[idx, scale, ncoefs])

            @micropython.viper
            def inner(v:int)->int:
                nonlocal _coefs, _buf, _c

                buf = ptr32(_buf)     # indexing ALWAYS return uint
                coefs = ptr32(_coefs) # indexing ALWAYS return uint
                c = ptr32(_c)
                idx:int = c[0]
                scale:int = c[1]
                ncoefs:int = c[2]

                buf[idx] = v # ok, can assign negative number
                o:int = 0
                for i in range(ncoefs):
                    # cast to negatives
                    # index directy from the array.array
                    x:int = int(_buf[(idx-i)%ncoefs])
                    y:int = int(_coefs[i])
                    o += (x * y) // scale
                idx = (idx+1)%ncoefs
                c[0] = idx
                # eprint(o)
                return o
    else:
        # PYTHON
        ncoefs = len(coefs)
        coefs = array('i', (coefs[i] for i in range(ncoefs)))
        buf = array('i', (0 for x in range(ncoefs)))
        idx = 0
        scale = scale or 1
        def inner(v:int)->int:
            nonlocal ncoefs, coefs, buf, idx, scale
            buf[idx] = v
            o = 0
            for i in range(ncoefs):
                o += (coefs[i] * buf[(idx-i)%ncoefs]) // scale
            idx = (idx+1)%ncoefs
            return o
    return inner

def lpf_fir_design(ncoefs,       # filter size
                   fa,           # cut-off f
                   fs,           # fs
                   width  = 400, #transition band size
                   aboost = 1,   #gain at on-set of cut-off
                   ):
    from scipy import signal
    coefs = signal.firls(ncoefs,
                        (0, fa,       fa+width, fs/2),
                        (1, aboost,   0,        0), 
                        fs=fs)
    coefs = [round(x*10000) for x in coefs]
    g = sum([coefs[i] for i in range(len(coefs))])
    return coefs,g

def bandpass_fir_design(ncoefs,            # filter size
                        fmark, fspace,     # mark/space frequencies
                        fs,                # fs
                        width=600,         # transition freqency begin/end
                        amark=1, aspace=1, # mark/space gain
                        ):
    from scipy import signal
    coefs = signal.firls(ncoefs,
                        (0, fmark-width, fmark, fspace, fspace+width, fs/2),
                        (0, 0,           amark, aspace, 0,            0), 
                        fs=fs)

    coefs = [round(x*10000) for x in coefs]
    g1 = sum([coefs[i]*math.cos(2*math.pi*fmark/fs*i) for i in range(len(coefs))])
    g2 = sum([coefs[i]*math.sin(2*math.pi*fspace/fs*i) for i in range(len(coefs))])
    g = int((abs(g1)+abs(g2))/2)
    return coefs,g

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
        try:
            buf[idx] = v
        except OverflowError:
            if v>0:
                buf[idx] = 0x7fffffff
            else:
                buf[idx] = -0x7fffffff
        if (buf[(idx-1)%buflen] > 0) != (buf[idx] > 0):
        # if (buf[(idx-1)%buflen] > 0) != (buf[idx] > 0) and\
           # (buf[(idx-1)%buflen] == buf[(idx-2)%buflen]):
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


