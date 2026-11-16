#!env/bin/python

import traceback
import sys
from datetime import datetime
from subprocess import check_output

import asyncio
from asyncio import Event
from asyncio import Queue

from ax25.ax25 import AX25
from ax25.callssid import CallSSID

from lib.parse_args import is_parse_args
from lib.gps import aprs_gps_format
from lib.aprs import generate_aprs_passcode

# try importing rich, colorize output text for readability
try:
    from rich.console import Console
    console = Console()
    print = console.print
except ImportError:
    console = None

APRS_IS_HOST = 'rotate.aprs.net'
APRS_IS_FULL_FEED_PORT = 10152
APRS_IS_FILTER_PORT = 14580

#APRS
#aprs how paths work: https://blog.aprs.fi/2020/02/how-aprs-paths-work.html
#connecting: https://www.aprs-is.net/Connecting.aspx
#filters: https://www.aprs-is.net/javAPRSFilter.aspx

#position: KX5X>APRS:=2941.97N/09545.01WChello world
#status:   KX5X>APRS:>hello world!
#message:  KX5X>APRS::KX5X   :hello world
#station:  KX5X-1>APRS:!2941.97NI09545.01W#144.390MHz Rx Only APRS iGate
# W5LCR-10>APRX29,TCPIP*,qAC,T2QUEBEC:!2906.46NI09627.19W#144.390MHz Louise, TX APRS iGate Digi

#https://aprs.fi/doc/guide/aprsfi-telemetry.html
#https://github.com/PhirePhly/aprs_notes/blob/master/telemetry_format.md
#specify parameter names and units
#telem:    KX5X>APRS::KX5X   :PARM.Title_A1,Title_B2,Title_C3,Title_D4,Title_E5,BIT_A1,BIT_B2,BIT_C3,BIT_D4,BIT_E5,BIT_F6,BIT_G7,BIT_H8
#telem:    KX5X>APRS::KX5X   :UNIT.Volt,Volt,Volt,Volt,Volt,B,B,B,B,B,B,B,B
#specify scaling ax^2+bx+c             a,b,c|a,b,c|a,b,c|a,b,c|a,b,c
#telem:    KX5X>APRS::KX5X   :EQNS.0,1,0,0,1,0,0,1,0,0,1,0,0,1,0
# sending data
#telem:    KX5X>APRS:T#000,1,2,3,4,5,01010101
#telem:    KX5X>APRS:T#002,10.12,20.23,30.45,40.67,50.89,10101010
#telem:    KX5X>APRS:T#003,110.12,120.23,130.45,140.67,150.89,10101010comment


async def run(cmd):
    return await asyncio.to_thread(check_output, cmd.split())

# APRS-IS servers send a '# aprsc ...' keepalive about every 20s, so silence this long means a dead link
RX_TIMEOUT_S = 60
TX_TIMEOUT_S = 15
CONNECT_TIMEOUT_S = 20

async def aprs_is_ingress(reader, login_evt, call):
    try:
        login_resp = 'logresp {} verified'.format(call.decode())
        while True:
            try:
                data = await asyncio.wait_for(reader.read(1024), RX_TIMEOUT_S)
            except asyncio.TimeoutError:
                raise ConnectionError('no data from APRS-IS in {}s'.format(RX_TIMEOUT_S))
            if not data:
                raise ConnectionError('APRS-IS closed the connection')
            line = data.decode(errors='replace')
            if line.find(login_resp) != -1:
                login_evt.set()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print('aprs_is ingress:', repr(err))
        raise # let the session notice and reconnect
    finally:
        print('exiting aprs_is ingress')

async def stdin_ingress(call,
                        ax25_q,
                        ):
    try:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        eol = ord('\n')
        done = False
        buf = bytearray(512)
        count = 0

        while not done:
            i = 0
            while True:
                try:
                    b = await reader.readexactly(1)
                except asyncio.IncompleteReadError:
                    done = True
                    break
                if ord(b) == eol:
                    break
                buf[i] = ord(b)
                i += 1
                if i >= 512:
                    break
            line = buf[:i]
            if not line:
                continue

            # print(line)
            try:
                ax25 = AX25(aprs = line)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                traceback.print_exc()
                print('SKIPPING...')
                continue

            count += 1

            nogate = False
            for digi in ax25.digis:
                try:
                    via = digi.to_aprs().lower()
                    if b'tcpip' in via or\
                    b'tcpxx' in via or\
                    b'rfonly' in via or\
                    b'nogate' in via:
                        nogate = True
                except asyncio.CancelledError:
                    raise
                except:
                    pass
            if nogate:
                try:
                    if console:
                        print('[bright_blue bold]\[{}][/] {}'.format('NOGATE', ax25.to_aprs_rich()))
                    else:
                        print('[{}] {}'.format('NOGATE', ax25))
                except Exception as err:
                    print(err)
                    print('[{}] {}'.format('NOGATE', ax25))
            else:
                try:
                    if console:
                        print('[bright_blue bold]\[{}][/] {}'.format(count, ax25.to_aprs_rich()))
                    else:
                        print('[{}] {}'.format(count, ax25))
                except Exception as err:
                    print(err)
                    print('[{}] {}'.format(count, ax25))

            if nogate:
                continue


            #Packets being relayed to APRS-IS network get ",qAR,IGATECALL-SSID" appended to outermost address before first ':' character
            #qAR = Packet is placed on APRS-IS by an IGate from RF.  The callSSID following the qAR it the callSSID of the IGate
            ax25.digis.append(CallSSID(call=b'qAR'))
            ax25.digis.append(CallSSID(aprs=call))

            await ax25_q.put((ax25,True))

    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()
    finally:
        print('exiting stdin ingress')

async def station_beacon(ax25_q, 
                         call = None, 
                         lat = None, lon = None, 
                         msg = '',
                         ):
    if not lat or not lon or not call:
        print('skipping beacon lat:{} lon:{}'.format(lat, lon))
    try:
        aprs_loc = aprs_gps_format(lat, lon, 
                                   symbol1 = 'I',  # use letter 'I'
                                   symbol2 = '#',  # digipeater symbol (green star)
                                   )
        msg = 'https://github.com/stephanelsmith/micro-aprs RX igate'
        ax25 = AX25(src  = call,
                    dst  = b'APRS',
                    info = '!{}{}'.format(aprs_loc, msg).encode(),
                    )
        #qAS = for a beacon generated by the server                    
        ax25.digis.append(CallSSID(call=b'qAS'))
        ax25.digis.append(CallSSID(aprs=call))
        while True:
            await ax25_q.put((ax25, False))
            await asyncio.sleep(60*60)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()
    finally:
        print('exiting station beacon')

async def aprs_is_egress(writer, 
                         call,
                         passcode,
                         login_evt,
                         ax25_q,
                         log_file = None,
                         ):
    try:
        #login
        login_str = 'user {} pass {} vers microax25afsk 0.0 filter p/{}'.format(
                    call.decode(), passcode, call.decode())
        print('>>>',login_str)
        writer.write(login_str.encode())
        writer.write(b'\r\n')
        await asyncio.wait_for(writer.drain(), TX_TIMEOUT_S)
       
        #wait for login response
        await asyncio.wait_for(login_evt.wait(), CONNECT_TIMEOUT_S)

        while True:
            ax25,echo = await ax25_q.get()
            sent = False
            try:
                if echo and log_file:
                    with open(log_file, 'a') as l:
                        l.write('[{}] {}\n'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ax25))
                writer.write(ax25.encode())
                writer.write(b'\r\n')
                await asyncio.wait_for(writer.drain(), TX_TIMEOUT_S)
                sent = True
            finally:
                if not sent:
                    ax25_q.put_nowait((ax25, False)) # connection failed, keep the packet for the next session
                ax25_q.task_done()
    except asyncio.CancelledError:
        raise
    except Exception as err:
        print('aprs_is egress:', repr(err))
        raise # let the session notice and reconnect
    finally:
        print('exiting aprs is egress')

async def aprs_is_session(call, passcode, ax25_q, log_file):
    '''One connection to APRS-IS. Returns/raises when the connection is lost.'''
    reader, writer = await asyncio.wait_for(
                         asyncio.open_connection(APRS_IS_HOST, APRS_IS_FILTER_PORT),
                         CONNECT_TIMEOUT_S)
    login_evt = Event()
    tasks = [asyncio.create_task(aprs_is_ingress(reader    = reader,
                                                 call      = call,
                                                 login_evt = login_evt,
                                                 )),
             asyncio.create_task(aprs_is_egress(writer    = writer,
                                                call      = call,
                                                passcode  = passcode,
                                                login_evt = login_evt,
                                                ax25_q    = ax25_q,
                                                log_file  = log_file,
                                                ))]
    try:
        # whichever side fails first ends the session
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), 5)
        except Exception:
            pass

async def main():
    args = is_parse_args(sys.argv)
    tasks = []
    try:
        call = args['args']['call'].upper().encode()
        passcode  = generate_aprs_passcode(call)
        ax25_q = Queue() # outlives connections, packets wait here during an outage

        # these live for the whole program, independent of the network
        tasks.append(asyncio.create_task(stdin_ingress(call      = call,
                                                       ax25_q    = ax25_q,
                                                       )))
        tasks.append(asyncio.create_task(station_beacon(call      = call,
                                                        ax25_q    = ax25_q,
                                                        lat       = args['args']['lat'],
                                                        lon       = args['args']['lon'],
                                                        msg       = args['args']['msg'],
                                                        )))

        retry_s = 1
        while True:
            t0 = asyncio.get_running_loop().time()
            try:
                await aprs_is_session(call, passcode, ax25_q, args['args']['log_file'])
            except asyncio.CancelledError:
                raise
            except Exception as err:
                print('aprs_is session ended:', repr(err))
            if asyncio.get_running_loop().time() - t0 > 60:
                retry_s = 1 # it was up a while, start backoff over
            print('reconnecting in {}s'.format(retry_s))
            await asyncio.sleep(retry_s)
            retry_s = min(retry_s*2, 60)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        traceback.print_exc()
    finally:
        for t in tasks:
            t.cancel()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

