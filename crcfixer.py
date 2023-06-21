#!python

import asyncio
import lib.upydash as _
from copy import deepcopy

from ax25.ax25 import AX25
from ax25.defs import CRCError
from ax25.defs import DecodeError
from ax25.defs import CallSSIDError

ORD_0 = 48
ORD_9 = 57
ORD_A = 65
ORD_Z = 90
ORD_COLON = 58

#check callssid uses characters A-Z, 0-9, or '-'
def callssid_valid(callssid):
    if len(callssid) == 0:
        return False
    for x in callssid:
        o = ord(x)
        if o >= ORD_0 and o <= ORD_9 or\
           o >= ORD_A and o <= ORD_Z or\
           o == ORD_COLON:
            pass
        else:
            return False
    return True

def flip(frame, flip_a, flip_b):
    idx = flip_a//8
    bit = flip_a%8
    frame[idx] = frame[idx] ^ (0x80>>bit)
    if flip_a != flip_b:
        idx = flip_b//8
        bit = flip_b%8
        frame[idx] = frame[idx] ^ (0x80>>bit)


def ax25_fixer(frame):
    _frame = bytearray(frame)

    #adjacent bits are common, try all those first
    flip_a_max = min((len(frame)-3)*8,254*8)
    for flip_a in range(8,flip_a_max):
        for flip_b in range(flip_a,flip_a+2):
            try:
                flip(_frame, flip_a, flip_b)
                try:
                    ax25 = AX25(frame = _frame)
                except DecodeError as err:
                    continue
                except CallSSIDError as err:
                    continue
                except CRCError as err:
                    continue
                if not callssid_valid(str(ax25.src)) or\
                    not callssid_valid(str(ax25.dst)):
                    continue
                # print('FOUND SOLUTION {} {} {}'.format(
                    # flip_a, flip_b, ax25))
                return (ax25, (flip_a,flip_b))
            finally:
                flip(_frame, flip_a, flip_b)

    #scan all
    flip_a_max = min((len(frame)-3)*8,240*8)
    for flip_a in range(8,flip_a_max):
        flip_b_max = min((len(frame)-3)*8,(flip_a+240)*8)
        for flip_b in range(flip_a,flip_b_max):
            try:
                flip(_frame, flip_a, flip_b)
                try:
                    ax25 = AX25(frame = _frame)
                except DecodeError as err:
                    continue
                except CallSSIDError as err:
                    continue
                except CRCError as err:
                    continue
                if not callssid_valid(str(ax25.src)) or\
                    not callssid_valid(str(ax25.dst)):
                    continue
                # print('FOUND SOLUTION {} {} {}'.format(
                    # flip_a, flip_b, ax25))
                return (ax25, (flip_a,flip_b))
            finally:
                flip(_frame, flip_a, flip_b)
    return (None,None)


async def main():

    #candidates
    frames = []

    #filter frames where we have valid src and dst
    with open('r_crc_err.txt', 'r') as f:
        for line in f.readlines():
            frame = eval(line)
            # try:
                # ax25 = AX25(frame = frame)
            # except CRCError as err:
                # ax25 = err.ax25
            # except DecodeError as err:
                # continue
            # if callssid_valid(str(ax25.src)) and\
               # callssid_valid(str(ax25.dst)):
                # frames.append(frame)
            frames.append(frame)

    with open('r_ax25_fixed.txt', 'w') as f:
        fixed_ax25s = []
        solutions = 0
        for count,frame in enumerate(frames):
            try:
                ax25 = AX25(frame = frame)
            except CRCError as err:
                ax25 = err.ax25
            print('{}'.format(count))
            print('SRC: {}'.format(ax25.src))
            print('DST: {}'.format(ax25.dst))
            print('INF: {}'.format(ax25.info))

            #look for solution
            ax25,flips = ax25_fixer(frame = frame)
            if ax25:
                solutions += 1
                print('FIXED: {} {}'.format(flips, ax25))
                fixed_ax25s.append((flips, ax25))
                f.write('{} {}\n'.format(flips, ax25))
            print('SOLUTIONS: {}'.format(solutions))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

