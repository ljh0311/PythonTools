# Time Logger Application

A Python desktop application for tracking work hours, calculating earnings, and generating reports.

## Features

- **Time Logging**: Track work hours with start/end times and break durations
- **Reporting**: Generate reports with visualizations for different time periods
- **Payroll Periods**: Define and manage custom payroll periods
- **Data Export**: Export data to CSV, Excel, and PDF formats
- **Data Visualization**: View charts showing hours worked and earnings

## Code Improvements

The codebase has been improved in several key areas:

### 1. Date Handling

- Created a dedicated `DateUtils` class that centralizes all date formatting and conversion logic
- Eliminated redundant date parsing code throughout the application
- Standardized error handling for date conversions
- Clear distinction between display dates (DD/MM/YYYY) and database dates (YYYY-MM-DD)

### 2. Database Operations

- Created a `DBUtils` class that provides a clean interface for database operations
- Implemented common query patterns to reduce redundancy
- Added better error handling for database operations
- Simplified database operations with higher-level methods

### 3. Error Handling

- Implemented a decorator pattern for consistent error handling
- Added proper logging of errors to console
- Improved user feedback for errors
- Reduced code duplication in try/except blocks

### 4. Code Organization

- Reduced redundancy in chart generation code
- Created helper methods for common UI tasks
- Improved method naming for clarity
- Used consistent parameter naming

## Installation

1. Clone the repository:
```
git clone <repository-url>
```

2. Install required packages:
```
pip install -r requirements.txt
```

3. Run the application:
```
python time_logger.py
```

## Dependencies

- Python 3.6+
- Tkinter (included with most Python installations)
- Matplotlib
- Pandas
- tkcalendar
- openpyxl (for Excel export)
- reportlab (for PDF export, optional)

## Usage

1. **Log Time Tab**: Enter work hours and save entries
2. **View Records Tab**: View, edit, and delete work records
3. **Payroll Periods Tab**: Create and manage payroll periods
4. **Reports Tab**: Generate reports and visualizations

## Database

The application uses SQLite to store data in a file named `timelog.db`. All work records are also backed up to a CSV file named `work_records.csv`.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 