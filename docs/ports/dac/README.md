# 〰️ ESP32S3 Digital to Analog Considersations

The ESP32S3 is full of built-in features from bluetooth to USB, but surprisingly lacks a DAC!  Some ESP32 skus have an [I2S to internal DAC](https://docs.espressif.com/projects/esp-idf/en/v4.4.1/esp32/api-reference/peripherals/i2s.html#configuring-i2s-to-use-internal-dac-for-analog-output) which sounds like a great feature, but unfortunately, not only does the ESP32S3 version no have it, this feature is deprecated... bummer.

The recommended way forward is to either use the PWM (their LEDC peripheral) or [Sigma-Delta output, either way you low pass filter the output to generate the output level](https://github.com/espressif/esp-idf/tree/b4268c874a4cf8fcf7c0c4153cffb76ad2ddda4e/examples/peripherals/sigma_delta/sdm_dac).  

Here we choose the PWM route simply because Micropython already has PWM support for the ESP32S3 target.  

### Output filter
As the PWM is digital, and output LPF, where $` R = 5.6k Ohm `$ and $` C = 47n F `$.  That gives about a 600Hz cutoff covering $`f_{mark} = 1200Hz`$ and $`f_{space} = 2200Hz`$.

### AFSK Output rate comparison
AFSK sampling rates from 11k to 44k all functional for creating demodulatable signal.  One consideration I noticed was at 44.1kHz, the microcontroller was periodically having issues keeping up.  Recommendation going with 22kHz or even 11kHz depending on application and timing margin needed.

#### 44.1kHz
<img src="44k.jpg" width="600">

#### 22.05kHz
<img src="22k.jpg" width="600">

#### 11.025kHz
<img src="11k.jpg" width="600">


### Input filtering
For input filtering $` R = 5.6k Ohm `$ and $` C = 10n F `$.  That gives about a 3000Hz cutoff covering $`f_{mark} = 1200Hz`$ and $`f_{space} = 2200Hz`$.  We also add an aditional scaling factor as ADC expects a 0-1V.

[Click here to visit CircuitJs simulation](https://www.falstad.com/circuit/circuitjs.html?ctz=CQAgjCAMB0l3BWc0DscBMkDMBOHAWOAydEBSMsihAUwFowwAoAcxEIq03bhCwVIVITAE4h0CAGzhJnATKFlZwgMY8KYWer7d84egA4o0SWAM4wCLAcgF05rHphwIwzCnGQjYfHszewUj0ANwBLADsmd21NCg5wQPYQYIB7AFcAFyYAdz55WJitYVz-BU9vXygc8rKJaQLhACUysBR6rXR0PQhSCU5xaCQhQaYC0oLA7w7PcHg5+AGEJmD2Cu77cEqNcEwNQeQh4yWV-G82nbPpbc7eMH27w5gltlPwc9fSoWrX1ukfrdEeV6KFI-F6Xig4l21TBZVhnxh8nQIKBOi+bFhXDkoPkXxSSVcO3QOCM6GgeHQWEgkiwZk6gQIWGM8EJoKqQA)
<br>

<img src="circuit-20250518-2010.svg" alt="" width="600"><br>

## :raised_hands: Acknowledgements
- [Falsatd's CircuitJs](https://www.falstad.com/circuit/circuitjs.html)
- [E32-S3 no DAC - No Problem! We'll Use PDM](https://www.atomic14.com/2024/01/05/esp32-s3-no-pins.html#:~:text=So%2C%20there's%20no%20DAC%20on,and%20use%20an%20analog%20amplifier.)
- [ESP32-S3 howto ADC and DAC](https://github.com/nakhonthai/ESP32APRS_T-TWR/tree/main/doc)


