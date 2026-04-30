# Car Rental Recommendation System

This application helps users find the best car rental option based on their trip details such as distance and duration.

## Files Overview

### Main Files (Use These)

- **CarRentalApp.bat** - The main launcher for the enhanced application (RECOMMENDED)
- **car_rental_recommender_gui.py** - The main GUI application with recommendations, EV support, reasoning display, and management tabs
- **car_rental_recommender_core.py** - Shared recommendation and data-processing logic used by the GUI

### Data and Configuration

- **22 - Sheet1.csv** - The data file with rental records
- **settings.json** - Application settings

### Support Files (For Developers)

- **requirements.txt** - Lists all required Python packages
- **test_ev_functionality.py** - Tests EV-specific recommendation behavior
- **test_reasoning_display.py** - Tests reasoning display behavior
- **ML_RECOMMENDATIONS_README.md** - Notes for machine-learning recommendation features
- **OLLAMA_INTEGRATION_README.md** - Notes for local AI/Ollama integration
- **EV_FEATURES_SUMMARY.md** - Summary of EV support
- **IMPLEMENTATION_COMPLETE.md** - Implementation summary

### Backup/Testing Files (Not Needed for Normal Use)

- **zzGG.py** - Legacy/experimental helper; avoid using it for normal application startup unless it is explicitly maintained

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

Review legacy files before deleting them. The current launcher still calls `fixed_car_loader.py`, but that file is not present in the checked-in project. Update the launcher or restore the loader before relying on the batch startup path.

