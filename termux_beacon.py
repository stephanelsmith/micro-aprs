
import traceback
import sys
from datetime import datetime
from subprocess import check_output

import asyncio
from asyncio import Event
from asyncio import Queue
import json

from ax25.ax25 import AX25
from ax25.callssid import CallSSID
from lib.gps import aprs_gps_format

CALL = 'KI5TOF'
PASSCODE = '17081'

async def run(cmd):
    return await asyncio.to_thread(check_output, *cmd.split())

async def start_termux():
    cmd = 'termux-api-start'
    r = await run(cmd)
    # print(r)

async def get_loc():
    try:
        # print('get_loc')
        while True:
            r = await run('termux-location')
            d = json.loads(r.decode())

            aprs_loc = aprs_gps_format(d['latitude'], d['longitude'])
            msg = 'bapfelpfannkuchen et un croque monsieur'
            ax25 = AX25(src  = CALL,
                        dst  = 'APRS',
                        info = '={}{}'.format(aprs_loc, msg).encode(),
                        )
            print(ax25, flush=True)
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

async def main():

    await start_termux()

    tasks = []
    try:
        tasks.append(asyncio.create_task(get_loc()))
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
