


# Micro APRS Modulation

Modulation and generation of the AFSK signal is a fairly straight forward process.  Working bottom up:

## Ideal waveform generation

First step is to generate the mark (1200Hz) and space (2200Hz) waveforms.  As a continuous functions:
  
![AFSK Mark](mark.png?raw=true "Mark Waveform")
![AFSK Space](space.png?raw=true "Space Waveform")

If we represent mark as +1 and space as -1, we can modulate the 
$$afsk(t) = cos\left(2 \pi f_c t + 2 \pi \Delta f  \int_{0}^t m[s] d s \right) $$

Direct evaluation with Mathematica yields 

![AFSK Square](square.png?raw=true "Square Waveform")

![AFSK Square](afsk_continuous.png?raw=true "Afsk")

Great!


## Discrete waveform generation

A key goal of this project is performance on embedded systems lacking a floating point unit.  As such, we need to be limited to integer only math as well as utilization of look-up tables for sinusoidal generation.

### Sin Lookup Table

First we will need a sin look-up table.  From [afsk/sin_table.py](https://github.com/stephanelsmith/micro-aprs-modem/blob/master/afsk/sin_table.py)

```python
return array('h', (int((2**15-1)*math.sin(x)) for x in frange(0,2*math.pi,2*math.pi/size)))
```


