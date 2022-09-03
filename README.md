# Micro AX25 AFSK

A python based library for encoding and decoding APRS/AX.25 packets in AFSK.  

This library is optimized for small computers (eg. OpenWRT and Linux machines running Python 3.x) and embedded systems, especially [micropython supported targets and platforms ](https://github.com/micropython/micropython#supported-platforms--architectures).

This library follows micropython's best practices for [optimizing speed](https://docs.micropython.org/en/latest/reference/speed_python.html#maximising-micropython-speed).  Especially:
* Avoid floating point arithmetic in critical sections.
* Avoid the use math libraries and dependencies in critical sections.  
	* Lookup tables `:+1:`
	* FFT, math.sin `:-1:`
* Avoid memory allocation in critical sections.  Buffers are preallocated and should not grow in critical sections.
* Buffer slices passed as memoryview objects to avoid excessive heap allocations
* Opportunistic implementation of critical functions with [viper emitter](https://docs.micropython.org/en/latest/reference/speed_python.html#the-viper-code-emitter)


The AFSK encoded/decoded APRS/AX.25 waveforms are tested against: 
* [DireWolf](https://github.com/wb2osz/direwolf)
* [Multimon-NG](https://github.com/EliasOenal/multimon-ng)

### Examples

Dire Worlf Test

    Test 1

Multimon-ng

    Test 2

## License


## Acknowledgments


