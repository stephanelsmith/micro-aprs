
import sys
from json import loads

def mod_parse_args(args):
    r = {
        'args' : {
            'verbose' : False,
            'quiet'   : False,
            'rate'    : 22050,
            'vox'     : False,
            'options' : {},
        },
        'in' : {
            # 'type' : 'aprs',
            'file'  : '-', #from stdin
        },
        'out' : {
            # 'type' : 'raw',
            'file'  : '-', #to stdout
        },
    }

    if '-h' in args or '--help' in args or '-help' in args:
        print('''APRS MOD
(C) Stephane Smith (KI5TOF) 2024

Usage: 
aprs_mod.py [options] (-t outfile) (-t infile)
aprs_mod.py [options] (-t infile)
aprs_mod.py [options]
aprs_mod.py

OPTIONS:
-r, --rate       22050 (default)
-vox, --vox      Vox mode, pad header flags to activate radio vox
-v, --verbose    verbose intermediate output to stderr

-t INPUT TYPE OPTIONS:
intype       aprs strings
infile       '-' (default)

-t OUTPUT TYPE OPTIONS:
outtype       raw 16 bit samples
outfile       '-' (default) | 'null' (no output) | '*.wav' (wave file) | 'play' play audio
''')
        return

    argstr = ' '.join(args)
    spl = [x.split() for x in ' '.join(args).split('-t')]
    try:
        #general args
        args = spl.pop(0)
        if '--rate' in args:
            r['args']['rate'] = get_arg_val(args, '--rate', int)
        if '-r' in args:
            r['args']['rate'] = get_arg_val(args, '-r', int)
        r['args']['vox'] = True if '-vox' in args or '--vox' in args else False
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
    if len(spl) == 2:
        try:
            _out = spl.pop(0)
            # r['out']['type'] = _out[0]
            r['out']['file'] = _out[-1]
        except IndexError:
            pass
    try:
        _in = spl.pop(0)
        # r['in']['type'] = _in[0]
        r['in']['file'] = _in[-1]
    except IndexError:
        pass
    return r

def demod_parse_args(args):
    r = {
        'args' : {
            'verbose' : False,
            'quiet'   : False,
            'rate'    : 22050,
            'options' : {},
        },
        'in' : {
            # 'type' : 'raw',
            'file'  : '-', #from stdin
        },
        'out' : {
            # 'type' : 'aprs',
            'file'  : '-', #to stdout
        },
    }

    if '-h' in args or '--help' in args:
        print('''APRS DEMOD
(C) Stephane Smith (KI5TOF) 2023

Usage: 
aprs_demod.py [options] (-t outfile) (-t infile)
aprs_demod.py [options] (-t infile)
aprs_demod.py [options]
aprs_demod.py

OPTIONS:
-r, --rate       22050 (default)
-v, --verbose    verbose intermediate output to stderr

-t INPUT TYPE OPTIONS:
intype       'raw' 16 bit signed samples
infile       '-' (default stdin) | 'filename.raw' raw file | 'rtl_fm' input from rtl_fm

-t OUTPUT TYPE OPTIONS:
outtype       'aprs' strings
outfile       '-' (default stdout)
''')
        exit()

    argstr = ' '.join(args)
    spl = [x.split() for x in ' '.join(args).split('-t')]
    try:
        #general args
        args = spl.pop(0)
        if '-rate' in args:
            r['args']['rate'] = get_arg_val(args, '-rate', int)
        if '-r' in args:
            r['args']['rate'] = get_arg_val(args, '-r', int)
        if '-v' in args or '-verbose' in args:
            r['args']['verbose'] = True
        if '-o' in args:
            r['args']['options'] = loads(get_arg_val(args, '-o', str))
            # print('OPTIONS:{}'.format(r['args']['options']))
    except IndexError:
        pass
    if len(spl) == 2:
        try:
            _out = spl.pop(0)
            # r['out']['type'] = _out[0]
            r['out']['file'] = _out[-1]
        except IndexError:
            pass
    try:
        _in = spl.pop(0)
        # r['in']['type'] = _in[0]
        r['in']['file'] = _in[-1]
    except IndexError:
        pass
    return r

def is_parse_args(args):
    r = {
        'args' : {
            'call'      : 'KI5TOF',
            'passcode'  : '17081',
            'lat'       : None,
            'lon'       : None,
            'msg'       : None,
            'log_file'  : 'aprs.log',
        },
    }
    try:
        #general args
        if '-h' in args or '--help' in args or len(args)==1:
            print('''APRS IS GATEWAY
(C) Stephane Smith (KI5TOF) 2023

Usage: python aprs_is.py [OPTIONS]
aprs_is.py sends aprs commands from stdin to aprs is servers.

OPTIONS:
    -c, --call         APRS call sign
    -p, --passcode     APRS passcode (https://apps.magicbug.co.uk/passcode/)
    -lat               Beacon lat (decimal notation)
    -lon               Beacon lon (decimal notation)
    -msg               Beacon message, default: micro-aprs-modem 144.390MHz rx only APRS iGate
    -log_file          Save APRS messages received to log
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
        if '-lat' in args:
            r['args']['lat'] = get_arg_val(args, '-lat', float)
        if '-lon' in args:
            r['args']['lon'] = get_arg_val(args, '-lon', float)
        if '-msg' in args:
            r['args']['msg'] = args[args.index('-msg')+1:]
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

