# Micro APRS DeModulation

DeModulation of AFSK samples into AX25 and APRS phrases.

Reviewing existing AFSK demodulation schemes primarily turned up FFT based demodulation implemented in C or using advanced math libraries.  In these implementations, band pass filters are designed to isolate mark and space frequencies individually to detect bits.  Exemplary examples used a variety of settings and gain values running many FFTsin parallel, to optimially detect across as many corner cases as possible.  

While this seems like a great idea, the idea of implementing FFT in Python, especially considering embedded systems and small computers as target ports, seems implausible.

Alternatively, I decided to go with an auto-correlator detection based approach.  This approach is integer only friendly, quite fir "looking" in implementation, and easy to optimize into C or specialized emitters (eg. [viper emitter in micropython](https://docs.micropython.org/en/v1.9.3/pyboard/reference/speed_python.html#the-viper-code-emitter)).


## Auto-Correlation Based Detection

The block diagram for the correlator is as follows:

<p align="center">
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/demod/corr_block.png?raw=true" alt=""/>
</p>

$$ H(t) = sin(\omega t) sin(\omega(t+d)) $$

By trig identity:

$$ sin(\alpha) sin(\beta) = \frac{1}{2} \left(cos(\alpha-\beta)-cos(\alpha+\beta) \right) $$

We find the output is:

$$ H(t) = \frac{1}{2} cos(\omega d) - \frac{1}{2} cos((d+2t)\omega)$$

The first term, the DC component, ie. $` \frac{1}{2} cos(\omega d) `$ , is what we are seeking to detect.  Graphically, here we can see all the terms together.

<p align="center">
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/demod/markcorr.gif?raw=true" alt=""/>
</p>

![DeModulation Block Diagram](demod_block.png?raw=true "DeModulation Block Diagram")

