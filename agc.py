
import math
from utils import frange
from array import array

import matplotlib.pyplot as plt


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

fs = 22050
ts = 1/fs
fmark = 1200
tmark = 1/fmark
T = tmark*50


famp = 50
tamp = 1/famp

agc = create_agc(sp = 2**12,
                 depth = int(tmark/ts),
                 )

xs   = list(frange(0,T,ts))
y1   = [int((2**8-1)*math.sin(x*fmark*2*math.pi)) for x in xs]
y3   = [agc(y1[i]) for i in range(len(xs))]

plt.plot(xs,y1)
plt.plot(xs,y3)
plt.show()





