

## :iphone: Termux (Android) based APRS Beacon

* One goal is use a cell phone to generate beacon audio samples that can then be passed two a handy radio.  This is accomplished using [Termux](https://termux.dev/en/), a rad feature packed terminal for phones.  You will need to install it from F-Droid and install Termux-Api, which allows for fetching the GPS points. In termux, you can install python3, pypy3, sox, screen and any other goodies that suit your fancy.
* Modulate and play APRS becaons messages.  You will need:
  * Type-C to audio cable connected to the mic of your radio.  I opted for one with additional power connector.  In the developer settings for Android, I set screen to always be on when plugged in.
  * [3.5 mm TRS to Dual 3.5 mm TSF Stereo Breakout Cable](https://www.amazon.com/gp/product/B000068O5H/ref=ppx_yo_dt_b_asin_title_o06_s00?ie=UTF8&psc=1). The mic connector only uses the tip connector, the rest are grounded.
  * A 3.5 mm to 2.5 mm jumper.  My handy radio mic input is 2.5mm.
  * For my radio, I also needed to AC couple the the mic pin TIP like so. I couldn't find any suitable cables, so got the soldering iron out!  Not difficult!
<p align="center">
  <img src="https://github.com/stephanelsmith/micro-aprs/blob/master/docs/termux/ioqNL.png?raw=true" alt=""/>
</p>


### Examples
To be run in Termux.
 
* Fetch GPS points and generate beacon APRS messages 
```
python termux_beacon.py
```

* Play APRS beacon messages to radio
```
python termux_beacon.py | python aprs_mod.py -vox -t play -t -
```
