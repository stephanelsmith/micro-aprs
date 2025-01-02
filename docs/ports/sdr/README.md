

## :radio: Live APRS Decode with RTL-SDR

* Live decode of APRS on 144.39MHz using rtl_fm:
```
rtl_fm -f 144.390M -s 22050 -g 1 - | python aprs_demod.py -t -
```

