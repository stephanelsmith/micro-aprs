
import math
from utils import frange
from array import array

import matplotlib.pyplot as plt
from scipy import signal


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

fs = 22050
ts = 1/fs
fmark = 1200
tmark = 1/fmark
fspace = 2200
tspace = 1/fspace
fcenter = 1700
T = tmark*50
nmark = int(tmark/ts)


ncoefsbaud = 2
ncoefs = int(nmark*ncoefsbaud) if int(nmark*ncoefsbaud)%2==1 else int(nmark*ncoefsbaud)+1

wid = 200
coefs = signal.firls(ncoefs,
                     (0, fmark-wid, fmark, fspace, fspace+wid, fs/2),
                     (0, 0,         1,     1,      0,          0), 
                     fs=fs)
print(coefs)
g = sum(coefs)
print(g)
coefs = [round(x*10000) for x in coefs]
print(coefs)
g1 = sum([coefs[i]*math.cos(2*math.pi*1200/fs*i) for i in range(len(coefs))])
g2 = sum([coefs[i]*math.sin(2*math.pi*2200/fs*i) for i in range(len(coefs))])
g = (abs(g1)+abs(g2))/2
print(g1,g2,g)

fir = create_fir(coefs = coefs,
                 scale = g,
                 )

xs   = list(frange(0,T,ts))
idxs   = list(range(len(xs)))

fig, axs = plt.subplots(4,1)
y1   = [int((2**8-1)*math.sin(xs[i]*fmark*2*math.pi)) for i in idxs]
y2   = [fir(y1[i]) for i in range(len(xs))]
axs[0].plot(xs,y1)
axs[0].plot(xs,y2)
axs[0].title.set_text('fmark')

y1   = [int((2**8-1)*math.sin(xs[i]*fspace*2*math.pi)) for i in idxs]
y2   = [fir(y1[i]) for i in range(len(xs))]
axs[1].plot(xs,y1)
axs[1].plot(xs,y2)
axs[1].title.set_text('fspace')

y1   = [int((2**8-1)*math.sin(xs[i]*400*2*math.pi)) for i in idxs]
y2   = [fir(y1[i]) for i in range(len(xs))]
axs[2].plot(xs,y1)
axs[2].plot(xs,y2)
axs[2].title.set_text('700')

y1   = [int((2**8-1)*math.sin(xs[i]*2700*2*math.pi)) for i in idxs]
y2   = [fir(y1[i]) for i in range(len(xs))]
axs[3].plot(xs,y1)
axs[3].plot(xs,y2)
axs[3].title.set_text('2700')






ncoefsbaud = 2
ncoefs = int(nmark*ncoefsbaud) if int(nmark*ncoefsbaud)%2==1 else int(nmark*ncoefsbaud)+1

wid = 200
coefs = signal.firls(ncoefs,
                     (0, fmark, fmark+wid, fs/2),
                     (1, 1,     0,         0), 
                     fs=fs)
print(coefs)
g = sum(coefs)
print(g)
coefs = [round(x*10000) for x in coefs]
print(coefs)
g = sum([coefs[i]*math.cos(2*math.pi*0/fs*i) for i in range(len(coefs))])
print(g)

fir = create_fir(coefs = coefs,
                 scale = g,
                 )

xs   = list(frange(0,T,ts))
idxs   = list(range(len(xs)))

fig, axs = plt.subplots(4,1)
y1   = [int((2**8-1)*math.sin(xs[i]*fmark*2*math.pi)) for i in idxs]
y2   = [fir(y1[i]) for i in range(len(xs))]
axs[0].plot(xs,y1)
axs[0].plot(xs,y2)
axs[0].title.set_text('fmark')

y1   = [int((2**8-1)*math.sin(xs[i]*fspace*2*math.pi)) for i in idxs]
y2   = [fir(y1[i]) for i in range(len(xs))]
axs[1].plot(xs,y1)
axs[1].plot(xs,y2)
axs[1].title.set_text('fspace')

y1   = [int((2**8-1)*math.sin(xs[i]*400*2*math.pi)) for i in idxs]
y2   = [fir(y1[i]) for i in range(len(xs))]
axs[2].plot(xs,y1)
axs[2].plot(xs,y2)
axs[2].title.set_text('700')

y1   = [int((2**8-1)*math.sin(xs[i]*2700*2*math.pi)) for i in idxs]
y2   = [fir(y1[i]) for i in range(len(xs))]
axs[3].plot(xs,y1)
axs[3].plot(xs,y2)
axs[3].title.set_text('2700')

plt.show()





