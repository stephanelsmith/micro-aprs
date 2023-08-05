# Micro APRS DeModulation

DeModulation of AFSK samples into AX25 and APRS phrases.

Reviewing existing AFSK demodulation schemes primarily turned up FFT based demodulation implemented in C or using advanced math libraries.  In these implementations, band pass filters are designed to isolate mark and space frequencies individually to detect bits.  Exemplary examples used a variety of settings and gain values running many FFTs in parallel, to optimially detect across as many corner cases as possible.  

While this seems like a great idea, the idea of implementing FFT in Python, especially considering embedded systems and small computers as target ports, seems implausible considering the computational intensity.

Alternatively, I decided to go with an auto-correlator detection based approach.  This approach is integer only friendly, quite fir "looking" in implementation, and easy to optimize into C or specialized emitters (eg. [viper emitter in micropython](https://docs.micropython.org/en/v1.9.3/pyboard/reference/speed_python.html#the-viper-code-emitter)).

Diving in...

## AFSK Auto-Correlation Based Detection

### Correlator Concept

The block diagram for the correlator is as follows:

<p align="center">
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/demod/corr_block.png?raw=true" alt=""/>
</p>

$$ H(t) = sin(\omega t)  sin(\omega(t+d)) $$

Where $` d `$  is the delay introduced by the delay block.  By trig identity:

$$ sin(\alpha) sin(\beta) = \frac{1}{2} \left(cos(\alpha-\beta)-cos(\alpha+\beta) \right) $$

We find the output is:

$$ H(t) = \frac{1}{2} cos(\omega_{mark} d) - \frac{1}{2} cos((d+2t)\omega_{mark})$$


The first term, the DC component, ie. $` \frac{1}{2} cos(\omega_{mark} d) `$ , is our signal detect.  Graphically, here we can see all the terms together.

<p align="center">
  <br>
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/demod/markcorr.gif?raw=true" alt=""/>
</p>

### Mark and Space Detection

Next step is to detect both mark and space frequencies.  A clever concept I found for 2 FSK is to optimially pick the delay $` d `$ as to maximize the difference between the two DC terms $` \frac{1}{2} cos(\omega_{mark} d) `$ and $` \frac{1}{2} cos(\omega_{space} d) `$

$$ MarkSpace(t) = \frac{1}{2} cos(\omega_{mark} d_{optimal}) - \frac{1}{2} cos(\omega_{space} d_{optimal}) $$

where $` d_{optimal} `$ is chosen to _maximize_ $` MarkSpace(t) `$.  Below, we show MarkSpace(t), Mark, and Space.  Searching iteratively, we find  $` d_{optimal} = 446 \micro s `$.  Graphically, $` d_{optimal} = 446 \micro s `$ is indicated by the red dashed line.  If you watch carefully, you will notice the DC level for mark and space are at their extremes.

<p align="center">
    <br>
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/demod/markspacecorrdelay.gif?raw=true" alt=""/>
</p>

Armed with this knowledge we now know if we delay the AFSK input signal by $` d_{optimal} = 446 \micro s `$, and filter out the ripple terms, we are able to detect marks as values < 0 and spaces as values > 0.  Incredibly, the detection algorithm only cost us a delay element (if sampling at 22050 Hz, a delay or buffer depth of 10 samples) and some multiplications!



### Top Level Diagram

To put everything together, we need two more blocks:
- A bandpass filter in the front, isolating the Mark/Space frequencies of interest.
- A low pass filter in the back, removing the correlator ripples leaving just the DC "value detection" term.
- A signal detector which includes clock recovery and bit sampler.

![DeModulation Block Diagram](demod_block.png?raw=true "DeModulation Block Diagram")


### Bandpass FIR filters

Now onto the input filter.  The goal here is to remove any DC offsets and any 'noise' out of band.  While I found that sane values can be picked to get a functional demodulator, I recommend final parameter tuning using real-world test, eg. track 2 of the TNC test CD.

I've picked a gain of 1x of 0dB at mark (1200Hz) and space (2200Hz) frequencies.

Using Mathematica's filter designer:
```
taps = LeastSquaresFilterKernel[{"Bandpass", {fMark (2 \[Pi])/fs - 
      fPad (2 \[Pi])/fs, fSpace (2 \[Pi])/fs + fPad (2 \[Pi])/fs}}, 
   n];
```

In Python, you can find the filter taps similarly as done in the [afsk/bandpass_fir_design](https://github.com/stephanelsmith/micro-aprs/blob/b9f495bdfbe1bea1bd5a199fc17ff02f6e048a79/afsk/func.py#L163) function:
```
    from scipy import signal
    coefs = signal.firls(ncoefs,
                        (0, fmark-width, fmark, fspace, fspace+width, fs/2),
                        (0, 0,           amark, aspace, 0,            0),
                        fs=fs)
```

For the location of zeros, we apply the Z transform and solve for the solution (in Mathematica again):
```
zexpr = ListZTransform[taps, z];
zs = z /. NSolve[zexpr == 0, z];
```

I always recommend looking at the Z-plane when designing filter, as the zero placement really helps one understand how the coefficients shape the magnitude response.  The resulting filter looks as follows:

![Bandpass Filter](bandpass_filter.png?raw=true "Bandpass Filter")

### Lowpass FIR filters

Same process for the low pass filter. Here, my initial filter design cutoff is 1200Hz.  For fun, including phase, group delay, and step response.  In the Z place, notice how the zeros on the real axis boost the gain, and how the zeros along the unit circle suppress the magnitude after our cutoff.

![Lowpass filter](lowpass_filter.png?raw=true "Lowpass filter")

### Output

After the low pass filtering of the correlated output, we have

<p align="center">
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/demod/corr_total.gif?raw=true" alt=""/>
</p>


### Digitizer

Here we convert the samples into bits.  Many implementations I found have feedback based clock recovery schemes.  However, I found that simple edge detection is doing a surprisingly good job, even for real-life tests and Track 2 of the TNC test CD.  This is the route I went here.  The other benefit being this scheme allows for decoding a signal after just a single header, while other methods used 25+ header bytes to lock the clock (I believe).

All-in-all, I didn't really do too much here.  This is an area of future work, but it's working to my satisfaction, requires very little compute in the spirit of this project.


### Final Thoughts

Incredibly, it turns out afsk demod comes down to:
- *Shift*: (generate the delayed signal)
- *Multiply*: (multiply delayed signal to signal)
- *Convolve*: (run the low pass fir)

Cool!
  
### References and Acknowledgements

Lots of good work out there which assisted me in my process, most notibly the following:
- [PSoC® 1 - Simplified FSK Detection](https://www.infineon.com/dgdl/Infineon-AN2336_PSoC_1_Simplified_FSK_Detection-ApplicationNotes-v07_00-EN.pdf?fileId=8ac78c8c7cdc391c017d07237cdd46c0)
- [AFSK Digital Correlator Demodulator](https://notebooks.githubusercontent.com/view/ipynb?browser=chrome&color_mode=auto&commit=18914893d0853070788a37d986bbd58db08721aa&device=unknown&enc_url=68747470733a2f2f7261772e67697468756275736572636f6e74656e742e636f6d2f6d6f62696c696e6b642f6166736b2d64656d6f64756c61746f722f313839313438393364303835333037303738386133376439383662626435386462303837323161612f6166736b2d64656d6f64756c61746f722e6970796e62&logged_in=false&nwo=mobilinkd%2Fafsk-demodulator&path=afsk-demodulator.ipynb&platform=android&repository_id=175103461&repository_type=Repository&version=98)
- [Direwolf - A-Better-APRS-Packet-Demodulator-Part-1-1200-baud.pdf](https://github.com/wb2osz/direwolf/blob/master/doc/A-Better-APRS-Packet-Demodulator-Part-1-1200-baud.pdf)
- [Not Black Magic - AFSK](https://www.notblackmagic.com/bitsnpieces/afsk/)

