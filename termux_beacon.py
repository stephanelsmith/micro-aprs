
import traceback
import sys
from datetime import datetime
from subprocess import check_output

import asyncio
from asyncio import Event
from asyncio import Queue
import json

from lib.utils import eprint
from ax25.ax25 import AX25
from ax25.callssid import CallSSID
from lib.gps import aprs_gps_format

CALL = 'KI5TOF-9'
PASSCODE = '17081'

async def run(cmd):
    eprint(cmd)
    return await asyncio.to_thread(check_output, cmd.split())

async def start_termux():
    cmd = 'termux-api-start'
    r = await run(cmd)

async def set_volume(volume):
    cmd = 'termux-volume music {}'.format(volume)
    r = await run(cmd)
    return r

async def set_wake_lock():
    cmd = 'termux-wake-lock'
    r = await run(cmd)
    return r
async def set_wake_unlock():
    cmd = 'termux-wake-unlock'
    r = await run(cmd)
    return r

async def get_loc():
    try:
        while True:
            eprint('getting gps')
            r = await run('termux-location')
            d = json.loads(r.decode())
            eprint('latlon: {} {}'.format(d['latitude'], d['longitude']))

            aprs_loc = aprs_gps_format(lat = d['latitude'], 
                                       lon = d['longitude'],
                                       symbol1 = '/', # standard symbol set
                                       symbol2 = '>', # car,
                                       )
            msg = 'hello world'
            ax25 = AX25(src  = CALL,
                        dst  = 'APRS',
                        info = '={}{}'.format(aprs_loc, msg).encode(),
                        )
            eprint(ax25)
            print(ax25, flush=True)
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

async def main():
    #eprint('starting termux')
    #await start_termux()
    eprint('setting volume')
    await set_volume(100)
    tasks = []
    try:
        await set_wake_lock()
        tasks.append(asyncio.create_task(get_loc()))
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()
    finally:
        await set_wake_unlock()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
