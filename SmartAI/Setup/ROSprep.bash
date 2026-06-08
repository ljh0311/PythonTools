# =============================================================================
# System Update and Package Installation
# =============================================================================

echo "🔄 Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "📦 Installing required system packages..."

# Python development tools
echo "🐍 Installing Python development packages..."
sudo apt install -y python3-pip python3-dev python3-venv

# Build tools and version control
echo "🔨 Installing build tools and Git..."
sudo apt install -y git cmake build-essential

# Scientific computing libraries
echo "🧮 Installing scientific computing libraries..."
sudo apt install -y libatlas-base-dev  # For numpy optimization

# Data storage and serialization
echo "💾 Installing HDF5 libraries..."
sudo apt install -y libhdf5-dev libhdf5-serial-dev

# GUI and Qt libraries
echo "🖥️  Installing GUI libraries..."
sudo apt install -y libqtgui4 libqtwebkit4 libqt4-test python3-pyqt5

# Multimedia and video processing
echo "🎥 Installing multimedia libraries..."
sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
sudo apt install -y libxvidcore-dev libx264-dev

# GTK development
echo "🎨 Installing GTK development libraries..."
sudo apt install -y libgtk-3-dev

# Boost libraries
echo "🚀 Installing Boost libraries..."
sudo apt install -y libboost-all-dev

echo "✅ Package installation completed!"

# Enable I2C, SPI, and GPIO
sudo raspi-config

# Clone the repository
git clone <your-repo-url>
cd SmartAI

# Create virtual environment
python3 -m venv robot_env
source robot_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add user to gpio group
sudo usermod -a -G gpio $USER

# Set GPIO permissions
sudo chown root:gpio /dev/gpiomem
sudo chmod g+rw /dev/gpiomem
