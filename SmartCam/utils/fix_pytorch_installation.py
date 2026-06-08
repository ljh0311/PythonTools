#!/usr/bin/env python3
"""
Script to fix PyTorch installation issues on Windows.
This script helps diagnose and fix the "WinError 193" PyTorch loading error.
"""

import sys
import subprocess
import os

def check_python_architecture():
    """Check if Python is 32-bit or 64-bit."""
    print("🔍 Checking Python architecture...")
    if sys.maxsize > 2**32:
        print(f"✅ Python is 64-bit (maxsize: {sys.maxsize})")
        return 64
    else:
        print(f"⚠️  Python is 32-bit (maxsize: {sys.maxsize})")
        print("   Note: PyTorch requires 64-bit Python on Windows")
        return 32

def check_pytorch_installation():
    """Check if PyTorch is installed and accessible."""
    print("\n🔍 Checking PyTorch installation...")
    try:
        import torch
        print(f"✅ PyTorch is installed: version {torch.__version__}")
        
        # Try to check if it's actually working
        try:
            x = torch.tensor([1.0])
            print("✅ PyTorch is functional")
            return True
        except Exception as e:
            print(f"❌ PyTorch is installed but not functional: {e}")
            return False
    except ImportError:
        print("❌ PyTorch is not installed")
        return False
    except OSError as e:
        print(f"❌ PyTorch installation error: {e}")
        print("   This is the error you're experiencing!")
        return False

def uninstall_pytorch():
    """Uninstall PyTorch and related packages."""
    print("\n🗑️  Uninstalling PyTorch and related packages...")
    packages = ['torch', 'torchvision', 'torchaudio']
    for package in packages:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', package], 
                         check=False, capture_output=True)
            print(f"   Uninstalled {package}")
        except Exception as e:
            print(f"   Warning: Could not uninstall {package}: {e}")

def install_pytorch_cpu():
    """Install CPU-only version of PyTorch (more reliable on Windows)."""
    print("\n📦 Installing PyTorch (CPU version)...")
    print("   This is the most reliable option for Windows.")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'torch', 'torchvision', 
                       '--index-url', 'https://download.pytorch.org/whl/cpu'], 
                      check=True)
        print("✅ PyTorch CPU version installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install PyTorch: {e}")
        return False

def install_pytorch_cuda():
    """Install CUDA version of PyTorch (if GPU is available)."""
    print("\n📦 Installing PyTorch (CUDA version)...")
    print("   This requires an NVIDIA GPU with CUDA support.")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'torch', 'torchvision', 
                       '--index-url', 'https://download.pytorch.org/whl/cu118'], 
                      check=True)
        print("✅ PyTorch CUDA version installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install PyTorch CUDA: {e}")
        return False

def verify_installation():
    """Verify that PyTorch is working correctly."""
    print("\n✅ Verifying PyTorch installation...")
    try:
        import torch
        print(f"   PyTorch version: {torch.__version__}")
        
        # Test basic functionality
        x = torch.tensor([1.0, 2.0, 3.0])
        y = x * 2
        print(f"   Test tensor operation: {y.tolist()}")
        
        # Check device
        if torch.cuda.is_available():
            print(f"   CUDA available: Yes (device: {torch.cuda.get_device_name(0)})")
        else:
            print("   CUDA available: No (using CPU)")
        
        print("✅ PyTorch is working correctly!")
        return True
    except Exception as e:
        print(f"❌ PyTorch verification failed: {e}")
        return False

def main():
    """Main function to fix PyTorch installation."""
    print("🔧 PyTorch Installation Fixer")
    print("=" * 50)
    print()
    
    # Check Python architecture
    arch = check_python_architecture()
    if arch == 32:
        print("\n⚠️  WARNING: You are using 32-bit Python.")
        print("   PyTorch requires 64-bit Python on Windows.")
        print("   Please install 64-bit Python from python.org")
        return
    
    # Check current installation
    pytorch_ok = check_pytorch_installation()
    
    if pytorch_ok:
        print("\n✅ PyTorch is already working correctly!")
        verify_installation()
        return
    
    # Ask user what to do
    print("\n" + "=" * 50)
    print("PyTorch needs to be reinstalled.")
    print("\nOptions:")
    print("1. Install CPU version (recommended, most reliable)")
    print("2. Install CUDA version (requires NVIDIA GPU)")
    print("3. Exit without changes")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        uninstall_pytorch()
        if install_pytorch_cpu():
            verify_installation()
    elif choice == "2":
        uninstall_pytorch()
        if install_pytorch_cuda():
            verify_installation()
    else:
        print("\nExiting without changes.")
        print("\nTo fix manually, run:")
        print("  pip uninstall torch torchvision torchaudio")
        print("  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")

if __name__ == "__main__":
    main()

