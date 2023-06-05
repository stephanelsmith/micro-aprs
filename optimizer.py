
import re
import asyncio
from subprocess import Popen, PIPE
from multiprocessing import Pool
from multiprocessing import cpu_count
from json import dumps

async def decode_async(raw_file = 'test/ISSpkt.raw', 
                       options = {}):
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
                options = {}):
    cmd = 'python demod.py -o {} -t raw {}'.format(
        dumps(options).replace(' ',''),
        raw_file,
    )
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

def f(x,y):
    return x+y

async def main():
    options = {
            'bandpass_width'  : 600,
            'bandpass_amark'  : 1,
            'bandpass_aspace' : 1,
            'lpf_width'       : 400,
            'lpf_aboost'      : 1,
    }
    # raw_file = 'test/ISSpkt.raw'
    raw_file = 'test/tnc_test02.raw'
    # await decode_async(raw_file = raw_file,
                       # options = options)
    # decode_sync(raw_file = raw_file,
                # options = options)

    tests = [(raw_file, options) for x in range(10)]
    with Pool(cpu_count()) as p:
        rs = p.starmap(decode_sync, tests)
    print(rs)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

