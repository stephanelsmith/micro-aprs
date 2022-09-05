

def insert_bit_in_array(mv, bit_idx):
    shift_bytes_right(mv, start_byte = bit_idx//8+1)
    split_shift_byte(mv, bit_idx)

def shift_bytes_right(mv, start_byte, stop_byte=None):
    if not stop_byte:
        stop_byte = len(mv)
    for idx in range(stop_byte-1, start_byte-1, -1):
        # print_byte(mv[idx])
        p       = 0 if idx == 0 else (mv[idx-1]&0x01)
        q       = 0x80 if p else 0
        mv[idx] = (mv[idx]>>1) | q
        # print_byte(mv[idx])

def split_shift_byte(mv, idx):
    if idx%8 == 0:
        mv[idx//8] = mv[idx//8] >> 1
    else:
        #right side
        t_shift = mv[idx//8] & (0xff>>(idx%8))
        t_shift = t_shift >> 1
        #left side
        mv[idx//8] = mv[idx//8] & (0xff<<((8-idx)%8))
        #combine, 0 (stuffed bit), left in center
        mv[idx//8] = mv[idx//8] | t_shift

def print_byte(b):
    print_binary([b])

def print_binary(mv):
    for idx in range(len(mv)*8):
        if idx%8==0:
            print('{} {} {} 0x{} '.format(str(idx//8).zfill(4), str(idx).zfill(4), chr(mv[idx//8]), hex(mv[idx//8])[2:].zfill(2)), end='')
        if idx%8==4:
            print(' ', end='')
        print(1 if mv[idx//8] & (0x80>>(idx%8)) else 0, end='')
        if idx%8==7:
            print('')

ba = bytearray(b'cafe')
print()
print_binary(ba)
print()
# shift_bytes_right(ba, start_byte=1)
# split_shift_byte(ba, idx=17)
insert_bit_in_array(ba, 8)
print_binary(ba)

