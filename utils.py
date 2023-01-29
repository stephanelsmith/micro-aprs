

import sys
import math
from pydash import py_ as _

def parse_args(argdefs):
    args = {}
    for arg,argdef in argdefs.items():
        idx = _.find_index(sys.argv, lambda arg: arg == '--'+arg or arg == '-'+argdef['short'])
        args[arg] = argdef['default']
        if idx >= 0:
            if argdef['type'] == bool:
                args[arg] = True
            else:
                args[arg] = argdef['type'](sys.argv[idx+1])
    return args

# integer division + ceil operation
# used in place of int(math.ceil(total_size/chunk_size))
def int_div_ceil(total_size, chunk_size):
    # return total_size//chunk_size + (bool(total_size%chunk_size))
    return total_size//chunk_size + (1 if total_size%chunk_size else 0)

def pretty_binary(mv, cols=10):
    for ridx in range(0,len(mv),cols):
        #byte number
        print(str(ridx).zfill(4),' ',end='') 
        #hex
        for idx in range(ridx,ridx+cols):
            v = hex(mv[idx])[2:].zfill(2) if idx<len(mv) else '--'
            print(v,end=' ')
        print('  ',end='')
        #binary
        for idx in range(ridx,ridx+cols):
            for b in range(8):
                if idx<len(mv):
                    v = 1 if (0x80>>b) & mv[idx] else 0
                else:
                    v = '-'
                print(v,end='')
            print(' ',end='')
        print('  ',end='')
        #string
        for idx in range(ridx,ridx+cols):
            v = chr(mv[idx]) if idx<len(mv) else '-'
            print(v,end='')
        print()

def format_bytes(mv):
    o = ''
    for idx in range(len(mv)):
        o += hex(mv[idx])[2:].zfill(2)
        o += ' '
    return o
def format_bits(mv):
    o = ''
    for idx in range(len(mv)):
        for b in range(8):
            o += '1' if (0x80>>b)&mv[idx] else '0'
        o += ' '
    return o

def reverse_byte(_byte):
    #xor reverse bit technique
    _byte = ((_byte & 0x55) << 1) | ((_byte & 0xAA) >> 1);
    _byte = ((_byte & 0x33) << 2) | ((_byte & 0xCC) >> 2);
    _byte = ((_byte & 0x0F) << 4) | ((_byte & 0xF0) >> 4);
    return _byte

def assign_bit(byte, idx, value):
    mask = (0x80>>(idx%8))
    if value:
        return byte | mask
    else:
        return byte & (mask ^ 0xff)
def get_bit(byte, idx):
    mask = (0x80)>>(idx%8)
    return (byte & mask) >> ((8-idx-1)%8)

def frange(start, stop, step, rnd=None):
    n = int(math.ceil((stop - start) / step))
    if isinstance(rnd,int):
        for i in range(n):
            yield round(start+i*step,rnd)
    else:
        for i in range(n):
            yield start+i*step
