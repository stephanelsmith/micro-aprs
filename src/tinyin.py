
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
from upy.afsk import out_afsk
from afsk.func import create_power_meter

from cdsp import i16tobs
from cdsp import utoi32
from cdsp import utoi16
from cdsp import isqrt

import lib.upydash as _

# afsk sample frequency
_FOUT = 11_025
# _FOUT = const(22_050)
# _FOUT = const(44_100)

_AFSK_IN_PIN = const(2)
_DEBUG_OUT_PIN = const(6)

cReadi16 = {
    'u16'    : 0  | uctypes.UINT16,
}

async def in_afsk(adc, rio, demod, do):
    pwrmtr = create_power_meter(siz = 40)

    read = adc.read_u16
    write = rio.write

    # pre-allocate read/write buffer
    buf = bytearray(uctypes.sizeof(cReadi16))
    stu = uctypes.struct(uctypes.addressof(buf),  cReadi16, uctypes.LITTLE_ENDIAN)

    tsf = ThreadSafeFlag()
    tog = do.toggle

    isin:int = 0

    tim = Timer(1)
    
    try:
        @micropython.viper
        def cb(tim):
            nonlocal isin
            _o:int = int(read()) # read from adc
            stu.u16 = _o
            write(buf)
            tog() # debug
            _o -= 32768 # u16 adc value convert to s16
            _p:int = int(pwrmtr(_o))
            # print(_o,_p)
            _isin:int = int(isin)
            if _p >= 300 and _isin == 0:
                isin = 3 # HACK OBJECT VALUE = 1 ... (1<<1)|1
            if _p < 300 and _isin == 1:
                tsf.set()
                tim.deinit()
        tim.init(mode=Timer.PERIODIC, freq=_FOUT, callback=cb)
        await tsf.wait()

    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()

from cdsp import tim_cb

class TimerCallback:
    def __init__(self, adc, do, tsf, rio, tim):
        self.test = 42
        self.tog = do.toggle
        self.tsfset = tsf.set
        self.read = adc.read_u16
        self.write = rio.write
        # self.pwrmtr = pwrmtr
        self.deinit = tim.deinit
        self.buf = bytearray(2)
        self.state = 0
        # self.rst = 1
        self.siz = 10
        self.arr = array('i', [0 for x in range(self.siz)])
        self.idx = 0
        self.cnt = 0

    def __call__(self, timer):
        # if not tim_cb(self):
            # timer.deinit()
        tim_cb(self)

async def in_afsk2(adc, rio, demod, do):
    # pwrmtr = create_power_meter(siz = 40)
    tim = Timer(1)
    tsf = ThreadSafeFlag()
    cb = TimerCallback(adc    = adc,
                       do     = do,
                       tsf    = tsf,
                       rio    = rio,
                       # pwrmtr = pwrmtr,
                       tim    = tim)
    
    try:
        tim.init(mode=Timer.PERIODIC, freq=_FOUT, callback=cb)
        await tsf.wait()
    except Exception as err:
        sys.print_exception(err)
    finally:
        tim.deinit()


async def start():

    tasks = []
    try:
        ax25_q = Queue()
        rio = RingIO(100000)

        adc = ADC(Pin(_AFSK_IN_PIN, Pin.IN), atten=ADC.ATTN_11DB)
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
                    # print(0)
                    await in_afsk2(adc, rio, demod, do)
                    print('READ: {}'.format(rio.any()))

                    if rio.any() == 0:
                        break
                    # print(1)

                    # process results
                    await demod.stream_core(in_rx = rio)
                    # print(2)

                    # process ax25
                    while not ax25_q.empty():
                        # print(3)
                        ax25 = await ax25_q.get()
                        print(ax25)
                    # print(4)

                    # clean up
                    gc.collect()
                    # return

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
