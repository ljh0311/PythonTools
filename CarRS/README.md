# Car Rental Recommendation System

This system helps you choose the most cost-effective car rental option based on your travel needs.

## Overview

The recommendation system analyzes historical rental data to provide suggestions for which car rental service and car model would be most economical for your planned trip.

The system considers:
- Distance to travel
- Duration of rental
- Whether it's a weekend or weekday
- Different pricing models from various providers:
  - Getgo: $0.39/km + hourly rate
  - Car Club: $0.33/km + hourly rate
  - Tribecar (Econ/Stand): Only hourly rate (fuel not included)

## Requirements

- Python 3.6+
- pandas
- numpy
- matplotlib (for GUI version)
- tkinter (typically included with Python)

## Installation

1. Ensure Python 3.6+ is installed on your system
2. Install required packages:
   ```
   pip install pandas numpy matplotlib
   ```

## Usage

### Command Line Version

1. Make sure your rental data CSV file is in the same directory as the script
2. Run the script:
   ```
   python car_rental_recommender.py
   ```
   Or simply double-click on `run_recommender.bat` on Windows.
3. Choose from the main menu:
   - **Get Rental Recommendations**: Enter trip details and get cost comparisons
   - **Manage Rental Records**: Add, view, modify, or delete rental records
   - **Exit**: Close the application

### GUI Version

For a more user-friendly experience, you can use the GUI version:

1. Make sure your rental data CSV file is in the same directory as the script
2. Run the GUI script:
   ```
   python car_rental_recommender_gui.py
   ```
   Or simply double-click on `run_gui.bat` on Windows.

3. The application has four tabs:
   - **Recommendations**: Enter trip details and get recommendations with cost breakdown
   - **Data Analysis**: Analyze your historical rental data with charts
   - **Settings**: Customize fuel costs, mileage charges, and more
   - **Records Management**: Add, view, edit, and delete rental records

## Record Management Features

Both versions of the application allow you to manage your rental records:

### Command Line Version
- View all rental records in a tabular format
- Add new rental records with detailed information
- Modify existing records (update any field)
- Delete records you no longer need

### GUI Version
- Visual table display of all rental records
- Form-based interface for adding and editing records
- Detailed view of all record fields
- One-click record deletion with confirmation
- Changes are automatically saved to the CSV file

## Data Format

The system expects a CSV file with the following columns:
- Car model
- Distance (KM)
- Fuel pumped
- Estimated fuel usage
- Consumption (KM/L)
- Fuel cost
- Pumped fuel cost
- Mileage cost ($0.39)
- Cost per KM
- Duration cost
- Total
- Date
- Est original fuel savings
- Weekday/weekend
- Rental hour
- Car Cat
- Cost/HR

## Notes

- For Tribecar (Econ/Stand) rentals, the system estimates fuel costs based on the assumption that $20 worth of RON 95 fuel at Esso provides approximately 110km of distance.
- The recommendations are sorted by estimated total cost, with the most economical options listed first.
- The GUI version provides visual comparisons of costs and additional data analysis features.
- When adding new records, only a few fields are required (car model, provider, distance, duration, and total cost). Other fields can be left blank. 