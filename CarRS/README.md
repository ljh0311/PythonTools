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
2. Use the different tabs to access various features:

### Recommendations Tab

- Enter your trip details (distance, duration, weekend trip)
- Get personalized rental recommendations
- View cost comparisons and charts

### Data Analysis Tab

- View rental statistics and trends
- Analyze provider performance
- Export analysis results

### Records Management Tab

- Add, edit, or delete rental records
- Search and filter your rental history
- Export your rental data

### Cost Planning Tab (NEW!)

- Set a target monthly cost (e.g., $2000)
- Choose calculation type:
  - **Duration-based**: Calculate required mileage for your target cost and duration
  - **Mileage-based**: Calculate required duration for your target cost and mileage
- View booking scenarios to optimize your rental strategy
- See detailed cost breakdowns

## Features

- **Rental Recommendations**: Get personalized rental recommendations based on trip details
- **Cost Analysis**: Compare costs between different providers and car models
- **Records Management**: Track and manage your rental history
- **Data Analysis**: View charts and statistics of your rental patterns
- **Cost Planning**: Plan your rentals to reach target monthly costs (NEW!)
  - Calculate required mileage for target cost and duration
  - Calculate required duration for target cost and mileage
  - Generate booking scenarios to optimize your rental strategy
  - View detailed cost breakdowns

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
