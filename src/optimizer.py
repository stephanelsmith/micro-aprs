#!python

import re
import asyncio
from subprocess import Popen, PIPE
from multiprocessing import Pool
from multiprocessing import cpu_count
from json import dumps
from copy import deepcopy
import lib.upydash as _

# async def decode_async(raw_file = 'test/ISSpkt.raw', 
                       # options = {},
                       # ):
    # print('DECODE SYNC')
    # cmd = 'python aprs_demod.py -o {} -t raw {}'.format(
        # dumps(options).replace(' ',''),
        # raw_file,
    # )
    # p = await asyncio.subprocess.create_subprocess_exec(
            # cmd.split()[0], *cmd.split()[1:],
			# stdout=asyncio.subprocess.PIPE,
			# )
    # count = 0
    # while True:
        # d = await p.stdout.readline()
        # if not d:
            # break
        # msg = d.decode().strip()
        # m = re.match('\d+:', msg)
        # if m:
            # count += 1
            # print('{} {}'.format(count, msg), flush=True)
        # else:
            # print('{}'.format(msg), flush=True)
    # print(' === DECODED {} FRAMES === '.format(count))
    # return count

def decode_sync(raw_file = 'test/ISSpkt.raw', 
                options = {},
                ):
    # cmd = 'python aprs_demod.py -o {} -t raw {}'.format(
    cmd = 'pypy3 aprs_demod.py -o \'{}\' -t raw {}'.format(
        dumps(options).replace(' ',''),
        raw_file,
    )
    print(cmd)
    p = Popen(cmd.split(),
              stdout = PIPE,
              )
    count = 0
    while True:
        d = p.stdout.readline()
        if not d:
            break
        msg = d.decode().strip()
        m = re.match('^\[\d+\]', msg)
        if m:
            count += 1
            print('{}'.format(msg), flush=True)
        else:
            print('{}'.format(msg), flush=True)
    print(' === DECODED {} FRAMES === '.format(count))
    return count

async def memoize_firs(argss):
    from afsk.func import lpf_fir_design
    from afsk.func import bandpass_fir_design
    from lib.memoize import memoize_dumps
    sampling_rate = 22050
    fmark = 1200
    tmark = 1/fmark
    fspace = 2200
    tspace = 1/fspace
    fs = sampling_rate
    ts = 1/fs
    fbaud = 1200
    tbaud = 1/fbaud
    for args in argss:
        options = args[1]
        print('optimizer','memoize',options)
        nmark = int(tmark/ts)
        bandpass_ncoefsbaud = options['bandpass_ncoefsbaud']
        bandpass_ncoefs = int(nmark*bandpass_ncoefsbaud) if int(nmark*bandpass_ncoefsbaud)%2==1 else int(nmark*bandpass_ncoefsbaud)+1
        bandpass_width = options['bandpass_width']
        bandpass_amark = options['bandpass_amark']
        bandpass_aspace = options['bandpass_aspace']
        coefs,g = bandpass_fir_design(ncoefs = bandpass_ncoefs,
                                        fmark  = fmark,
                                        fspace = fspace,
                                        fs     = fs,
                                        width  = bandpass_width,
                                        amark  = bandpass_amark,
                                        aspace = bandpass_aspace,
                                        )
        memoize_dumps('bpf', (coefs,g), fmark, fspace, fs,
                                        bandpass_ncoefs,
                                        bandpass_width, 
                                        bandpass_amark, 
                                        bandpass_aspace)
        nmark = int(tmark/ts)
        lpf_ncoefsbaud = options['lpf_ncoefsbaud']
        lpf_ncoefs = int(nmark*lpf_ncoefsbaud) if int(nmark*lpf_ncoefsbaud)%2==1 else int(nmark*lpf_ncoefsbaud)+1
        lpf_width = options['lpf_width']
        lpf_aboost = options['lpf_aboost']
        lpf_f = options['lpf_f']
        coefs,g = lpf_fir_design(ncoefs = lpf_ncoefs,
                                    fa     = lpf_f,
                                    fs     = fs,
                                    width  = lpf_width,
                                    aboost = lpf_aboost,
                                    )
        memoize_dumps('lpf', (coefs,g), lpf_f, fs,
                                        lpf_ncoefs, 
                                        lpf_width, 
                                        lpf_aboost)



async def main():
    testdefs = {
            'bandpass_ncoefsbaud' : [5],
            'bandpass_width'      : [400],
            'bandpass_amark'      : [2],
            'bandpass_aspace'     : [3],
            'lpf_ncoefsbaud'      : [5],
            'lpf_f'               : [800],
            'lpf_width'           : [250],
            'lpf_aboost'          : [3],
            'squelch'             : range(50,200,20),
    }
    # raw_file = 'test/ISSpkt.raw'
    raw_file = 'test/tnc_test02.raw'
    
    tests = []

    #generate tests, all premutations
    for k,vs in testdefs.items():
        _tests   = deepcopy(tests)
        tests = []
        for v in vs:
            p = deepcopy(_tests) if len(_tests)>0 else [{}]
            for test in p:
                test.update({k:v})
                tests.append(test)

    # #generate tests, item-by-item
    # for k,vs in testdefs.items():
        # for v in vs:
            # tests.append({k:v})
    
    argss = _.map(tests, lambda options: (raw_file, options))

    #memoize all the fir coefs, pypy3 doesn't have scipy
    await memoize_firs(argss)

    with Pool(cpu_count()) as p:
        rs = p.starmap(decode_sync, argss)
    os = []
    for r,test in zip(rs,tests):
        os.append((r,test))
    os = _.sort_by(os, lambda o:o[0])
    with open('r.txt','w') as f:
        for o in os:
            print(o)
            f.write('{} - {}\n'.format(o[0],o[1]))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

