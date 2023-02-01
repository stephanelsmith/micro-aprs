
import sys
import asyncio
import traceback
from pydash import py_ as _

from afsk.mod import AFSKModulator
from ax25 import AX25

from lib.utils import parse_args
from lib.utils import pretty_binary

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
    try:
        async with AFSKModulator(sampling_rate = 22050,
                                 verbose       = args['verbose']) as afsk_demod:
            ax25 = AX25(src   = 'KI5TOF',
                        dst   = 'APRS',
                        digis = [],
                        info  = 'hello world!',
                        )
            print(ax25)
            print(ax25.to_aprs())
            print('--ax25--')
            pretty_binary(ax25.to_ax25())
            print('--afsk--')
            pretty_binary(ax25.to_afsk())
    except Exception as err:
        traceback.print_exc()
    except asyncio.CancelledError:
        return
    finally:
        pass


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
