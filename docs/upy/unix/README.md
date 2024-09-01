# Building Micropython Firware

## Does the Micropython port require a custom firmware build?

No, building a custom firmware is not necessary for the Micropython port.  By default, tight loops are optimized with the [Viper emitter](https://docs.micropython.org/en/latest/reference/speed_python.html#the-viper-code-emitter) which provides a significant performance boost.

That said, there are many benefits to a custom Micropython build:
- Next level performance with C optimized functions
- Byte frozen code for faster load/start time
- Easier (in my opinion) code iteration


# [Unix Port](unix/README.md)

# Embedded Ports (ESP32)
## [ProS3](pros3/README.md)
## [Lilygottwr](lilygottwr/README.md)

