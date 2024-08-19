
# ESP32 BUILD
make BOARD=SS_APRS USER_C_MODULES=/home/ssmith/micro-aprs/c_modules/esp32s3.cmake
#py -m esptool --chip esp32s3 --port COM13 write_flash -z 0 .\micropython_latest\ports\esp32\build-SS_APRS\firmware.bin

