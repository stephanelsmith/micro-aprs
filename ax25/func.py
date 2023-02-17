
def assign_bit(byte, idx, value):
    mask = (0x80>>(idx%8))
    if value:
        return byte | mask
    else:
        return byte & (mask ^ 0xff)
def get_bit(byte, idx):
    mask = (0x80)>>(idx%8)
    return (byte & mask) >> ((8-idx-1)%8)

def reverse_byte(_byte):
    #xor reverse bit technique
    _byte = ((_byte & 0x55) << 1) | ((_byte & 0xAA) >> 1);
    _byte = ((_byte & 0x33) << 2) | ((_byte & 0xCC) >> 2);
    _byte = ((_byte & 0x0F) << 4) | ((_byte & 0xF0) >> 4);
    return _byte

def reverse_bit_order(mv):
    for idx in range(len(mv)):
        mv[idx] = reverse_byte(mv[idx])

def do_bitstuffing(mv, start_bit, stop_bit):
    #bit stuff frame in place
    idx = start_bit
    c = 0   #running count of consecutive 1s
    cnt = 0 #count of number of bits that were stuffed
    while idx < stop_bit:
        if get_bit(mv[idx//8], idx):
            c += 1
        else:
            c = 0
        idx += 1
        if c == 5:
            #stuff a bit
            #shift all bytes to the right, starting next byte
            insert_bit_in_array(mv, bit_idx = idx)
            c = 0
            cnt += 1 
            idx += 1
    return cnt

def insert_bit_in_array(mv, bit_idx):
    #shift bytes right
    shift_bytes_right(mv, start_byte = bit_idx//8+1)
    #byte in question, stuff the bit
    split_shift_byte(mv, bit_idx)

def shift_bytes_right(mv, start_byte, stop_byte=None):
    #shift bytes right by one bit
    if not stop_byte:
        stop_byte = len(mv)
    #idx iterating byte index
    for idx in range(stop_byte-1, start_byte-1, -1):
        #work from right to left
        p       = 0 if idx == 0 else (mv[idx-1]&0x01)
        q       = 0x80 if p else 0
        mv[idx] = (mv[idx]>>1) | q

def split_shift_byte(mv, idx):
    #insert a 0 at bit index position
    if idx%8 == 0:
        #if we are shifting the first bit, just shift
        mv[idx//8] = mv[idx//8] >> 1
    else:
        #we need to split at specific bit index position
        #right side
        t_shift = mv[idx//8] & (0xff>>(idx%8))
        t_shift = t_shift >> 1
        #left side
        mv[idx//8] = mv[idx//8] & (0xff<<((8-idx)%8))
        #combine, 0 (stuffed bit), left in center
        mv[idx//8] = mv[idx//8] | t_shift


def unstuff(mv, stop_bit):
    #look for 111110, remove the 0
    c = 0
    idx = 0
    while idx < stop_bit:
        mask = (0x80>>(idx%8))
        b = (mv[idx//8] & mask) >> ((8-idx-1)%8) #pick bit
        if b == 0 and c == 5:
            #detected stuffed bit, remove it
            shift_in = shift_bytes_left(mv, idx//8+1)
            remove_bit_shift_from_right(mv, idx, shift_in)
            c = 0
            continue
        c = c+b if b==1 else 0
        idx += 1

def remove_bit_shift_from_right(mv, idx, shift_in=0):
    if idx%8 == 7:
        #the bit is far right, just apply shift_in
        pass
    else:
        #we need to split at specific bit index position
        #get the portion that's getting shifted
        rmask = 0xff >> (idx%8)
        lmask = rmask ^ 0xff
        mv[idx//8] = (lmask & mv[idx//8]) | (((mv[idx//8]&rmask)<<1)&0xff)
    if shift_in:
        mv[idx//8] |= 0x01
    else:
        mv[idx//8] &= (0x01 ^ 0xff)

def shift_bytes_left(mv, start_byte):
    l = 0x00
    #idx iterating byte index
    for idx in range(len(mv)-1,start_byte-1, -1):
        #work from right to left
        t = 0x80 & mv[idx] #save bit shifted out
        mv[idx] = (mv[idx]<<1)&0xff
        mv[idx] = mv[idx] | 0x01 if l else mv[idx] #shift l
        l = t # store shifted bit for next iteration
    return l



def convert_nrzi(mv, stop_bit):
    #https://en.wikipedia.org/wiki/Non-return-to-zero
    #The HDLC a logical 0 is transmitted as a transition, and a logical 1 is transmitted as no transition.
    c = 0
    for idx in range(stop_bit):
        mask = (0x80)>>(idx%8)
        b = get_bit(mv[idx//8], idx)
        if b == 0:
            #toggle
            c ^= 0x01
        mv[idx//8] = assign_bit(mv[idx//8], idx, c)


