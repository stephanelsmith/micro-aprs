
# HackRF APRS Decoder

This project is a HackRF-based APRS (Automatic Packet Reporting System) implementation to handle the reception and transmission of APRS signals. It utilizes the HackRF device as an SDR (Software Defined Radio) for receiving and transmitting packets. This project is based on the excellent work from [micro-aprs](https://github.com/stephanelsmith/micro-aprs).

![image](https://github.com/user-attachments/assets/e1caabe6-4f9e-43e2-8c9f-90dff6370495)

---

## Features

- **APRS Reception**: Use `aprs_rx.py` to receive and decode APRS messages from live signals.
- **APRS Transmission**: Use `aprs_tx.py` to send APRS messages with a graphical interface.
- **HackRF Integration**: Full support for HackRF to handle both reception and transmission.
- **Python-based Design**: Easy to modify and extend for your specific needs.

---

## Prerequisites

Make sure you have the following installed on your system:

- Python 3.x
- Required Python modules (installable via `pip`):
  ```bash
  pip install -r requirements.txt
  ```
- GNU Radio and its dependencies.
- HackRF tools (e.g., `hackrf_transfer`).
- Tkinter and ttkbootstrap for the GUI.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/fpoisson2/hackrf-aprsc.git
   cd hackrf-aprsc
   ```

   2. Install GNU Radio
   3. Install osmosdr
   4. python3 -m venv .venv --system-site-packages
   5. source .venv/bin/activate
   6. pip install ttkbootstrap
   7. pip install numpy



---

## Usage

### APRS Reception

1. Connect your HackRF device to your system.
2. Run the APRS receiver script:
   ```bash
   python aprs_rx.py -i hackrf -o aprs -
   ```
3. This will start listening for APRS messages on the default frequency (144.39 MHz in North America). Messages will be displayed on the console.

### APRS Transmission

1. Launch the GUI for APRS transmission:
   ```bash
   python aprs_tx.py
   ```
2. Set the frequency, callsign, and other parameters in the GUI.
3. Queue and transmit APRS messages directly from the GUI.

---

## Key Components

### `aprs_rx.py`

Handles the reception and demodulation of APRS signals. It uses GNU Radio to process the input from the HackRF and decodes the packets.

### `aprs_tx.py`

Provides a GUI for sending APRS messages. It supports configuring the HackRF and transmitting custom APRS messages.

### `core.py`

Contains utility functions for HackRF management, generating APRS-compatible WAV files, and supporting communication protocols like UDP.

---

## Acknowledgments

This project is inspired by and built upon the work from [micro-aprs](https://github.com/stephanelsmith/micro-aprs).

---

## License

This project is released under the MIT License.
