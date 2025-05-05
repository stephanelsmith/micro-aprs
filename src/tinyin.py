
import sys
import asyncio
import gc
import time

from array import array
from asyncio import Event
from micropython import RingIO
from machine import ADC
from machine import Pin
from machine import Timer
from asyncio import ThreadSafeFlag
import uctypes

from lib.compat import Queue

from afsk.mod import AFSKModulator
from ax25.ax25 import AX25
from afsk.demod import AFSKDemodulator
from ax25.from_afsk import AX25FromAFSK
from afsk.func import afsk_detector
from upy.afsk import out_afsk
from afsk.func import create_power_meter

from cdsp import i16tobs
from cdsp import utoi32
from cdsp import isqrt

import lib.upydash as _

# afsk sample frequency
_FOUT = 11_025
# _FOUT = const(22_050)
# _FOUT = const(44_100)

_AFSK_IN_PIN = const(2)
_DEBUG_OUT_PIN = const(6)

cReadi16 = {
    'i16'    : 0  | uctypes.INT16,
}

async def in_afsk(adc, rio, demod, do):
    # bpf = demod.bpf
    pwrmtr = demod.pwrmtr
    # pwrmtr = create_power_meter(siz = 10)

    read = adc.read_u16
    write = rio.write
    stdout = sys.stdout.write


    # pre-allocate read/write buffer
    buf = bytearray(uctypes.sizeof(cReadi16))
    stu = uctypes.struct(uctypes.addressof(buf),  cReadi16, uctypes.LITTLE_ENDIAN)

    tsf = ThreadSafeFlag()
    tim = Timer(1)

    # closure params saved as array
    _c = array('i',[0,10,])
    _arr = array('i', (0 for x in range(10)))

    try:
        @micropython.viper
        def cb(tim):
            o:int = int(read()) # read from adc
            stu.i16 = o
            write(buf)

            do.toggle() # debug

            p = pwrmtr(o)

            # # unpack closure params
            # arr = ptr32(_arr)     # indexing ALWAYS return uint
            # c = ptr32(_c)
            # i:int = c[0]
            # siz:int = c[1]

            # arr[i] = o

            # p:int = 0
            # for k in range(siz):
                # b:int = int(utoi32(arr[k])) # cast to int32
                # p += b*b
            # p = int(isqrt(p//siz))

            # c[0] = (i+1)%siz

        tim.init(mode=Timer.PERIODIC, freq=_FOUT, callback=cb)
        await tsf.wait()

    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()


        # while True:
            # o:int = int(read())
            # # o:int = int(bpf(o))
            # # p:int = int(pwrmtr(o))
            # # stdout(str(o))
            # # stdout(' ')
            # # stdout(str(p))
            # # stdout(' | ')
            # # cnt += 1
            # # if cnt >= 11_025:
                # # diff = time.ticks_diff(time.ticks_us(),t_us)
                # # print(diff, 11_025.0/diff)
                # # cnt = 0
                # # t_us = time.ticks_us()
            # tog()

            # # if p > sql  and not isin:
                # # isin = 1
            # # elif p < sql and isin:
                # # # return 
                # # pass
            # # write(i16tobs(o))


async def start():

    tasks = []
    try:
        ax25_q = Queue()
        rio = RingIO(500000)

        adc = ADC(Pin(_AFSK_IN_PIN, Pin.IN))
        do = Pin(_DEBUG_OUT_PIN, Pin.OUT)

        bits_q = Queue()
        async with AFSKDemodulator(sampling_rate = _FOUT,
                                   in_rx         = None,   # don't launch core task
                                   stream_type   = 'u16',
                                   bits_out_q    = bits_q,
                                   is_embedded   = True,
                                   options       = {},
                                   verbose       = False,
                                   ) as demod:
            async with AX25FromAFSK(bits_in_q      = bits_q,
                                    ax25_q         = ax25_q,
                                    verbose        = False):
                while True:
                    # synchronous read from ADC
                    await in_afsk(adc, rio, demod, do)
                    print('READ: {}'.format(rio.any()))

                    if rio.any() == 0:
                        break

                    # process results
                    await demod.stream_core(in_rx = rio)

                    # process ax25
                    while not ax25_q.empty():
                        ax25 = await ax25_q.get()
                        print(ax25)

                    # clean up
                    gc.collect()

        await asyncio.gather(*tasks, return_exceptions=True)

    except asyncio.CancelledError:
        raise
    except KeyboardInterrupt:
        return
    except Exception as err:
        sys.print_exception(err)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*[t for t in tasks if not t.done()], return_exceptions=True)


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
