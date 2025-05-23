
import math
from array import array
import struct
import builtins

from lib.utils import eprint
from lib.compat import IS_UPY, HAS_C, HAS_VIPER

# viper functions needs to be in a different file, micropython workaround
# for architectures that don't support viper like raspberry pi

if IS_UPY:
    import micropython
    if HAS_C:
        from cdsp import isqrt
        from cdsp import sign
    else:
        from math import sqrt
        def isqrt(x):
            return int(sqrt(x))
else:
    try:
        from math import isqrt
    except ImportError:
        from math import sqrt
        def isqrt(x):
            return int(sqrt(x))
    def sign(a:int)->int:
        return (a > 0) - (a < 0)

if IS_UPY and HAS_C:
    from cdsp import utoi32
    from cdsp import utoi16
elif IS_UPY and HAS_VIPER:
    @micropython.viper
    def utoi32(u:int)->int:
        if u <= int(0x7FFFFFFF):
            return int(u)
        else:
            return int(u) - int(0x100000000)
else:
    def utoi32(u32:int)->int:
        if u32 <= 0x7FFFFFFF:
            return u32
        else:
            return u32 - 0x100000000

# 2 bytes input (formated as either u16 or s16), conversion to integer (unsigned shifted)
if IS_UPY and HAS_C:
    from cdsp import bu16toi
elif IS_UPY:
    def bu16toi(b:bytes)->int:
        # s = 32768 if shift else 0
        return struct.unpack('<H', b)[0] - 32768
        # return int.from_bytes(b, 'little') - s
else:
    def bu16toi(b)->int:
        # s = 32768 if shift else 0
        return int.from_bytes(b, 'little', signed=False) - 32768
if IS_UPY and HAS_C:
    from cdsp import bs16toi
elif IS_UPY:
    def bs16toi(b:bytes)->int:
        return struct.unpack('<h', b)[0]
else:
    def bs16toi(b)->int:
        return int.from_bytes(b, 'little', signed=True)

if IS_UPY and HAS_VIPER:
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


if IS_UPY and HAS_VIPER:
    @micropython.viper
    def afsk_detector(arr:ptr32, size:int)->bool:
        pol:int = 1 #polarity of the run we are currently tracking
        run:int = 0 #current run count (number of consecutive pos/neg samples)
        act:int = 0 #count of the number of runs we've seen above a threshold
        for i in range(size):
            # v:int = arr[i] # WARN, THIS IS ALWAYS U32 (POSITIVE VALUE)
            # v:int = int(utoi32(arr[i]))
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

if IS_UPY and HAS_VIPER:
    def create_nrzi():
        #process the bit stream bit-by-bit with closure
        c:int = 0
        # nl = array('B', [c])
        @micropython.viper
        def inner(b:int) -> int:
            nonlocal c
            # _nl = ptr8(nl)
            _c:int      = int(c)
            if b == 0:
                _c = 1 if _c == 0 else 0
            c = (_c<<1)|1 # INTEGER TO OBJECT HACK
            return _c
        return inner
else:
    def create_nrzi():
        c = 0
        def inner(b:int) -> int:
            nonlocal c
            if b == 0:
                c ^= 1 #toggle
            return c
        return inner

if IS_UPY and HAS_VIPER:
    def create_unnrzi():
        #process the bit stream bit-by-bit with closure
        c:int = 1
        # nl = array('B', [c])
        @micropython.viper
        def inner(b:int) -> int:
            nonlocal c
            # _nl = ptr8(nl)
            # c:int      = _nl[0]
            _c:int = int(c)
            _r:int = 0
            if b == _c:
                _r = 1
            # _nl[0] = b # c = b
            _c = b
            c = (_c<<1)|1 # INTEGER TO OBJECT HACK
            return _r
        return inner
else:
    def create_unnrzi():
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
if IS_UPY and HAS_C:
    def create_corr(ts,):
        delay:int = int(round(CORRELATOR_DELAY/ts)) #correlator delay (index)
        i:int = 0
        dat = array('i', (0 for x in range(delay)))
        # C OPTIMIZED
        @micropython.viper
        def inner(v:int)->int:
            nonlocal i
            _dat = ptr32(dat) # indexing ALWAYS return UINT
            _i:int = int(i)
            _delay:int = int(delay)
            # o = v*dat[idx] # !!!! DOES NOT work, dat[idx] is always uint32
            _d:int = int(utoi32(_dat[_i])) # cast to int32
            _o:int = int(isqrt(abs(v*_d))) * int(sign(v)) * int(sign(_d))
            _dat[_i] = v
            _i = (_i+1)%_delay # c[0] = idx
            i = (_i<<1)|1 # INTEGER TO OBJECT HACK
            return _o
        return inner
elif IS_UPY and HAS_VIPER:
    # VIPER OPTIMIZED
    def create_corr(ts,):
        delay:int = int(round(CORRELATOR_DELAY/ts)) #correlator delay (index)
        i:int = 0
        dat = array('i', (0 for x in range(delay)))
        @micropython.viper
        def inner(v:int)->int:
            nonlocal i
            _dat = ptr32(dat) # indexing ALWAYS return UINT
            _i:int = int(i)
            _delay:int = int(delay)
            v >>= 2 # shift to prevent overflow, do this as we don't have a isqrt viper yet TODO!
            # o = v*dat[idx]       # !!!! DOES NOT work, dat[idx] is always uint32
            _d:int = int(_dat[_i]) # get int value from array
            _o:int = v*_d 
            _dat[_i] = v
            _i = (_i+1)%_delay
            i = (_i<<1)|1 # INTEGER TO OBJECT HACK`
            return _o
        return inner
else:
    # PYTHON
    def create_corr(ts,):
        delay = int(round(CORRELATOR_DELAY/ts)) #correlator delay (index)
        dat = array('i', (0 for x in range(delay)))
        i = 0
        def inner(v:int)->int:
            nonlocal i
            # o = v*dat[i]
            o = isqrt(abs(v*dat[i])) * sign(v) * sign(dat[i])
            dat[i] = v
            i = (i+1)%delay
            return o
        return inner

if IS_UPY and HAS_C:
    def create_power_meter(siz:int,):
        from cdsp import power_meter_core
        buf = array('i', (0 for x in range(siz)))
        i:int = 0
        @micropython.viper
        def inner(v:int)->int:
            nonlocal i
            _o:int = int(power_meter_core(buf, v, i))
            _i:int = (int(i)+1)%int(siz)
            i = (_i<<1)|1 # INTEGER TO OBJECT HACK
            return _o
        return inner
elif IS_UPY and HAS_VIPER:
    def create_power_meter(siz,):
        buf = array('i', (0 for x in range(siz)))
        i:int = 0
        @micropython.viper
        def inner(v:int)->int:
            nonlocal i
            _buf = ptr32(buf)     # indexing ALWAYS return uint
            _i:int = int(i)
            _siz:int = int(siz)
            _buf[_i] = v # ok, can assign negative number

            # find dc point
            _a:int = 0
            for j in range(_siz):
                _a += int(utoi32(_buf[j]))
            _a = _a//_siz

            _o:int = 0
            for j in range(_siz):
                _b:int = int(utoi32(_buf[j])) # cast to int32
                _b -= _a
                _o += _b*_b
            _o = int(isqrt(_o//_siz))
            _i = (_i+1)%_siz
            i = (_i<<1)|1 # INTEGER TO OBJECT HACK
            return _o
        return inner
else:
    def create_power_meter(siz,):
        buf = array('i', (0 for x in range(siz)))
        i = 0
        def inner(v:int)->int:
            nonlocal i
            buf[i] = v

            # find dc point
            a = 0
            for k in range(siz):
                a += buf[k]
            a //= siz

            o = 0
            for k in range(siz):
                b = buf[k]-a
                o += b*b
            o = isqrt(o//siz)
            i = (i+1)%siz
            return o
        return inner

if IS_UPY and HAS_C:
    def create_fir(coefs, scale):
        from cdsp import fir_core
        ncoefs:int = len(coefs)
        coefs = array('i', (coefs[i] for i in range(ncoefs)))
        buf = array('i', (0 for x in range(ncoefs)))
        i:int = 0
        scale:int = scale or 1
        @micropython.viper
        def inner(v:int)->int:
            nonlocal i
            # i, o = fir_core(coefs, buf, v, i, scale) # CALL C
            _o:int = int(fir_core(coefs, buf, v, i, scale)) # CALL C
            _i:int = (int(i)+1)%int(ncoefs)
            i = (_i<<1)|1 # INTEGER TO OBJECT HACK
            return _o
        return inner
elif IS_UPY and HAS_VIPER:
    def create_fir(coefs, scale):
        ncoefs:int = len(coefs)
        coefs = array('i', (coefs[i] for i in range(ncoefs)))
        buf = array('i', (0 for x in range(ncoefs)))
        i:int = 0
        scale = scale or 1
        @micropython.viper
        def inner(v:int)->int:
            nonlocal i

            _buf = ptr32(buf)     # indexing ALWAYS return uint
            _coefs = ptr32(coefs) # indexing ALWAYS return uint
            _i:int = int(i)
            _scale:int = int(scale)
            _ncoefs:int = int(ncoefs)

            _buf[_i] = v # ok, can assign negative number
            _o:int = 0
            for j in range(_ncoefs):
                # cast to negatives
                # index directy from the array.array
                _x:int = int(buf[(_i-j)%_ncoefs])
                _y:int = int(coefs[j])
                _o += (_x * _y) // _scale
            _i = (_i+1)%_ncoefs
            i = (_i<<1)|1 # INTEGER TO OBJECT HACK
            return _o
        return inner
else:
    def create_fir(coefs, scale):
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
    try:
        from scipy import signal
    except ImportError:
        raise Exception('Missing LPF FIR coefficients.  Re-run with python with scipy to generate coefs.')
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
    try:
        from scipy import signal
    except ImportError:
        raise Exception('Missing Bandpass FIR coefficients.  Re-run with python with scipy to generate coefs.')
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
