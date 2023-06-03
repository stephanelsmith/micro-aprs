
import re
import asyncio
from subprocess import Popen, PIPE
from json import dumps

async def iterate():
    cmd = 'python demod.py -o {} -t raw test/tnc_test02.raw'.format(
        dumps({"bandpass_width":600,"lpf_width":400}).replace(' ',''),
    )
    p = await asyncio.subprocess.create_subprocess_exec(
            cmd.split()[0], *cmd.split()[1:],
			# stdin=asyncio.subprocess.PIPE,
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
    print()
    print(' === DECODED {} FRAMES === '.format(count))
    print()

async def main():
    await iterate()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

