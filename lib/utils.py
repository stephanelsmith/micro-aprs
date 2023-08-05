
import sys
import math


# integer division + ceil operation
# used in place of int(math.ceil(total_size/chunk_size))
def int_div_ceil(total_size, chunk_size):
    # return total_size//chunk_size + (bool(total_size%chunk_size))
    return total_size//chunk_size + (1 if total_size%chunk_size else 0)

def pretty_binary(mv, 
                  cols      = 8, 
                  to_stderr = True):
    if to_stderr:
        _print = eprint
    else:
        _print = print
    for ridx in range(0,len(mv),cols):
        #byte number
        _print('{:04}'.format(ridx),' ',end='') 
        #hex
        for idx in range(ridx,ridx+cols):
            v = '{:02x}'.format(mv[idx]) if idx<len(mv) else '--'
            _print(v,end=' ')
        _print('  ',end='')
        #binary
        for idx in range(ridx,ridx+cols):
            for b in range(8):
                if idx<len(mv):
                    v = 1 if (0x80>>b) & mv[idx] else 0
                else:
                    v = '-'
                _print(v,end='')
            _print(' ',end='')
        _print('  ',end='')
        #string
        for idx in range(ridx,ridx+cols):
            if idx<len(mv) and mv[idx]>=32 and mv[idx]<=127:
                _print(chr(mv[idx]),end='')
            else:
                _print('-',end='')
        _print()

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


def assign_bit(byte, idx, value):
    mask = (0x80>>(idx%8))
    if value:
        return byte | mask
    else:
        return byte & (mask ^ 0xff)
def get_bit(byte, idx):
    mask = (0x80)>>(idx%8)
    return (byte & mask) >> ((8-idx-1)%8)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

