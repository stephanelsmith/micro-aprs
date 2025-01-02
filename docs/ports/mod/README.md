
# Getting Started with Python

```aprs_mod.py``` and ```aprs_demod.py``` are the two primary utilities built around stdin and stdout piping to interconnect stages.

:point_up: ```aprs_demod.py``` pre-saves fir filter coefficients.  If you are changing the bpf and lpf parameters in demod (not common), please have scipy installed to memoize the computed filter coefficients.


## :loud_sound: APRS to AFSK audio samples

```aprs_mod.py``` provides conversion from APRS string(s) into raw 16 bit signed integer raw format with a default sampling rate 22050. 

### Arguments

* Command line options showing with help flag ```-h```
```
python aprs_mod.py -h
```
```
APRS MOD
(C) Stephane Smith (KI5TOF) 2024

Usage:
aprs_mod.py [options] (-t outfile) (-t infile)
aprs_mod.py [options] (-t infile)
aprs_mod.py [options]
aprs_mod.py

OPTIONS:
-r, --rate       22050 (default)
-vox, --vox      Vox mode, pad header flags to activate radio vox
-v, --verbose    verbose intermediate output to stderr

-t INPUT TYPE OPTIONS:
intype       aprs strings
infile       '-' (default)

-t OUTPUT TYPE OPTIONS:
outtype       raw 16 bit samples
outfile       '-' (default) | 'null' (no output) | '*.wav' (wave file) | 'play' play audio
```

### Examples

* APRS to AFSK verbose (-v flag)
Just show verbose output, but don't output the samples to stdout (setting stdout to null).
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -v -t null -t -
```

* Generate AFSK wave audio file.  Decode with direwolf, multimon-ng, and aprd_demod.
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py | sox -t raw -b 16 -e signed-integer -c 1 -v 1.0 -r 22050 - -t wav test/test.wav
atest test/test.wav
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | multimon-ng -t raw -A -a AFSK1200 -
sox -t wav test/test.wav -t raw -b 16 -e signed-integer -c 1 -r 22050 - | python aprs_demod.py -t -
```

* ```aprs_mod.py```  inline decode.
```
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py -t - -t aprs - | multimon-ng -t raw -A -a AFSK1200 -
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py | multimon-ng -t raw -A -a AFSK1200 -
echo "KI5TOF>APRS:>hello world!" | python aprs_mod.py | python aprs_demod.py -t -
```


