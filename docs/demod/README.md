# Micro APRS DeModulation

DeModulation of AFSK samples into AX25 and APRS phrases.

Reviewing existing AFSK demodulation schemes primarily turned up FFT based demodulation implemented in C or using advanced math libraries.  In these implementations, band pass filters are designed to isolate mark and space frequencies individually to detect bits.  Exemplary examples used a variety of settings and gain values running many FFTsin parallel, to optimially detect across as many corner cases as possible.  

While this seems like a great idea, the idea of implementing FFT in Python, especially considering embedded systems and small computers as target ports, seems implausible.

Alternatively, I decided to go with an auto-correlator detection based approach.  This approach is integer only friendly, quite fir "looking" in implementation, and easy to optimize into C or specialized emitters (eg. [viper emitter in micropython](https://docs.micropython.org/en/v1.9.3/pyboard/reference/speed_python.html#the-viper-code-emitter)).


## Auto-Correlation Based Detection

![Correlator Block](corr_block.png?raw=true "Correlator Block")

The output of the block is:

$$ H(t) = sin(\omega t) sin(\omega(t+d)) $$

Using trig identity:

$$ sin(\alpha) sin(\beta) = \frac{1}{2} \left(cos(\alpha-\beta)-cos(\alpha+\beta) \right) $$

We find that:

$$ H(t) = \frac{1}{2} cos(\omega d) - \frac{1}{2} cos((d+2t)\omega)$$

![Mark Correlator Example](markcorr.gif?raw=true "Mark Correlator Example")

![DeModulation Block Diagram](demod_block.png?raw=true "DeModulation Block Diagram")

