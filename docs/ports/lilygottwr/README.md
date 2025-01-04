# LilyGo T-TWR

The LilyGo T-TWR is a commerically available dev kit including ESP32S3 + [NiceRF SA868 Wireless Transceiver](https://www.nicerf.com/walkie-talkie-module/2w-embedded-walkie-talkie-module-sa868.html).  The T-TWR comes in a few flavors, the one I've chosen is the VHF (covering APRS 144.39MHz) normal edition. 
<p align="center">
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/ports/lilygottwr/T-TWR_Plus_600x600.webp?raw=true" alt="" width="600"/>
</p>

## References
- LilyGo T-TWR
  - [Pin map](https://github.com/Xinyuan-LilyGO/T-TWR/blob/master/lib/LilyGo_TWR_Library/src/utilities.h)
  - [Schematic](https://github.com/Xinyuan-LilyGO/T-TWR/blob/master/schematic/T-TWR-Plus_Rev2.0.pdf)
- SA868 wireless transceiver
  - [Datasheet](SA868.pdf)
  - [sa868.cpp](https://github.com/Xinyuan-LilyGO/T-TWR/blob/master/lib/LilyGo_TWR_Library/src/sa868.cpp) Reference firmware
- X Powers AXP2101 PMU
  - [Datasheet](https://www.lcsc.com/datasheet/lcsc_datasheet_2305060916_X-Powers-Tech-AXP2101_C3036461.pdf')
  - [Xpower/Lilygo Library for Micropython](https://github.com/lewisxhe/XPowersLib) 


## :hammer: Building Micropython Firware
For a step-by-step getting started, [please see the TinyS3 port](https://github.com/stephanelsmith/micro-aprs/tree/master/docs/ports/tinys3#hammer-building-micropython-firware-for-tinys3).
```
make BOARD=SS_TTWR USER_C_MODULES=~/micro-aprs/c_modules/esp32s3.cmake
```
```
py -m esptool --chip esp32s3 --port COM9 write_flash -z 0 .\build-SS_TTWR\firmware.bin
```
```
py -m serial.tools.miniterm COM8
```


## :raised_hands: Acknowledgements
- Images and information from [LilyGo T-TWR Store](https://www.lilygo.cc/products/t-twr-plus?srsltid=AfmBOooEmV2bkOz1-0ceEJCwkFkITOXYzLGBPkWvyBfF2cm7XqGT4BYH).
- [LilyGo T-TWR Github Page](https://github.com/Xinyuan-LilyGO/T-TWR)
- [NiceRF SA868 Spec Sheet](SA868.pdf)

