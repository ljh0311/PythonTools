# Car Rental Recommendation System

This application helps users find the best car rental option based on their trip details such as distance and duration.

## Files Overview

### Main Files (Use These)

- **CarRentalApp.bat** - The main launcher for the enhanced application (RECOMMENDED)
- **fixed_car_loader.py** - The enhanced loader script that fixes data issues and adds features

### Original Files

- **car_rental_recommender_gui.py** - The original GUI application
- **car_rental_recommender.py** - The original CLI application
- **22 - Sheet1.csv** - The data file with rental records

### Support Files (For Developers)

- **requirements.txt** - Lists all required Python packages

### Backup/Testing Files (Not Needed for Normal Use)

- **load_and_run.py** - Older script that attempted to load data
- **direct_load.py** - Older script that attempted to directly load data
- **run_gui.bat** - Original GUI launcher
- **run_recommender.bat** - Original CLI launcher
- **run_with_data.bat** - Testing launcher
- **run_fixed_app.bat** - Testing launcher
- **run_direct_load.bat** - Testing launcher

## How to Use

1. Double-click on **CarRentalApp.bat** to start the application
2. Enter your trip details:
   - Distance in kilometers
   - Duration in hours
   - Check "Weekend Trip" if applicable
3. Click "Get Recommendations" to see rental options

## Features

- Rental recommendations based on trip details
- Cost analysis and comparison between providers
- Records management for tracking past rentals
- Data analysis with charts and statistics

## Troubleshooting

If you encounter any issues:

1. Make sure **22 - Sheet1.csv** is in the same folder as the application
2. Check that all required Python packages are installed
3. Ensure you have Python 3.6 or newer installed

## Cleaning Up (Optional)

If you want to clean up unused files, you can safely delete these files:
- load_and_run.py
- direct_load.py
- run_gui.bat
- run_recommender.bat
- run_with_data.bat
- run_fixed_app.bat
- run_direct_load.bat 