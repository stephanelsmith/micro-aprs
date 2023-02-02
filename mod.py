
import sys
import asyncio
import traceback
import struct
from pydash import py_ as _
from asyncio import Queue

from afsk.mod import AFSKModulator
from ax25 import AX25

from lib.utils import parse_args
from lib.utils import pretty_binary


async def afsk_out(afsk_q):
    try:
        while True:
            samp = await afsk_q.get()
            x = struct.pack('<h', samp)
            sys.stdout.buffer.write(x)
            afsk_q.task_done()
    except Exception as err:
        traceback.print_exc()

async def main():
    args = parse_args({
        'rate' : {
            'short'   : 'r',
            'type'    : int,
            'default' : 22050,
        },
        'verbose' : {
            'short'   : 'v',
            'type'    : bool,
            'default' : False,
        },
    })
    tasks = []
    afsk_q = Queue()

    tasks.append(asyncio.create_task(afsk_out(afsk_q)))

    try:
        async with AFSKModulator(sampling_rate = 22050,
                                 verbose       = args['verbose']) as afsk_demod:
            ax25 = AX25(src   = 'KI5TOF',
                        dst   = 'APRS',
                        digis = [],
                        info  = 'hello world!',
                        )
            if args['verbose']:
                print(ax25)
                print(ax25.to_aprs())
                print('--ax25--')
                pretty_binary(ax25.to_ax25())
                print('--afsk--')
                ax25,stop_bit = ax25.to_afsk()
                pretty_binary(ax25)
            else:
                ax25,stop_bit = ax25.to_afsk()
                await afsk_demod.to_samples(ax25     = ax25, 
                                            stop_bit = stop_bit,
                                            afsk_q   = afsk_q)
                await afsk_q.join()
    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        return
    finally:
        _.for_each(tasks, lambda t: t.cancel())
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

# afsk = AFSK(sampling_rate = args['rate'])


# ax25 = AX25()
# ax25.encode_ui_frame(src        = 'KI5TOF',
                     # dst        = 'APRS',
                     # digis      = [],
                     # info       = '>hello world', 
                     # flags_pre  = args['flags_pre'],
                     # flags_post = args['flags_post'],
                     # debug      = args['debug'])
# if args['debug']:
    # #we are debugging, exit early
    # exit()

# afsk.dump_ax25_raw_samples(ax25     = ax25,
                           # zpad_ms  = args['zpad_ms'],
                           # out_type = args['out_type'],
                           # )
