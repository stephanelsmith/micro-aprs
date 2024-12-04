
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

Before you begin, ensure your system meets the following requirements:

- **Operating System:** Ubuntu/Linux (instructions are tailored for Ubuntu. For other OS, refer to respective documentation)
- **Git:** Installed for cloning the repository
- **Python 3:** Version 3.6 or later
- **pip:** Python package installer
- **Virtual Environment Module:** `venv` (comes pre-installed with Python 3. If not, install it using your package manager)

## Installation

Follow these steps to set up the `hackrf-aprsc` project on your system.

### 1. Clone the Repository

Begin by cloning the `hackrf-aprsc` repository from GitHub and navigating into the project directory:

```bash
git clone https://github.com/fpoisson2/hackrf-aprsc.git
cd hackrf-aprsc
```

### 2. Install GNU Radio

**GNU Radio** is an essential toolkit for building software-defined radios. The installation process varies based on your operating system. Below are instructions for Ubuntu/Linux. For other operating systems, refer to the [GNU Radio Installation Guide](https://wiki.gnuradio.org/index.php/InstallingGR).

#### For Ubuntu/Linux:

1. **Update Package Lists:**

   ```bash
   sudo apt-get update
   ```

2. **Install GNU Radio:**

   Install GNU Radio using the package manager:

   ```bash
   sudo apt-get install gnuradio
   ```

   *This command installs the latest stable version available in the Ubuntu repositories.*

3. **Verify Installation:**

   After installation, verify it by checking the version:

   ```bash
   gnuradio-companion --version
   ```

   This should display the installed GNU Radio version.

### 3. Install Osmocom's osmosdr

**Osmocom's osmosdr** provides drivers and modules for various SDR hardware, making it essential for this project.

#### For Ubuntu/Linux:

1. **Install Pre-built Packages:**

   ```bash
   sudo apt-get install libosmosdr-dev gr-osmosdr
   ```

2. **Verify Installation:**

   Launch GNU Radio Companion (GRC) and search for osmosdr-related blocks to ensure they are available.

### 4. Set Up a Python Virtual Environment

Creating a virtual environment ensures that project-specific dependencies are isolated from the system-wide Python installation.

1. **Create the Virtual Environment:**

   ```bash
   python3 -m venv .venv --system-site-packages
   ```

### 5. Activate the Virtual Environment

Activate the virtual environment to start using it.

```bash
source .venv/bin/activate
```

### 6. Install Python Dependencies

With the virtual environment activated, install the necessary Python packages using `pip`.

1. **Install `ttkbootstrap`:**

   ```bash
   pip install ttkbootstrap
   ```

2. **Install `numpy`:**

   ```bash
   pip install numpy
   ```




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
