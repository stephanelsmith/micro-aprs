
import asyncio
import sys
import gc
from micropython import const

from machine import Pin
from machine import UART

from lilygottwr.sa868.sa868 import SA868
from lilygottwr.sa868.pwr import SA868Pwr
import lilygottwr.sa868.defs as sa868_defs

# lilygo-twr specific pin
_MIC_CH_SEL  = const(17)     # mic channel select, 0->mic, 1->esp

async def gc_coro():
    try:
        while True:
            gc.collect()
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

async def sa868_tx_coro(sa868_uart):

    ptt = Pin(sa868_defs.PTT, Pin.OUT, value=1)
    pd = Pin(sa868_defs.PD, Pin.OUT, value=1)
    hl = Pin(sa868_defs.HL_POWER, Pin.OUT, value=1)

    read_stdin = asyncio.StreamReader(sys.stdin.buffer)
    sys.stdout.buffer.write(b'> ')
    c = bytearray()
    while True:
        b = await read_stdin.read(1)
        sys.stdout.buffer.write(b)
        c += b
        if b == b'\n':
            if c[:3] == b'ptt':
                ptt.value(not ptt.value())
                print('ptt:{} is_tx:{}'.format(ptt.value(), ptt.value() == 0))
            elif c[:2] == b'pd':
                pd.value(not pd.value())
                print('pd:{}'.format(pd.value()))
            elif c[:2] == b'hl':
                hl.value(not hl.value())
                print('hl:{}'.format(hl.value()))
            else:
                sa868_uart.write(c)
            sys.stdout.buffer.write(b'> ')
            c = bytearray()

async def sa868_rx_coro(sa868_uart):
    read_sa868 = asyncio.StreamReader(sa868_uart)
    while True:
        r = await read_sa868.readline()
        sys.stdout.buffer.write(b'< ')
        sys.stdout.buffer.write(r)

async def start():
    try:
        gc_task = asyncio.create_task(gc_coro())

        # radio to connect to mic esp
        mic_ch_sel = Pin(_MIC_CH_SEL, Pin.OUT, value=0)

        # high-z audio in pin
        audio_in = Pin(sa868_defs.AUDIO_SPEAKER, Pin.IN, pull=None)

        print('sa868 powering on')
        async with SA868Pwr():
            tasks = []
            print('uart')
            sa868_uart = UART(1, 9600, 
                              tx = sa868_defs.RX, 
                              rx = sa868_defs.TX)
            tasks.append(asyncio.create_task(sa868_tx_coro(sa868_uart)))
            tasks.append(asyncio.create_task(sa868_rx_coro(sa868_uart)))
            print('gather')
            await asyncio.gather(*tasks)

    finally:
        gc_task.cancel()

def main():
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        sys.print_exception(err)
    finally:
        asyncio.new_event_loop()  # Clear retained state

