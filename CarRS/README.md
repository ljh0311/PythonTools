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
3. Enter your planned trip details when prompted:
   - Distance in kilometers
   - Duration in hours
   - Whether it's a weekend trip

4. Review the top 5 recommendations based on estimated cost

### GUI Version

For a more user-friendly experience, you can use the GUI version:

1. Make sure your rental data CSV file is in the same directory as the script
2. Run the GUI script:
   ```
   python car_rental_recommender_gui.py
   ```
   Or simply double-click on `run_gui.bat` on Windows.

3. The application has three tabs:
   - **Recommendations**: Enter trip details and get recommendations with cost breakdown
   - **Data Analysis**: Analyze your historical rental data with charts
   - **Settings**: Customize fuel costs, mileage charges, and more

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