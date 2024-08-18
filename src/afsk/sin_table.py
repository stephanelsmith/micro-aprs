
import math
from array import array
from afsk.func import frange

def get_sin_table(size   = 1024, 
                  signed = True,
                  ):
    if signed:
        # signed version [-32768,32767]
        return array('h', (int((0x7fff)*math.sin(x)) for x in frange(0,2*math.pi,2*math.pi/size)))
    else:
        # unsigned, [0,65535]
        return array('H', (int(0x7fff+0x7fff*math.sin(x)) for x in frange(0,2*math.pi,2*math.pi/size)))
