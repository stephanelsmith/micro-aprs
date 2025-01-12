
@micropython.viper
def crc16_ccit(data:object)->int:
    crc:int = 0xffff
    table = ptr16(CRC16_AX25)
    bs = ptr8(data)
    for i in range(int(len(data))):
        b:int = bs[i]
        crc = ((crc) >> 8) ^ table[((crc) ^ b) & 0xff];
    return (crc ^ 0xffff) & 0xffff
