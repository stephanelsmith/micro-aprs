
def generate_aprs_passcode(callsign):
    # Convert to uppercase and remove any SSID
    if isinstance(callsign, (bytes, bytearray)):
        callsign = callsign.decode()
    callsign = callsign.split('-')[0].upper()
    
    hash_val = 0x73e2
    i = 0
    
    while i < len(callsign):
        # Shift and add the first character of the pair
        hash_val ^= ord(callsign[i]) << 8
        # Shift and add the second character if it exists
        if i + 1 < len(callsign):
            hash_val ^= ord(callsign[i+1])
        i += 2
        
    return hash_val & 0x7fff

