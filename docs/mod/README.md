


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

![Afsk](afsk_continuous.png?raw=true "Afsk")

Great!


## Discrete waveform generation

A key goal of this project is performance on embedded systems lacking a floating point unit.  As such, we need to be limited to integer only math as well as utilization of look-up tables for sinusoidal generation.

### Sin Lookup Table

First we will need a sin look-up table.  From [afsk/sin_table.py](https://github.com/stephanelsmith/micro-aprs-modem/blob/master/afsk/sin_table.py). 

```python
return array('h', (int((2**15-1)*math.sin(x)) for x in frange(0,2*math.pi,2*math.pi/size)))
```

![Discrete Sin](discrete_sin.png?raw=true "Discrete Sin")

This look-up table, either generated on start or pre-generated look-up table (default), will provide the values for the waveform
- Where the phase [0,PI) is mapped to [1,1024)
- Where the frequency is determined by iterative step size.

### Non-Integer Frequency Sample Correction

To faithfully reproduce a mark tone (1200 Hz) at a sampling rate of 22050 Hz, with a lookup table of size 1024, the stride length is:

$$ N_{markstep} = \frac{1024}{\frac{t_{mark}}{t_{s}}} = 55.7279 $$ 

While this wouldn't normally be a problem if we are solving sin directly and simply tracking the phase accumulation, because we are using integer math, rounding $N_{markstep}$ up or down with lead to a rapid frequency rate deviation.  It will be necessary to not only track the frequency step size, but also track the factional residue.

In our case, we pick a residue size of 10000, which leads us with a residue of 7279.

In implementation, we will accumulate the the phase (look-up table index) by 55 each iteration.  In a seperate residue accumulator, we increment by the residue amount of 7279.  We again increment the phase every time the residue accumulator is greater the the residue size (careful to keep the remainder amound in the residue accumulator.  In code:

```
mark_step_int = 55 
mark_residue = 7279
residue_size = 10000
markspace_index = 0  # the phase accumulator
markspace_residue_accumulator = 0

for t in range(tsim_array_size):
  # append the sample from the lookup table, 
	r.append(sin_array[markspace_index%lookup_size])

  # advanced the phase by the integer phase step size
	markspace_index += mark_step_int

  # advance the phase residue accumulator
	markspace_residue_accumulator += mark_residue

  # update the phase/residue accumulators if we exceed the residue size
	markspace_index += markspace_residue_accumulator // residue_size 
	markspace_residue_accumulator = markspace_residue_accumulator % residue_size
```

With this scheme, we are able to create the desired waveform, matching exact as well as floating point implementations.

![Compare Sin](sin_out.png?raw=true "Compare Sin")

### Putting it together

Each bit will need to include one baud period's worth of samples.  Similar to mark and space, you will need to track the phase and residue to account for the correct number of samples per bit.  By retaining the phase and residue between adjacent mark/space bits, the output is a continous waveform.

![Mark/Space](markspace_out.png?raw=true "Mark/Space")

 



