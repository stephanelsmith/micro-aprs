# APRS-IS helpers

def generate_aprs_passcode(call):
    '''APRS-IS passcode for a callsign (bytes or str), the SSID is ignored.
    Standard public algorithm: https://www.aprs-is.net/Connecting.aspx'''
    if isinstance(call, str):
        call = call.encode()
    call = call.split(b'-')[0].upper()
    h = 0x73e2
    for i in range(0, len(call), 2):
        h ^= call[i] << 8
        if i+1 < len(call):
            h ^= call[i+1]
    return h & 0x7fff
