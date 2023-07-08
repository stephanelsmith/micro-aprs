

import sys
import math
from json import loads


def parse_args(args):
    r = {
        'args' : {
            'verbose' : False,
            'quiet'   : False,
            'rate'    : 22050,
            'options' : {},
        },
        'in' : {
            'type' : 'raw',
            'file'  : '-', #from stdin
        },
        'out' : {
            'type' : 'raw',
            'file'  : '-', #to stdout
        },
    }
    argstr = ' '.join(args)
    spl = [x.split() for x in ' '.join(args).split('-t')]
    try:
        #general args
        args = spl.pop(0)
        if '-h' in args or '--help' in args or len(args)==1:
            print('''APRS MOD/DEMOD
Usage: 
aprs_mod/demod.py [GENERAL OPTIONS] -t [OUTPUT OPTIONS] -t [INPUT OPTIONS]
aprs_mod/demod.py [GENERAL OPTIONS] -t [INPUT OPTIONS]

GENERAL OPTIONS:
    -r, --rate       22050 (default)
    -v, --verbose    verbose mode to show intermediary steps
    -q, --quiet      suppress output, may be used with verbose

INPUT/OUTPUT OPTIONS:
    -t, --type       type, currently only supports 'raw'
    -f, --file       file input/output.  Default '-'
''')
            exit()
        if '-rate' in args:
            r['args']['rate'] = get_arg_val(args, '-rate', int)
        if '-r' in args:
            r['args']['rate'] = get_arg_val(args, '-r', int)
        if '-v' in args or '-verbose' in args:
            r['args']['verbose'] = True
        if '-q' in args or '-quiet' in args:
            r['args']['quiet'] = True
        if '-o' in args:
            r['args']['options'] = loads(get_arg_val(args, '-o'))
        if '-options' in args:
            r['args']['options'] = loads(get_arg_val(args, '-options'))
    except IndexError:
        pass
    types = ['raw']
    if len(spl) == 2:
        try:
            _out = spl.pop(0)
            r['out']['type'] = _out[0]
            if r['out']['type'] not in types:
                raise Exception('unknown type {}, not in {}'.format(r['out']['type'], types))
            r['out']['file'] = _out[-1]
        except IndexError:
            pass
    try:
        _in = spl.pop(0)
        r['in']['type'] = _in[0]
        if r['in']['type'] not in types:
            raise Exception('unknown type {}, not in {}'.format(r['in']['type'], types))
        r['in']['file'] = _in[-1]
    except IndexError:
        pass
    return r

def is_parse_args(args):
    r = {
        'args' : {
            'call'      : 'KI5TOF',
            'passcode'  : '17081',
        },
    }
    try:
        #general args
        if '-h' in args or '--help' in args or len(args)==1:
            print('''APRS IS GATEWAY
Usage: python aprs_is.py [OPTIONS]
aprs_is.py sends aprs commands from stdin to aprs is servers.

OPTIONS:
    -c, --call         APRS call sign
    -p, --passcode     APRS passcode (https://apps.magicbug.co.uk/passcode/)
''')
            exit()
        if '-p' in args:
            r['args']['passcode'] = get_arg_val(args, '-p', str)
        if '--passcode' in args:
            r['args']['passcode'] = get_arg_val(args, '--passcode', str)
        if '-c' in args:
            r['args']['call'] = get_arg_val(args, '-c', str)
        if '--call' in args:
            r['args']['call'] = get_arg_val(args, '--call', str)
    except IndexError:
        pass
    return r

def get_arg_val(args, arg, fn=None):
    try:
        if not fn:
            return args[args.index(arg)+1]
        else:
            return fn(args[args.index(arg)+1])
    except:
        None

# integer division + ceil operation
# used in place of int(math.ceil(total_size/chunk_size))
def int_div_ceil(total_size, chunk_size):
    # return total_size//chunk_size + (bool(total_size%chunk_size))
    return total_size//chunk_size + (1 if total_size%chunk_size else 0)

def pretty_binary(mv, 
                  cols      = 10, 
                  to_stderr = True):
    if to_stderr:
        _print = eprint
    else:
        _print = print
    for ridx in range(0,len(mv),cols):
        #byte number
        _print(str(ridx).zfill(4),' ',end='') 
        #hex
        for idx in range(ridx,ridx+cols):
            v = hex(mv[idx])[2:].zfill(2) if idx<len(mv) else '--'
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
            v = chr(mv[idx]) if idx<len(mv) else '-'
            v = v if v.isprintable() else '-'
            _print(v,end='')
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

