

@micropython.viper
def clamps16(o:int) -> int:
    if o > 32767:
        return 32767
    if o < -32768:
        return -32768
    return o

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

@micropython.viper
def nrzi_inner(b:int) -> int:
    nonlocal nl
    _nl = ptr8(nl)
    c:int      = _nl[0]
    if b == 0:
        c = 1 if c == 0 else 0
    _nl[0] = c
    return c

@micropython.viper
def unnrzi_inner(b:int) -> int:
    nonlocal nl
    _nl = ptr8(nl)
    c:int      = _nl[0]
    r:int      = 0
    if b == c:
        r = 1
    _nl[0] = b # c = b
    return r

@micropython.viper
def corr_inner_c(v:int)->int:
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

@micropython.viper
def corr_inner(v:int)->int:
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

@micropython.viper
def fir_inner(v:int)->int:
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
