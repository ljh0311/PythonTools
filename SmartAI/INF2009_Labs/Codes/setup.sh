#!/bin/bash

echo "Setting up Deep Learning on Edge environment..."

# Create and activate virtual environment
echo "Creating virtual environment..."
python3 -m venv dlonedge
source dlonedge/bin/activate

# Install required packages
echo "Installing required packages..."
pip3 install --upgrade pip
pip3 install torch torchvision torchaudio
pip3 install opencv-python
pip3 install numpy --upgrade

# Create results directory
mkdir -p results

echo "Setup complete! To run tests:"
echo "1. Activate the environment: source dlonedge/bin/activate"
echo "2. Run the tests: python3 run_tests.py" 