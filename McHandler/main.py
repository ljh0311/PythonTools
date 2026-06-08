#!/usr/bin/env python3
"""
Minecraft Mod Handler - Main entry point
"""

from gui import McHandlerGUI

def main():
    """Main entry point"""
    print("Starting Minecraft Mod Handler...")
    print("Make sure Ollama is running for AI features!")
    
    app = McHandlerGUI()
    app.run()

if __name__ == "__main__":
    main()