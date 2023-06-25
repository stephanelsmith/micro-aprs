#!python

import re
import asyncio
from subprocess import Popen, PIPE
from multiprocessing import Pool
from multiprocessing import cpu_count
from json import dumps
from copy import deepcopy
import lib.upydash as _

async def decode_async(raw_file = 'test/ISSpkt.raw', 
                       options = {},
                       ):
    cmd = 'python demod.py -o {} -t raw {}'.format(
        dumps(options).replace(' ',''),
        raw_file,
    )
    p = await asyncio.subprocess.create_subprocess_exec(
            cmd.split()[0], *cmd.split()[1:],
			stdout=asyncio.subprocess.PIPE,
			)
    count = 0
    while True:
        d = await p.stdout.readline()
        if not d:
            break
        msg = d.decode().strip()
        m = re.match('\d+:', msg)
        if m:
            count += 1
            print('{} {}'.format(count, msg), flush=True)
        else:
            print('{}'.format(msg), flush=True)
    print(' === DECODED {} FRAMES === '.format(count))
    return count

def decode_sync(raw_file = 'test/ISSpkt.raw', 
                options = {},
                ):
    cmd = 'python demod.py -o {} -t raw {}'.format(
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
        m = re.match('\d+:', msg)
        if m:
            count += 1
            print('{} {}'.format(count, msg), flush=True)
        else:
            print('{}'.format(msg), flush=True)
    print(' === DECODED {} FRAMES === '.format(count))
    return count

async def main():
    testdefs = {
            'bandpass_ncoefsbaud' : [4],
            'bandpass_width'      : [400],
            'bandpass_amark'      : [6],
            'bandpass_aspace'     : [3],
            'lpf_ncoefsbaud'      : [6],
            'lpf_f'               : [1000],
            'lpf_width'           : [200],
            'lpf_aboost'          : [3],
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

    # print(len(tests))
    
    argss = _.map(tests, lambda options: (raw_file, options))
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

