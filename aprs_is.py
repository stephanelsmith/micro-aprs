

import asyncio
import traceback
import sys

CALL = 'KI5TOF'
PASSCODE = '17081'

APRS_IS_HOST = 'rotate.aprs.net'
APRS_IS_FULL_FEED_PORT = 10152
APRS_IS_FILTER_PORT = 14580

#APRS
#connecting: https://www.aprs-is.net/Connecting.aspx
#filters: https://www.aprs-is.net/javAPRSFilter.aspx

#position: KI5TOF>APRS:=2941.97N/09545.01WChello world
#status:   KI5TOF>APRS:>QTH
#message:  KI5TOF>APRS::KI5TOF   :hello world

#https://aprs.fi/doc/guide/aprsfi-telemetry.html
#https://github.com/PhirePhly/aprs_notes/blob/master/telemetry_format.md
#specify parameter names and units
#telem:    KI5TOF>APRS::KI5TOF   :PARM.Title_A1,Title_B2,Title_C3,Title_D4,Title_E5,BIT_A1,BIT_B2,BIT_C3,BIT_D4,BIT_E5,BIT_F6,BIT_G7,BIT_H8
#telem:    KI5TOF>APRS::KI5TOF   :UNIT.Volt,Volt,Volt,Volt,Volt,B,B,B,B,B,B,B,B
#specify scaling ax^2+bx+c             a,b,c|a,b,c|a,b,c|a,b,c|a,b,c
#telem:    KI5TOF>APRS::KI5TOF   :EQNS.0,1,0,0,1,0,0,1,0,0,1,0,0,1,0
# sending data
#telem:    KI5TOF>APRS:T#000,1,2,3,4,5,01010101
#telem:    KI5TOF>APRS:T#002,10.12,20.23,30.45,40.67,50.89,10101010
#telem:    KI5TOF>APRS:T#003,110.12,120.23,130.45,140.67,150.89,10101010comment

async def ingress(reader):
    try:
        while True:
            data = await reader.read(1024)
            if data:
                print('<<<',data)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

async def egress(writer):
    login_str = 'user {} pass {} vers microax25afsk 0.0 filter p/{}'.format(
            CALL, PASSCODE, CALL)
    print(login_str)
    try:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        while True:
            line = await reader.readline()
            line = line.decode().strip().encode()
            print('>>>',line)
            writer.write(line)
            writer.write(b'\r\n')
            await writer.drain()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()

async def main():
    try:
        reader, writer = await asyncio.open_connection(APRS_IS_HOST, APRS_IS_FILTER_PORT)
        tasks = []
        tasks.append(asyncio.create_task(ingress(reader = reader)))
        tasks.append(asyncio.create_task(egress(writer = writer)))
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

