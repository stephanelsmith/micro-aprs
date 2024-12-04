
import sys
import asyncio
import gc
from array import array

from machine import Pin, PWM
from machine import Timer
from machine import UART
from machine import I2C

from asyncio import Event
from asyncio import ThreadSafeFlag
from micropython import const

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25

from lilygottwr.sa868.sa868 import SA868
from lilygottwr.sa868.pwr import SA868Pwr
import lilygottwr.sa868.defs as sa868_defs
from lilygottwr.xpower import start as xpower_start

import lib.upydash as _

_FPWM = const(500_000)
# _FOUT = const(22_050)
_FOUT = const(44_100)

AFSK_OUT_PIN = sa868_defs.AUDIO_MIC

# lilygo-twr specific pin
_MIC_CH_SEL  = const(17)     # mic channel select, 0->mic, 1->esp
_I2C_SCA = 8
_I2C_SCL = 9

async def gc_coro():
    try:
        while True:
            gc.collect()
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
    except Exception as err:
        sys.print_exception(err)

async def sa868_rx_coro(sa868_uart, rx_q):
    read_sa868 = asyncio.StreamReader(sa868_uart)
    while True:
        r = await read_sa868.readline() 
        # await rx_q.put(r)  # eg. b'\x80+DMOERROR\r\n'
        await rx_q.put(r.strip())  # eg. b'\x80+DMOERROR'
        sys.stdout.buffer.write(b'< ')
        sys.stdout.buffer.write(r)

async def sa868_tx_rx(sa868_uart, rx_q, msg):
    # expect msg to be bytes or bytearray
    if isinstance(msg, str):
        msg = msg.encode()
    while True:
        print('> {}'.format(msg))
        sa868_uart.write(msg)
        sa868_uart.write(b'\r\n')
        try:
            r = await asyncio.wait_for_ms(rx_q.get(), 1000)
            if b'ERROR' in r:
                continue
            return r.strip()
        except asyncio.TimeoutError:
            await asyncio.sleep_ms(1000)
            continue

async def out_afsk(arr, siz):

    try:
        tsf = ThreadSafeFlag()
        pwm = PWM(Pin(AFSK_OUT_PIN), freq=_FPWM, duty_u16=0) # resolution = 26.2536 - 1.4427 log(fpwm)
        tim = Timer(1)

        nl = array('H', [0,]) # viper nonlocals

        @micropython.viper
        def cb(tim):
            nonlocal nl,pwm,arr,siz,tsf
            _nl  = ptr16(nl)  # uint
            _arr = ptr16(arr) # uint
            i:int = _nl[0]
            if i < int(siz):
                pwm.duty_u16(_arr[i])
                i += 1
            if i == int(siz):
                tsf.set()
                i += 1 # > int size we are done
            _nl[0] = i

        tim.init(freq=_FOUT, mode=Timer.PERIODIC, callback=cb)
        await tsf.wait()
    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()
        pwm.deinit()

async def start():

    try:
        gc_task = asyncio.create_task(gc_coro())
        rx_q = Queue()

        async with AFSKModulator(sampling_rate = _FOUT,
                                 signed        = False,
                                 amplitude     = 0x6000,
                                 verbose       = False) as afsk_mod:
            aprs = b'KI5TOF>APRS:>hello world!'
            ax25 = AX25(aprs    = aprs,
                        verbose = False,)
            #AFSK
            afsk,stop_bit = ax25.to_afsk()

            await afsk_mod.pad_zeros(ms = 1000)
            await afsk_mod.send_flags(50)
            await afsk_mod.to_samples(afsk     = afsk, 
                                      stop_bit = stop_bit,
                                      )
            await afsk_mod.send_flags(10)
            await afsk_mod.pad_zeros(ms = 1000)
            arr,siz = await afsk_mod.flush()


        # radio to connect to mic esp, 0->mic, 1->esp
        mic_ch_sel = Pin(_MIC_CH_SEL, Pin.OUT, value=1)

        # high-z audio in pin
        audio_in = Pin(sa868_defs.AUDIO_SPEAKER, Pin.IN, pull=None)

        # ptt, active low, rx=1, tx=0
        ptt = Pin(sa868_defs.PTT, Pin.OUT, value=1)

        # pd, pd=0 is power down, pd=1 is up (this should really be called enable)
        pd  = Pin(sa868_defs.PD, Pin.OUT, value=1) 

        # 0->low power, 1->high power
        hl = Pin(sa868_defs.HL_POWER, Pin.OUT, value=0)

        # start the xpower pmu module
        i2c = I2C(0, scl = Pin(_I2C_SCL), sda  = Pin(_I2C_SCA), freq=400000)
        i2c_scan = i2c.scan()
        print('i2c scan: {}'.format(i2c_scan))
        pmu = await xpower_start(i2c = i2c)

        print('sa868 powering on')
        async with SA868Pwr():
            tasks = []
            print('uart')
            sa868_uart = UART(1, 9600, 
                              tx = sa868_defs.RX, 
                              rx = sa868_defs.TX)

            tasks.append(asyncio.create_task(sa868_rx_coro(sa868_uart, rx_q)))

            await asyncio.sleep_ms(100)

            # connect to SA868
            await sa868_tx_rx(sa868_uart, rx_q, msg=b'AT+DMOCONNECT')

            # set tx/rx frequencies 144.4MHz
            # ：AT+DMOSETGROUP=TXPower，TFV，RFV，Tx_CXCSS，SQ，Rx_CXCSS
            await sa868_tx_rx(sa868_uart, rx_q, msg=b'AT+DMOSETGROUP=1,144.4000,144.4000,0000,1,0000')

            x = 0
            while True:
                x += 1
                try:
                    print(':{}'.format(x))
                    ptt.value(0)
                    print(1)
                    await asyncio.sleep_ms(1000)
                    print(2)
                    await out_afsk(arr, siz)
                finally:
                    print(3)
                    await asyncio.sleep_ms(1000)
                    print(4)
                    ptt.value(1)
                    print(5)
                    await asyncio.sleep_ms(1000)

    except Exception as err:
        sys.print_exception(err)
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
main()
