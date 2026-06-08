#!/usr/bin/env python3
"""
CDID Car Tuning Assistant - Web launcher
(Roblox CDID car tuning – runs on http://localhost:5001)
"""

import os
import sys

def main():
    # Run from cdid_car_tuning so templates/static and imports work
    root = os.path.dirname(os.path.abspath(__file__))
    cdid_dir = os.path.join(root, 'cdid_car_tuning')
    if not os.path.isdir(cdid_dir):
        print("Error: cdid_car_tuning folder not found.")
        sys.exit(1)
    os.chdir(cdid_dir)
    sys.path.insert(0, cdid_dir)

    print("CDID Car Tuning Assistant (Roblox)")
    print("=" * 50)
    print("Starting web app at http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    from app import app
    # use_reloader=False: launcher does os.chdir(), so reloader would look for this script in cdid_car_tuning/ and fail
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)

if __name__ == "__main__":
    main()
