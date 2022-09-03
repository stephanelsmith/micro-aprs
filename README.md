

# Micro AX25 AFSK

A python based library for encoding and decoding APRS/AX.25 packets in AFSK.  

The purpose of this library is to thread-the-needle of both enabling APRS/AX.25/AFSK from PC to microcontroller while maintaining portability and readability of python.  This library is optimized for embedded systems, especially [micropython supported targets and platforms ](https://github.com/micropython/micropython#supported-platforms--architectures) and small computers (eg. OpenWRT), not to mention and machine running python!

In practice this means we:
* Avoid floating point and math libraries and dependencies in critical sections.  
	* :+1: Integer math
	* :+1: Lookup tables 
	* :-1: Floating point math
	* :-1: Basic math (sin/cos/etc...) or advanced math (FFT) libraries 
* Avoid memory allocation in critical sections.
	* :+1: Pre-computing buffer/array sizes and modifying in place
	* :+1: Using memoryview objects to pass slices to functions and modifying those slices in place
	* :-1: Dynamically appending items to a list
	* :-1: Functional programming style -> creating/returning new arrays instead of mutating in place
* Single threaded, multitask friendly
	* :+1::+1: Asyncio
* Other optimizations that may look unusual to the untrained eye
	* :+1: Local caching object references
	* :+1: Short variable names
	* :+1: Viper emitter (with vanilla python backup)


## Testing

The gold standards tested against are: 
* [DireWolf](https://github.com/wb2osz/direwolf)
* [Multimon-NG](https://github.com/EliasOenal/multimon-ng)

Dire Worlf Test

    Test 1

Multimon-ng

    Test 2

## License


## Acknowledgments

  - Dire wolf
