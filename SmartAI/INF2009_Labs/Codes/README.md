# Deep Learning on Edge - MobileNetV2 Performance Testing

This guide will help you run MobileNetV2 performance tests on your Raspberry Pi 400, comparing basic and quantized versions of the model.

## Prerequisites

1. Raspberry Pi 400 with Raspbian OS
2. Webcam connected and working
3. Internet connection for package installation
4. SSH access to your Raspberry Pi (if transferring files from another computer)

## Step-by-Step Setup

### 1. File Transfer
Transfer all files to your Raspberry Pi 400 using one of these methods:

**Option A: Using the transfer script (from Windows)**
```bash
./Codes/transfer.ps1 -RaspberryPiIP "YOUR_PI_IP_ADDRESS"
```

**Option B: Manual transfer (from any OS)**
```bash
scp -r Codes/* pi@YOUR_PI_IP:~/dlonedge/
```

### 2. Environment Setup
SSH into your Raspberry Pi and run:
```bash
cd ~/dlonedge
chmod +x setup.sh
./setup.sh
```

### 3. Camera Setup
Ensure your camera is properly configured:
```bash
# Enable camera interface
sudo raspi-config
# Navigate to: Interface Options > Camera > Enable

# If using USB webcam, load video module
sudo modprobe bcm2835-v4l2

# Verify camera is detected
v4l2-ctl --list-devices
```

### 4. Running the Tests
```bash
# 1. Activate the virtual environment
source dlonedge/bin/activate

# 2. Run the lab runner
python3 lab_runner.py
```

## Expected Output

The script will run three tests in sequence:

1. **Basic MobileNetV2**
   - Expected FPS: 5-6 frames per second
   - No quantization optimizations

2. **Quantized MobileNetV2**
   - Expected FPS: 15-30 frames per second
   - Uses QNNPACK quantization engine
   - Should show significant performance improvement

3. **Quantized MobileNetV2 with Predictions**
   - Similar FPS to regular quantized version
   - Displays top 10 predictions for each frame

### Results File
- All results are saved in `lab_results.md`
- The file includes:
  - System information
  - Test timestamps
  - FPS measurements for each test
  - Average FPS calculations
  - Any warnings or errors

## Troubleshooting

### Common Issues

1. **Camera Not Working**
   ```bash
   # Check camera status
   v4l2-ctl --list-devices
   
   # If no devices listed, try:
   sudo modprobe bcm2835-v4l2
   ```

2. **QNNPACK Not Available**
   ```bash
   # Verify PyTorch installation
   python3 -c "import torch; print(torch.__version__)"
   
   # Check QNNPACK support
   python3 -c "import torch; print(torch.backends.quantized.supported_engines)"
   ```

3. **Low FPS**
   - Ensure no other intensive processes are running
   - Check CPU temperature: `vcgencmd measure_temp`
   - Consider using a fan if temperature is above 80°C

### Error Messages

- "RuntimeError: QNNPACK not available": This is normal on non-ARM platforms
- "Failed to read frame": Check camera connection and permissions
- "Import Error": Run `pip install -r requirements.txt` again

## Additional Notes

- The quantized model should show significantly better performance than the basic model
- FPS measurements are averaged over multiple readings for accuracy
- Tests automatically stop after collecting sufficient measurements
- Results are saved with timestamps for easy comparison between runs 