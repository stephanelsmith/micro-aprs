#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting hackrf-aprsc setup..."

cd hackrf-aprs || { echo "Failed to enter hackrf-aprsc directory"; exit 1; }

# 2. Install GNU Radio
echo "Updating package lists..."
sudo apt-get update

echo "Installing GNU Radio..."
sudo apt-get install -y gnuradio

echo "Verifying GNU Radio installation..."
gnuradio-companion --version

# 3. Install Osmocom's osmosdr
echo "Installing Osmocom's osmosdr..."
sudo apt-get install -y libosmosdr-dev gr-osmosdr

echo "Verifying osmosdr installation..."
if gnuradio-companion --help | grep -q osmosdr; then
    echo "osmosdr is available in GNU Radio Companion."
else
    echo "osmosdr blocks not found in GRC. Please check the installation."
    exit 1
fi

# 4. Set Up a Python Virtual Environment
echo "Creating a Python virtual environment..."
python3 -m venv .venv --system-site-packages

# 5. Activate the Virtual Environment
echo "Activating the virtual environment..."
source .venv/bin/activate

# 6. Install Python Dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install ttkbootstrap numpy

echo "Setup completed successfully!"
echo "To activate the virtual environment in the future, run: source .venv/bin/activate"
