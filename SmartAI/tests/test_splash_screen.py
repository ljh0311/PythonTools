#!/usr/bin/env python3
"""
Test script to demonstrate the splash screen functionality.
This script shows how the splash screen works without running the full robot system.
"""

import tkinter as tk
import sys
import os
import time
import threading

# Add the gui/dialogs directory to the path (updated for tests/ folder location)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gui', 'dialogs'))

def test_splash_screen():
    """Test the splash screen functionality"""
    
    # Create a temporary root window
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    def simulate_loading():
        """Simulate loading process"""
        print("Starting loading simulation...")
        time.sleep(1)
        print("Loading robot configuration...")
        time.sleep(0.5)
        print("Initializing hardware components...")
        time.sleep(0.5)
        print("Setting up motor controllers...")
        time.sleep(0.5)
        print("Configuring sensors...")
        time.sleep(0.5)
        print("Preparing navigation system...")
        time.sleep(0.5)
        print("Starting autonomous controller...")
        time.sleep(0.5)
        print("Launching control interface...")
        time.sleep(0.5)
        print("Loading complete!")
    
    def on_splash_complete():
        """Called when splash screen completes"""
        print("Splash screen completed!")
        root.quit()
    
    try:
        # Import the splash screen
        from robot_splash_screen import RobotSplashScreen
        
        print("Creating splash screen...")
        
        # Create splash screen
        splash = RobotSplashScreen(root, on_splash_complete)
        
        # Start loading simulation in background
        loading_thread = threading.Thread(target=simulate_loading, daemon=True)
        loading_thread.start()
        
        print("Splash screen created. Starting main loop...")
        
        # Run the splash screen
        root.mainloop()
        
        print("Main loop completed.")
        
    except ImportError as e:
        print(f"Error importing splash screen: {e}")
        print("Make sure the robot_splash_screen.py file is in the gui/dialogs directory.")
    except Exception as e:
        print(f"Error running splash screen: {e}")
    
    finally:
        # Clean up
        try:
            root.destroy()
        except:
            pass
    
    print("Test completed!")

if __name__ == "__main__":
    test_splash_screen() 

