

import sys
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


def print_byte(b):
    print_binary([b])

def print_binary(mv):
    for idx in range(len(mv)*8):
        if idx%8==0:
            print('{} {} {} 0x{} '.format(str(idx//8).zfill(4), str(idx).zfill(4), chr(mv[idx//8]), hex(mv[idx//8])[2:].zfill(2)), end='')
        if idx%8==4:
            print(' ', end='')
        print(1 if mv[idx//8] & (0x80>>(idx%8)) else 0, end='')
        if idx%8==7:
            print('')

def reverse_byte(_byte):
    #xor reverse bit technique
    _byte = ((_byte & 0x55) << 1) | ((_byte & 0xAA) >> 1);
    _byte = ((_byte & 0x33) << 2) | ((_byte & 0xCC) >> 2);
    _byte = ((_byte & 0x0F) << 4) | ((_byte & 0xF0) >> 4);
    return _byte
