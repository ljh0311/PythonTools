import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sqlite3
import csv
from datetime import datetime, timedelta
import calendar
import matplotlib
matplotlib.use('TkAgg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import Calendar
from openpyxl.styles import Font
import traceback
import functools

# Constants
DATE_FORMAT = "%d/%m/%Y"
DB_DATE_FORMAT = "%Y-%m-%d"  # Format for dates stored in the database
DEFAULT_DATE_RANGE = ("01/04/2025", "30/04/2025")  # Fallback dates

# Decorator for error handling
def handle_errors(show_message=True, return_value=None):
    """Decorator to handle errors consistently throughout the application.
    
    Args:
        show_message (bool): Whether to show a message box with the error
        return_value: Value to return if an error occurs
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Error in {func.__name__}: {str(e)}")
                traceback.print_exc()
                
                if show_message and hasattr(args[0], 'root'):
                    messagebox.showerror("Error", f"{func.__name__} error: {str(e)}")
                return return_value
        return wrapper
    return decorator


class DateUtils:
    """Utility class for date operations"""
    
    @staticmethod
    def format_date_for_display(date_str):
        """Convert a date string to display format (dd/mm/yyyy)"""
        if not date_str:
            return ""
            
        try:
            # If the date is in DB format (yyyy-mm-dd)
            if '-' in date_str:
                date_obj = datetime.strptime(date_str, DB_DATE_FORMAT).date()
                return date_obj.strftime(DATE_FORMAT)
            # If already in display format
            elif '/' in date_str:
                # Validate the format
                datetime.strptime(date_str, DATE_FORMAT)
                return date_str
            else:
                # Unknown format
                return date_str
        except ValueError:
            # Return original if conversion fails
            return date_str
    
    @staticmethod
    def format_date_for_db(date_str):
        """Convert a date string to database format (yyyy-mm-dd)"""
        if not date_str:
            return date_str
            
        try:
            # If already in DB format
            if '-' in date_str:
                # Validate the format
                datetime.strptime(date_str, DB_DATE_FORMAT)
                return date_str
            # If in display format
            elif '/' in date_str:
                date_obj = datetime.strptime(date_str, DATE_FORMAT).date()
                return date_obj.strftime(DB_DATE_FORMAT)
            else:
                # Unknown format
                return date_str
        except ValueError:
            # Return original if conversion fails
            return date_str
    
    @staticmethod
    def string_to_date(date_str):
        """Convert a date string to a datetime.date object"""
        if not date_str:
            return datetime.now().date()
            
        try:
            if '/' in date_str:
                return datetime.strptime(date_str, DATE_FORMAT).date()
            elif '-' in date_str:
                return datetime.strptime(date_str, DB_DATE_FORMAT).date()
            else:
                # Default to today if format unknown
                return datetime.now().date()
        except ValueError:
            # Return today if conversion fails
            return datetime.now().date()
    
    @staticmethod
    def date_to_string(date_obj, for_db=False):
        """Convert a date object to string in the appropriate format"""
        if not isinstance(date_obj, (datetime.date, datetime.datetime)):
            return ""
            
        if for_db:
            return date_obj.strftime(DB_DATE_FORMAT)
        else:
            return date_obj.strftime(DATE_FORMAT)
    
    @staticmethod
    def get_today():
        """Get today's date as a datetime.date object"""
        return datetime.now().date()
    
    @staticmethod
    def get_date_range(option):
        """Get start and end dates based on a predefined range option"""
        today = datetime.now().date()
        current_month = today.month
        current_year = today.year
        
        if option == "today":
            return today, today
            
        elif option == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
            
        elif option == "this_week":
            # Start of the week (Monday) to today
            start_date = today - timedelta(days=today.weekday())
            return start_date, today
            
        elif option == "last_week":
            # Last week's Monday to Sunday
            start_date = today - timedelta(days=today.weekday() + 7)
            end_date = start_date + timedelta(days=6)
            return start_date, end_date
            
        elif option == "this_month":
            # First day of current month to today
            start_date = today.replace(day=1)
            return start_date, today
            
        elif option == "last_month":
            # Calculate previous month
            if current_month == 1:  # January
                previous_month = 12
                previous_year = current_year - 1
            else:
                previous_month = current_month - 1
                previous_year = current_year
                
            # First day of previous month
            first_day = datetime(previous_year, previous_month, 1).date()
            
            # Last day of previous month
            if previous_month == 12:  # December
                last_day = datetime(previous_year, 12, 31).date()
            else:
                last_day = datetime(current_year, current_month, 1).date() - timedelta(days=1)
                
            return first_day, last_day
            
        elif option == "this_year":
            # January 1st of current year to today
            start_date = datetime(current_year, 1, 1).date()
            return start_date, today
            
        elif option == "last_year":
            # Full previous year
            previous_year = current_year - 1
            start_date = datetime(previous_year, 1, 1).date()
            end_date = datetime(previous_year, 12, 31).date()
            return start_date, end_date
            
        # Default to this month
        start_date = today.replace(day=1)
        return start_date, today


class DBUtils:
    """Utility class for database operations"""
    
    def __init__(self, conn, cursor):
        self.conn = conn
        self.cursor = cursor
    
    def execute_query(self, query, params=None, commit=False):
        """Execute a database query and return results
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for the query
            commit (bool): Whether to commit after executing
            
        Returns:
            list: Query results or None if error
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            if commit:
                self.conn.commit()
                
            # For SELECT queries
            if query.strip().upper().startswith("SELECT"):
                return self.cursor.fetchall()
            return None
        except Exception as e:
            print(f"Database error: {str(e)}")
            if commit:
                self.conn.rollback()
            return None
    
    def insert_record(self, table, data):
        """Insert a record into a table
        
        Args:
            table (str): Table name
            data (dict): Column names and values to insert
            
        Returns:
            bool: Success status
        """
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            self.cursor.execute(query, tuple(data.values()))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Insert error: {str(e)}")
            self.conn.rollback()
            return False
    
    def update_record(self, table, data, condition):
        """Update records in a table
        
        Args:
            table (str): Table name
            data (dict): Column names and values to update
            condition (tuple): (where_clause, params) 
            
        Returns:
            bool: Success status
        """
        try:
            set_clause = ', '.join([f"{col} = ?" for col in data.keys()])
            where_clause, where_params = condition
            
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            params = tuple(data.values()) + where_params
            
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Update error: {str(e)}")
            self.conn.rollback()
            return False
    
    def delete_record(self, table, condition):
        """Delete records from a table
        
        Args:
            table (str): Table name
            condition (tuple): (where_clause, params)
            
        Returns:
            bool: Success status
        """
        try:
            where_clause, params = condition
            query = f"DELETE FROM {table} WHERE {where_clause}"
            
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Delete error: {str(e)}")
            self.conn.rollback()
            return False
    
    def get_date_filtered_records(self, table, from_date=None, to_date=None, 
                                  additional_conditions=None, order_by="date DESC"):
        """Get records filtered by date range
        
        Args:
            table (str): Table name
            from_date (str, optional): Start date in any format
            to_date (str, optional): End date in any format
            additional_conditions (tuple, optional): (clause, params)
            order_by (str): ORDER BY clause
            
        Returns:
            list: Query results or empty list if error
        """
        try:
            # Convert dates to database format
            db_from_date = DateUtils.format_date_for_db(from_date) if from_date else None
            db_to_date = DateUtils.format_date_for_db(to_date) if to_date else None
            
            # Build query
            query = f"SELECT * FROM {table} WHERE 1=1"
            params = []
            
            if db_from_date:
                query += " AND date >= ?"
                params.append(db_from_date)
                
            if db_to_date:
                query += " AND date <= ?"
                params.append(db_to_date)
                
            # Add any additional conditions
            if additional_conditions:
                clause, add_params = additional_conditions
                query += f" AND {clause}"
                params.extend(add_params)
                
            # Add order by
            if order_by:
                query += f" ORDER BY {order_by}"
                
            # Execute query
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Date filter query error: {str(e)}")
            return []


class TimeLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Work Time Logger")
        self.root.geometry("1200x750")  # Increased window size
        self.root.resizable(True, True)
        
        # Configure matplotlib to avoid memory leaks
        plt.rcParams['figure.max_open_warning'] = 10
        matplotlib.rcParams['figure.figsize'] = [9, 10]
        
        # Set application theme and styles
        self.set_application_theme()
        
        # Initialize database and CSV storage
        self.initialize_database()
        self.csv_file_path = "data/work_records.csv"
        self.ensure_csv_exists()
        
        # Set up database utilities
        self.db_utils = DBUtils(self.conn, self.cursor)
        
        # Create main notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_log_tab()
        self.create_view_tab()
        self.create_payroll_tab()
        self.create_report_tab()
        
        # Initialize date range with available dates
        self.update_date_range()
        
    def set_application_theme(self):
        """Set up custom styles and theme for the application"""
        # Define colors
        self.primary_color = "#1976D2"  # Blue
        self.secondary_color = "#2196F3"  # Lighter blue
        self.accent_color = "#FF5722"  # Orange
        self.success_color = "#4CAF50"  # Green
        self.warning_color = "#FFC107"  # Amber
        self.error_color = "#F44336"  # Red
        self.background_color = "#F5F5F5"  # Light gray
        self.text_color = "#212121"  # Dark gray
        
        # Set window background color
        self.root.configure(background=self.background_color)
        
        # Create custom styles
        style = ttk.Style()
        
        # Configure Frame style
        style.configure("TFrame", background=self.background_color)
        style.configure("TLabelframe", background=self.background_color)
        style.configure("TLabelframe.Label", foreground=self.text_color, background=self.background_color)
        
        # Configure Button styles - FIXED for better readability
        style.configure("TButton", 
                      background=self.primary_color,
                      foreground="black",
                      font=("Arial", 10, "bold"),
                      padding=5)
        
        style.map("TButton",
                background=[('active', self.secondary_color), ('pressed', self.secondary_color)],
                foreground=[('pressed', 'black'), ('active', 'black')])
        
        # Accent button style for primary actions
        style.configure("Accent.TButton", 
                       background=self.accent_color,
                       foreground="black",
                       font=("Arial", 10, "bold"),
                       padding=5)
        
        style.map("Accent.TButton",
                background=[('active', "#FF7043"), ('pressed', "#FF7043")],
                foreground=[('pressed', 'black'), ('active', 'black')])
        
        # Success button style
        style.configure("Success.TButton", 
                       background=self.success_color,
                       foreground="black",
                       font=("Arial", 10, "bold"),
                       padding=5)
        
        # Add explicit mapping for Success.TButton 
        style.map("Success.TButton",
                 background=[('active', "#66BB6A"), ('pressed', "#66BB6A")],
                 foreground=[('pressed', 'black'), ('active', 'black')])
        
        # Configure Label style
        style.configure("TLabel", background=self.background_color, foreground=self.text_color)
        
        # Configure Entry style
        style.configure("TEntry", fieldbackground="white", foreground=self.text_color)
        
        # Configure Notebook style
        style.configure("TNotebook", background=self.background_color, tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab", 
                       background=self.background_color, 
                       foreground=self.text_color,
                       padding=[10, 5],
                       font=("Arial", 10))
        
        style.map("TNotebook.Tab",
                background=[("selected", self.primary_color)],
                foreground=[("selected", "black")],
                expand=[("selected", [1, 1, 1, 0])])
        
        # Configure Treeview
        style.configure("Treeview", 
                       background="white", 
                       foreground=self.text_color, 
                       rowheight=25,
                       fieldbackground="white")
        style.configure("Treeview.Heading", 
                       font=("Arial", 10, "bold"), 
                       background=self.primary_color, 
                       foreground="black")
        style.map("Treeview",
                background=[('selected', self.secondary_color)],
                foreground=[('selected', 'black')])
        
        # Configure Combobox
        style.configure("TCombobox", 
                       background="white", 
                       foreground=self.text_color,
                       fieldbackground="white")
        
        # Make sure button text is readable
        style.map("TCombobox",
               fieldbackground=[('readonly', 'white')],
               foreground=[('readonly', self.text_color)])
    
    def initialize_database(self):
        """Initialize the SQLite database for storing time logs"""
        if not os.path.exists("data"):
            os.makedirs("data")
            
        self.conn = sqlite3.connect("data/timelog.db")
        self.cursor = self.conn.cursor()
        
        # Create time_logs table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                start_time TEXT,
                end_time TEXT,
                break_duration INTEGER,
                hourly_rate REAL,
                total_hours REAL,
                total_earnings REAL,
                notes TEXT
            )
        ''')
        
        # Create payroll_periods table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payroll_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_name TEXT,
                start_date TEXT,
                end_date TEXT,
                is_default INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.commit()
        
    def ensure_csv_exists(self):
        """Make sure the CSV file exists with correct headers"""
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                # Write header with minimal fields for compact storage
                writer.writerow(['date', 'start', 'end', 'break_min', 'rate', 'hours', 'earnings', 'notes'])
                
    def sync_to_csv(self):
        """Sync all records from the database to the CSV file"""
        try:
            # Get all records from database
            self.cursor.execute("SELECT date, start_time, end_time, break_duration, hourly_rate, total_hours, total_earnings, notes FROM time_logs ORDER BY date")
            records = self.cursor.fetchall()
            
            # Write to CSV file (overwriting existing content)
            with open(self.csv_file_path, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                # Write header
                writer.writerow(['date', 'start', 'end', 'break_min', 'rate', 'hours', 'earnings', 'notes'])
                # Write data
                for record in records:
                    writer.writerow(record)
                    
            return True
        except Exception as e:
            print(f"Error syncing to CSV: {str(e)}")
            return False
            
    def add_record_to_csv(self, record):
        """Add a single record to the CSV file"""
        try:
            with open(self.csv_file_path, 'a', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(record)
            return True
        except Exception as e:
            print(f"Error adding record to CSV: {str(e)}")
            return False
        
    def create_log_tab(self):
        """Create the tab for logging new work entries"""
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Log Time")
        
        # Main container with padding
        main_container = ttk.Frame(log_frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Create a two-column layout with equal widths
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 10))
        
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.LEFT, fill="both", expand=True, padx=(10, 0))
        
        # Date selection - Left panel
        date_frame = ttk.LabelFrame(left_panel, text="Date Selection")
        date_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Add calendar for date selection with new date format
        self.cal = Calendar(date_frame, selectmode='day', date_pattern='dd/mm/yyyy', 
                          background=self.primary_color, foreground="white",
                          headersbackground=self.secondary_color, headersforeground="white")
        self.cal.pack(padx=15, pady=15, fill="both", expand=True)
        
        # Quick date buttons
        quick_date_frame = ttk.Frame(date_frame)
        quick_date_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        today_btn = ttk.Button(quick_date_frame, text="Today", 
                              command=lambda: self.cal.selection_set(datetime.now().date()))
        today_btn.pack(side=tk.LEFT, padx=5)
        
        yesterday_btn = ttk.Button(quick_date_frame, text="Yesterday", 
                                  command=lambda: self.cal.selection_set(datetime.now().date() - timedelta(days=1)))
        yesterday_btn.pack(side=tk.LEFT, padx=5)
        
        # Time and rate entry - Right panel
        entry_frame = ttk.LabelFrame(right_panel, text="Work Details")
        entry_frame.pack(fill="both", expand=True)
        
        # Create a container with padding
        details_container = ttk.Frame(entry_frame)
        details_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Start time with improved layout
        time_section = ttk.Frame(details_container)
        time_section.pack(fill="x", pady=(0, 10))
        
        start_label = ttk.Label(time_section, text="Start Time (HH:MM):", font=("Arial", 10, "bold"))
        start_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.start_time_var = tk.StringVar()
        start_entry = ttk.Entry(time_section, textvariable=self.start_time_var, width=12)
        start_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # End time
        end_label = ttk.Label(time_section, text="End Time (HH:MM):", font=("Arial", 10, "bold"))
        end_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.end_time_var = tk.StringVar()
        end_entry = ttk.Entry(time_section, textvariable=self.end_time_var, width=12)
        end_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Break duration
        break_label = ttk.Label(time_section, text="Break Duration (minutes):", font=("Arial", 10, "bold"))
        break_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        self.break_var = tk.IntVar()
        break_entry = ttk.Entry(time_section, textvariable=self.break_var, width=12)
        break_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Set default break duration
        self.break_var.set(30)
        
        # Rate section
        rate_section = ttk.Frame(details_container)
        rate_section.pack(fill="x", pady=10)
        
        # Hourly rate
        rate_label = ttk.Label(rate_section, text="Hourly Rate ($):", font=("Arial", 10, "bold"))
        rate_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.rate_var = tk.DoubleVar()
        rate_entry = ttk.Entry(rate_section, textvariable=self.rate_var, width=12)
        rate_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Set default rate
        self.rate_var.set(12.0)
        
        # Notes
        notes_section = ttk.Frame(details_container)
        notes_section.pack(fill="x", pady=10)
        
        notes_label = ttk.Label(notes_section, text="Notes:", font=("Arial", 10, "bold"))
        notes_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.notes_var = tk.StringVar()
        notes_entry = ttk.Entry(notes_section, textvariable=self.notes_var, width=30)
        notes_entry.pack(side=tk.LEFT, padx=5, pady=5, fill="x", expand=True)
        
        # Calculated values display
        calc_frame = ttk.LabelFrame(right_panel, text="Calculated Values")
        calc_frame.pack(fill="x", pady=10)
        
        # Add a container with padding
        calc_container = ttk.Frame(calc_frame)
        calc_container.pack(fill="x", padx=15, pady=10)
        
        # Total hours with improved layout
        hours_row = ttk.Frame(calc_container)
        hours_row.pack(fill="x", pady=5)
        
        ttk.Label(hours_row, text="Total Hours:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.total_hours_var = tk.StringVar()
        ttk.Label(hours_row, textvariable=self.total_hours_var, 
                 font=("Arial", 12), foreground=self.primary_color).pack(side=tk.LEFT, padx=5)
        
        # Total earnings
        earnings_row = ttk.Frame(calc_container)
        earnings_row.pack(fill="x", pady=5)
        
        ttk.Label(earnings_row, text="Total Earnings:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.total_earnings_var = tk.StringVar()
        ttk.Label(earnings_row, textvariable=self.total_earnings_var, 
                 font=("Arial", 12), foreground=self.success_color).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(right_panel)
        button_frame.pack(fill="x", pady=15)
        
        # Use different styles for different actions
        ttk.Button(button_frame, text="Calculate", command=self.calculate_totals).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Save Entry", command=self.save_entry, style="Accent.TButton").pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset Form", command=self.reset_form).pack(side=tk.LEFT, padx=10)
        
    def create_view_tab(self):
        """Create the tab for viewing existing entries"""
        view_frame = ttk.Frame(self.notebook)
        self.notebook.add(view_frame, text="View Records")
        
        # Main container with padding
        main_container = ttk.Frame(view_frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Search and filter options with better design
        filter_frame = ttk.LabelFrame(main_container, text="Search & Filter")
        filter_frame.pack(fill="x", pady=(0, 15))
        
        # Create a container for filter controls
        filter_container = ttk.Frame(filter_frame)
        filter_container.pack(fill="x", padx=15, pady=10)
        
        # Date range selection with better layout
        date_section = ttk.Frame(filter_container)
        date_section.pack(side=tk.LEFT, padx=(0, 20))
        
        date_label = ttk.Label(date_section, text="Date Range:", font=("Arial", 10, "bold"))
        date_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        ttk.Label(date_section, text="From:").grid(row=0, column=1, padx=(10, 2), pady=5, sticky="w")
        self.from_date_var = tk.StringVar()
        from_entry = ttk.Entry(date_section, textvariable=self.from_date_var, width=12)
        from_entry.grid(row=0, column=2, padx=2, pady=5, sticky="w")
        
        ttk.Label(date_section, text="To:").grid(row=0, column=3, padx=(10, 2), pady=5, sticky="w")
        self.to_date_var = tk.StringVar()
        to_entry = ttk.Entry(date_section, textvariable=self.to_date_var, width=12)
        to_entry.grid(row=0, column=4, padx=2, pady=5, sticky="w")
        
        # Filter buttons
        button_section = ttk.Frame(filter_container)
        button_section.pack(side=tk.RIGHT, padx=10)
        
        apply_button = ttk.Button(button_section, text="Apply Filter", 
                                command=self.apply_filter, style="Accent.TButton")
        apply_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        reset_button = ttk.Button(button_section, text="Reset Filter", 
                                command=self.reset_filter)
        reset_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Stats section
        stats_frame = ttk.LabelFrame(main_container, text="Summary Statistics")
        stats_frame.pack(fill="x", pady=(0, 15))
        
        # Add a container for stats display
        stats_container = ttk.Frame(stats_frame)
        stats_container.pack(fill="x", padx=15, pady=10)
        
        # Add summary statistics for the current filter
        stats_section = ttk.Frame(stats_container)
        stats_section.pack(fill="x")
        
        # Total records
        ttk.Label(stats_section, text="Total Records:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.total_records_var = tk.StringVar(value="0")
        ttk.Label(stats_section, textvariable=self.total_records_var).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        
        # Total hours for the filter
        ttk.Label(stats_section, text="Total Hours:", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=(20, 5), pady=2, sticky="w")
        self.filter_total_hours_var = tk.StringVar(value="0.00")
        ttk.Label(stats_section, textvariable=self.filter_total_hours_var).grid(row=0, column=3, padx=5, pady=2, sticky="w")
        
        # Total earnings for the filter
        ttk.Label(stats_section, text="Total Earnings:", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=(20, 5), pady=2, sticky="w")
        self.filter_total_earnings_var = tk.StringVar(value="$0.00")
        ttk.Label(stats_section, textvariable=self.filter_total_earnings_var).grid(row=0, column=5, padx=5, pady=2, sticky="w")
        
        # Date range display
        ttk.Label(stats_section, text="Date Range:", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.date_range_var = tk.StringVar(value="All dates")
        ttk.Label(stats_section, textvariable=self.date_range_var).grid(row=1, column=1, padx=5, pady=2, sticky="w", columnspan=5)
        
        # Treeview for data display with improved design
        self.create_treeview(main_container)
        
        # Buttons for record management
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill="x", pady=10)
        
        # Create buttons with proper styling
        action_buttons = [
            ("Edit Selected", self.edit_record, "TButton"),
            ("Delete Selected", self.delete_record, "TButton"),
            ("Refresh", self.load_records, "TButton"),
            # Add an export button here for convenience
            ("Export Selected", self.export_selected, "Accent.TButton")
        ]
        
        for text, cmd, style in action_buttons:
            ttk.Button(button_frame, text=text, command=cmd, style=style).pack(side=tk.LEFT, padx=5)
        
    def export_selected(self):
        """Export selected records to CSV"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select one or more records to export")
            return
            
        # Get the file path for saving
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Selected Records"
        )
        
        if not file_path:
            return  # User cancelled
            
        try:
            # Get data for selected records
            rows = []
            for item in selected:
                values = self.tree.item(item)['values']
                rows.append(values)
                
            # Create a CSV file
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['ID', 'Date', 'Start Time', 'End Time', 'Break', 'Rate', 'Hours', 'Earnings', 'Notes'])
                # Write data
                for row in rows:
                    writer.writerow(row)
                    
            messagebox.showinfo("Export Successful", f"Exported {len(rows)} record(s) to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export records: {str(e)}")
            
    @handle_errors(show_message=True)
    def load_records(self):
        """Load records from database into the treeview"""
        # Clear existing records
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # Get records from database
        records = self.db_utils.execute_query("SELECT * FROM time_logs ORDER BY date DESC")
        
        # Insert into treeview
        for record in records:
            formatted_record = self.format_record_for_treeview(record)
            self.tree.insert("", "end", values=formatted_record)
            
        # Update summary statistics
        self.update_record_summary(records)
    
    def update_record_summary(self, records):
        """Update the summary statistics for current records"""
        if not records:
            self.total_records_var.set("0")
            self.filter_total_hours_var.set("0.00")
            self.filter_total_earnings_var.set("$0.00")
            self.date_range_var.set("No records")
            return
            
        # Update total records
        self.total_records_var.set(str(len(records)))
        
        # Calculate totals
        total_hours = sum(record[6] for record in records) if records else 0
        total_earnings = sum(record[7] for record in records) if records else 0
        
        # Set values
        self.filter_total_hours_var.set(f"{total_hours:.2f}")
        self.filter_total_earnings_var.set(f"${total_earnings:.2f}")
        
        # Determine date range from records
        try:
            dates = [record[1] for record in records]
            min_date = min(dates)
            max_date = max(dates)
            self.date_range_var.set(f"{min_date} to {max_date}")
        except (ValueError, TypeError):
            self.date_range_var.set("All dates")
    
    def create_payroll_tab(self):
        """Create a tab for managing payroll periods"""
        payroll_frame = ttk.Frame(self.notebook)
        self.notebook.add(payroll_frame, text="Payroll Periods")
        
        # Create left frame for adding new periods
        add_frame = ttk.LabelFrame(payroll_frame, text="Define Payroll Period")
        add_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Period name
        ttk.Label(add_frame, text="Period Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.period_name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.period_name_var, width=25).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Payroll period type
        ttk.Label(add_frame, text="Period Type:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.period_type_var = tk.StringVar(value="Monthly")
        period_types = ["Monthly", "Bi-weekly", "Weekly", "Yearly", "Custom"]
        ttk.Combobox(add_frame, textvariable=self.period_type_var, values=period_types, 
                    state="readonly", width=15).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Start date
        ttk.Label(add_frame, text="Start Date (dd/mm/yyyy):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.period_start_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.period_start_var, width=12).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # End date
        ttk.Label(add_frame, text="End Date (dd/mm/yyyy):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.period_end_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.period_end_var, width=12).grid(row=3, column=1, padx=5, pady=5, sticky="w")
        
        # Default period checkbox
        self.default_period_var = tk.BooleanVar()
        ttk.Checkbutton(add_frame, text="Set as default payroll period", 
                       variable=self.default_period_var).grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        # Generate recurring periods
        ttk.Label(add_frame, text="Generate Recurring Periods:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.num_periods_var = tk.IntVar(value=6)
        ttk.Spinbox(add_frame, from_=1, to=24, textvariable=self.num_periods_var, width=5).grid(row=5, column=1, padx=5, pady=5, sticky="w")
        
        # Apply period type changes
        ttk.Button(add_frame, text="Apply Selected Period Type", 
                  command=self.apply_period_type).grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        # Payroll pattern description
        pattern_frame = ttk.LabelFrame(add_frame, text="Common Patterns")
        pattern_frame.grid(row=6, column=0, columnspan=3, padx=5, pady=10, sticky="ew")
        
        def set_monthly_pattern():
            # Set pattern for 2nd of month to 1st of next month
            self.period_type_var.set("Monthly")
            self.apply_period_type()
        
        def set_biweekly_pattern():
            # Set pattern for biweekly payroll
            self.period_type_var.set("Bi-weekly")
            self.apply_period_type()
        
        def set_weekly_pattern():
            # Set pattern for weekly payroll (Monday to Sunday)
            self.period_type_var.set("Weekly")
            self.apply_period_type()
        
        def set_yearly_pattern():
            # Set pattern for yearly payroll (Jan 1 to Dec 31)
            self.period_type_var.set("Yearly")
            self.apply_period_type()
        
        # Pattern buttons
        ttk.Button(pattern_frame, text="Monthly (26th-25th)", command=set_monthly_pattern).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(pattern_frame, text="Bi-weekly", command=set_biweekly_pattern).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(pattern_frame, text="Weekly", command=set_weekly_pattern).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(pattern_frame, text="Yearly", command=set_yearly_pattern).grid(row=0, column=3, padx=5, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(add_frame)
        button_frame.grid(row=7, column=0, columnspan=3, padx=5, pady=10)
        
        ttk.Button(button_frame, text="Add Payroll Period", command=self.add_payroll_period).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Generate Recurring Periods", command=self.generate_recurring_periods).pack(side=tk.LEFT, padx=5)
        
        # Create right frame for listing existing periods
        list_frame = ttk.LabelFrame(payroll_frame, text="Existing Payroll Periods")
        list_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Create treeview for payroll periods
        columns = ("id", "period_name", "start_date", "end_date", "is_default")
        self.period_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # Configure column headings
        self.period_tree.heading("id", text="ID")
        self.period_tree.heading("period_name", text="Period Name")
        self.period_tree.heading("start_date", text="Start Date")
        self.period_tree.heading("end_date", text="End Date")
        self.period_tree.heading("is_default", text="Default")
        
        # Configure column widths
        self.period_tree.column("id", width=40)
        self.period_tree.column("period_name", width=200)
        self.period_tree.column("start_date", width=100)
        self.period_tree.column("end_date", width=100)
        self.period_tree.column("is_default", width=60)
        
        # Add scrollbar
        period_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.period_tree.yview)
        self.period_tree.configure(yscrollcommand=period_scroll.set)
        
        # Layout
        self.period_tree.pack(side=tk.LEFT, fill="both", expand=True)
        period_scroll.pack(side=tk.RIGHT, fill="y")
        
        # Period management buttons
        period_button_frame = ttk.Frame(list_frame)
        period_button_frame.pack(fill="x", pady=5)
        
        ttk.Button(period_button_frame, text="Set as Default", command=self.set_default_period).pack(side=tk.LEFT, padx=5)
        ttk.Button(period_button_frame, text="Delete Period", command=self.delete_period).pack(side=tk.LEFT, padx=5)
        ttk.Button(period_button_frame, text="Refresh", command=self.load_payroll_periods).pack(side=tk.LEFT, padx=5)
        ttk.Button(period_button_frame, text="Run Report", command=self.report_for_period).pack(side=tk.LEFT, padx=5)
        
        # Make the grid layout flexible
        payroll_frame.columnconfigure(0, weight=1)
        payroll_frame.columnconfigure(1, weight=1)
        payroll_frame.rowconfigure(0, weight=1)
        
        # Load existing payroll periods
        self.load_payroll_periods()
        
    def create_report_tab(self):
        """Create the tab for generating reports and visualizations"""
        report_frame = ttk.Frame(self.notebook)
        self.notebook.add(report_frame, text="Reports & Statistics")
        
        # Main container with padding
        main_container = ttk.Frame(report_frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Report options
        options_frame = ttk.LabelFrame(main_container, text="Report Options")
        options_frame.pack(fill="x", pady=10)
        
        # Report type selection
        report_type_frame = ttk.Frame(options_frame)
        report_type_frame.pack(fill="x", padx=15, pady=10)
        
        ttk.Label(report_type_frame, text="Report Type:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.report_type_var = tk.StringVar()
        report_types = ["Daily Summary", "Weekly Summary", "Monthly Summary", "Current Payroll Period", "Custom Range"]
        report_type_combo = ttk.Combobox(report_type_frame, textvariable=self.report_type_var, values=report_types, state="readonly", width=20)
        report_type_combo.pack(side=tk.LEFT, padx=5)
        report_type_combo.current(0)  # Set default selection
        
        # Date range for custom reports with calendar popups
        date_frame = ttk.Frame(options_frame)
        date_frame.pack(fill="x", padx=15, pady=5)
        
        # Create a better-looking date selection section
        date_section = ttk.Frame(date_frame)
        date_section.pack(fill="x", pady=5)
        
        # From date with icon button
        from_frame = ttk.Frame(date_section)
        from_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(from_frame, text="From:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.report_from_var = tk.StringVar()
        from_date_entry = ttk.Entry(from_frame, textvariable=self.report_from_var, width=12)
        from_date_entry.pack(side=tk.LEFT, padx=5)
        
        calendar_button_from = ttk.Button(from_frame, text="📅", width=3, 
                                       command=lambda: self.show_calendar_popup("report_from"))
        calendar_button_from.pack(side=tk.LEFT, padx=2)
        
        # To date with icon button
        to_frame = ttk.Frame(date_section)
        to_frame.pack(side=tk.LEFT)
        
        ttk.Label(to_frame, text="To:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.report_to_var = tk.StringVar()
        to_date_entry = ttk.Entry(to_frame, textvariable=self.report_to_var, width=12)
        to_date_entry.pack(side=tk.LEFT, padx=5)
        
        calendar_button_to = ttk.Button(to_frame, text="📅", width=3, 
                                     command=lambda: self.show_calendar_popup("report_to"))
        calendar_button_to.pack(side=tk.LEFT, padx=2)
        
        # Quick Date Range Selection
        date_range_frame = ttk.LabelFrame(options_frame, text="Quick Select")
        date_range_frame.pack(fill="x", padx=15, pady=10)
        
        # Create a more attractive button layout
        quick_select_container = ttk.Frame(date_range_frame)
        quick_select_container.pack(fill="x", padx=10, pady=5)
        
        # First row of quick select buttons - make them more attractive
        quick_select_row1 = ttk.Frame(quick_select_container)
        quick_select_row1.pack(fill="x", pady=5)
        
        # Define a list of button specs: (text, command, style)
        quick_buttons_row1 = [
            ("Today", lambda: self.set_quick_date_range("today"), "TButton"),
            ("Yesterday", lambda: self.set_quick_date_range("yesterday"), "TButton"),
            ("This Week", lambda: self.set_quick_date_range("this_week"), "TButton"),
            ("Last Week", lambda: self.set_quick_date_range("last_week"), "TButton")
        ]
        
        # Create buttons with even spacing
        for text, cmd, style in quick_buttons_row1:
            ttk.Button(quick_select_row1, text=text, command=cmd, style=style, width=12).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Second row of quick select buttons
        quick_select_row2 = ttk.Frame(quick_select_container)
        quick_select_row2.pack(fill="x", pady=5)
        
        # Define a list of button specs for second row
        quick_buttons_row2 = [
            ("This Month", lambda: self.set_quick_date_range("this_month"), "TButton"),
            ("Last Month", lambda: self.set_quick_date_range("last_month"), "TButton"),
            ("This Year", lambda: self.set_quick_date_range("this_year"), "TButton"),
            ("Last Year", lambda: self.set_quick_date_range("last_year"), "TButton"),
            ("All Data", lambda: self.set_all_data_range(), "Accent.TButton")
        ]
        
        # Create buttons with even spacing
        for text, cmd, style in quick_buttons_row2:
            ttk.Button(quick_select_row2, text=text, command=cmd, style=style, width=12).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Add rate filter section with improved layout
        rate_filter_frame = ttk.LabelFrame(options_frame, text="Filters")
        rate_filter_frame.pack(fill="x", padx=15, pady=10)
        
        # Create a container for rate filters
        rate_container = ttk.Frame(rate_filter_frame)
        rate_container.pack(fill="x", padx=10, pady=5)
        
        # Rate filter section
        rate_section = ttk.Frame(rate_container)
        rate_section.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(rate_section, text="Rate Range:").pack(side=tk.LEFT, padx=5)
        ttk.Label(rate_section, text="Min:").pack(side=tk.LEFT, padx=(15, 2))
        self.min_rate_var = tk.StringVar()
        ttk.Entry(rate_section, textvariable=self.min_rate_var, width=6).pack(side=tk.LEFT)
        
        ttk.Label(rate_section, text="Max:").pack(side=tk.LEFT, padx=(15, 2))
        self.max_rate_var = tk.StringVar()
        ttk.Entry(rate_section, textvariable=self.max_rate_var, width=6).pack(side=tk.LEFT)
        
        # Keyword filter section
        keyword_section = ttk.Frame(rate_container)
        keyword_section.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(keyword_section, text="Keyword:").pack(side=tk.LEFT, padx=5)
        self.keyword_filter_var = tk.StringVar()
        ttk.Entry(keyword_section, textvariable=self.keyword_filter_var, width=15).pack(side=tk.LEFT, padx=5)
        
        # Comparison section with improved layout
        comparison_frame = ttk.Frame(options_frame)
        comparison_frame.pack(fill="x", padx=15, pady=10)
        self.comparison_frame = comparison_frame  # Store reference to comparison_frame
        
        # Add variable for comparison checkbox
        self.compare_enabled_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(comparison_frame, text="Compare with previous period", 
                      variable=self.compare_enabled_var, command=self.toggle_comparison).pack(side=tk.LEFT, padx=5)
        
        # Generate report button - make it stand out
        generate_button = ttk.Button(options_frame, text="Generate Report", command=self.generate_report, style="Accent.TButton")
        generate_button.pack(pady=15, ipadx=10, ipady=5)
        
        # Create a horizontal container for statistics and charts
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill="both", expand=True, padx=0, pady=10)
        
        # Statistics summary - left side
        stats_frame = ttk.LabelFrame(content_frame, text="Statistics")
        stats_frame.pack(side=tk.LEFT, fill="y", padx=(0, 10), pady=0, expand=False)
        
        # Rest of the method remains the same...
        # Current Period Statistics
        current_stats = ttk.LabelFrame(stats_frame, text="Current Period")
        current_stats.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        ttk.Label(current_stats, text="Total Hours:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.stats_hours_var = tk.StringVar()
        ttk.Label(current_stats, textvariable=self.stats_hours_var).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(current_stats, text="Total Earnings:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.stats_earnings_var = tk.StringVar()
        ttk.Label(current_stats, textvariable=self.stats_earnings_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(current_stats, text="Average Daily Hours:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.stats_avg_hours_var = tk.StringVar()
        ttk.Label(current_stats, textvariable=self.stats_avg_hours_var).grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        ttk.Label(current_stats, text="Average Hourly Rate:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.stats_avg_rate_var = tk.StringVar()
        ttk.Label(current_stats, textvariable=self.stats_avg_rate_var).grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        # Add period length info
        ttk.Label(current_stats, text="Period Length:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.stats_period_length_var = tk.StringVar()
        ttk.Label(current_stats, textvariable=self.stats_period_length_var).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Add work days info
        ttk.Label(current_stats, text="Work Days:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.stats_work_days_var = tk.StringVar()
        ttk.Label(current_stats, textvariable=self.stats_work_days_var).grid(row=2, column=3, padx=5, pady=5, sticky="w")
        
        # Advanced Statistics
        advanced_stats = ttk.LabelFrame(stats_frame, text="Advanced Statistics")
        advanced_stats.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        ttk.Label(advanced_stats, text="Projected Monthly Earnings:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.stats_projected_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_projected_var).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(advanced_stats, text="Most Productive Day:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.stats_productive_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_productive_var).grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # Add average earnings per day
        ttk.Label(advanced_stats, text="Avg. Daily Earnings:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.stats_daily_earnings_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_daily_earnings_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Add hourly rate range
        ttk.Label(advanced_stats, text="Hourly Rate Range:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.stats_rate_range_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_rate_range_var).grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        # Add productive time of day analysis
        ttk.Label(advanced_stats, text="Peak Hours:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.stats_peak_hours_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_peak_hours_var).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Add least productive day
        ttk.Label(advanced_stats, text="Least Productive Day:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.stats_least_productive_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_least_productive_var).grid(row=2, column=3, padx=5, pady=5, sticky="w")
        
        # Comparison Statistics
        comparison_stats = ttk.LabelFrame(stats_frame, text="Comparison to Previous Period")
        comparison_stats.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        
        # Add variable for comparison checkbox
        self.compare_enabled_var = tk.BooleanVar(value=False)
        
        ttk.Label(comparison_stats, text="Hours Change:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.compare_hours_var = tk.StringVar()
        self.compare_hours_label = ttk.Label(comparison_stats, textvariable=self.compare_hours_var)
        self.compare_hours_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(comparison_stats, text="Earnings Change:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.compare_earnings_var = tk.StringVar()
        self.compare_earnings_label = ttk.Label(comparison_stats, textvariable=self.compare_earnings_var)
        self.compare_earnings_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # Add absolute value comparisons
        ttk.Label(comparison_stats, text="Previous Hours:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.prev_hours_var = tk.StringVar()
        ttk.Label(comparison_stats, textvariable=self.prev_hours_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(comparison_stats, text="Previous Earnings:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.prev_earnings_var = tk.StringVar()
        ttk.Label(comparison_stats, textvariable=self.prev_earnings_var).grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        # Trend visualization frame
        trend_frame = ttk.LabelFrame(stats_frame, text="Performance Trends")
        trend_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        
        # Hours trend indicators
        ttk.Label(trend_frame, text="Hours Trend:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.hours_trend_var = tk.StringVar()
        ttk.Label(trend_frame, textvariable=self.hours_trend_var).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Earnings trend indicators
        ttk.Label(trend_frame, text="Earnings Trend:").grid(row=0, column=2, padx=5, pady=5, sticky="w") 
        self.earnings_trend_var = tk.StringVar()
        ttk.Label(trend_frame, textvariable=self.earnings_trend_var).grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # Hourly rate trend
        ttk.Label(trend_frame, text="Rate Trend:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.rate_trend_var = tk.StringVar()
        ttk.Label(trend_frame, textvariable=self.rate_trend_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Productivity trend
        ttk.Label(trend_frame, text="Productivity:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.productivity_var = tk.StringVar()
        ttk.Label(trend_frame, textvariable=self.productivity_var).grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        # Make sure grid cells expand properly
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)
        
        # Frame for charts - set a minimum height to ensure charts are visible
        # Move charts to the right side with flexible width
        self.chart_frame = ttk.LabelFrame(content_frame, text="Charts")
        self.chart_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=(5, 0), pady=0)
        
        # Set a minimum width and height for the chart frame
        self.chart_frame.update()
        min_height = 350  # Minimum height in pixels
        min_width = 600   # Minimum width in pixels
        self.chart_frame.configure(height=min_height, width=min_width)
        self.chart_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Add chart type selector with improved design
        chart_controls = ttk.Frame(self.chart_frame)
        chart_controls.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(chart_controls, text="Chart Type:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.chart_type_var = tk.StringVar(value="Bar Chart")
        chart_types = ["Bar Chart", "Line Chart", "Pie Chart", "Weekly Distribution"]
        chart_type_combo = ttk.Combobox(chart_controls, textvariable=self.chart_type_var, values=chart_types, 
                                      state="readonly", width=20)
        chart_type_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(chart_controls, text="Apply", 
                  command=lambda: self.update_chart_type(), style="TButton").pack(side=tk.LEFT, padx=5)
        
        # Create a notebook for the charts
        self.chart_notebook = ttk.Notebook(self.chart_frame)
        self.chart_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create frames for each chart type
        self.bar_chart_frame = ttk.Frame(self.chart_notebook)
        self.line_chart_frame = ttk.Frame(self.chart_notebook)
        self.pie_chart_frame = ttk.Frame(self.chart_notebook)
        self.weekly_chart_frame = ttk.Frame(self.chart_notebook)
        
        # Add the frames to the notebook
        self.chart_notebook.add(self.bar_chart_frame, text="Bar")
        self.chart_notebook.add(self.line_chart_frame, text="Line")
        self.chart_notebook.add(self.pie_chart_frame, text="Pie")
        self.chart_notebook.add(self.weekly_chart_frame, text="Weekly")
        
        # Export options with improved design
        export_frame = ttk.Frame(main_container)
        export_frame.pack(fill="x", pady=15)
        
        export_label = ttk.Label(export_frame, text="Export & Reports:", font=("Arial", 10, "bold"))
        export_label.pack(side=tk.LEFT, padx=(0, 10))
        
        export_buttons = [
            ("Open CSV File", self.open_csv_file, "TButton"),
            ("Export to CSV", self.export_to_csv, "TButton"),
            ("Export to Excel", self.export_to_excel, "TButton"),
            ("Save PDF Report", self.export_to_pdf, "TButton"),
            ("Overview Report", self.show_overview_report, "Accent.TButton")
        ]
        
        for text, cmd, style in export_buttons:
            ttk.Button(export_frame, text=text, command=cmd, style=style).pack(side=tk.LEFT, padx=5)
    
    def create_treeview(self, parent):
        """Create a treeview widget for displaying time log records"""
        # Frame to contain the treeview and scrollbar
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create the treeview
        columns = ("id", "date", "start_time", "end_time", "break_duration", 
                    "hourly_rate", "total_hours", "total_earnings", "notes")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        # Configure column headings
        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Date")
        self.tree.heading("start_time", text="Start Time")
        self.tree.heading("end_time", text="End Time")
        self.tree.heading("break_duration", text="Break (min)")
        self.tree.heading("hourly_rate", text="Rate ($/hr)")
        self.tree.heading("total_hours", text="Hours")
        self.tree.heading("total_earnings", text="Earnings ($)")
        self.tree.heading("notes", text="Notes")
        
        # Configure column widths
        self.tree.column("id", width=40)
        self.tree.column("date", width=100)
        self.tree.column("start_time", width=80)
        self.tree.column("end_time", width=80)
        self.tree.column("break_duration", width=80)
        self.tree.column("hourly_rate", width=80)
        self.tree.column("total_hours", width=80)
        self.tree.column("total_earnings", width=100)
        self.tree.column("notes", width=200)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for treeview and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Load initial data
        self.load_records()
        
    def calculate_totals(self):
        """Calculate total hours and earnings based on user input"""
        try:
            # Get start and end times
            start_time = self.start_time_var.get()
            end_time = self.end_time_var.get()
            
            # Parse times
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")
            
            # Handle overnight shifts
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            # Calculate duration in hours
            duration = (end_dt - start_dt).total_seconds() / 3600
            
            # Subtract break duration
            break_duration = self.break_var.get() / 60  # Convert minutes to hours
            total_hours = duration - break_duration
            
            # Calculate earnings
            hourly_rate = self.rate_var.get()
            total_earnings = total_hours * hourly_rate
            
            # Update display
            self.total_hours_var.set(f"{total_hours:.2f}")
            self.total_earnings_var.set(f"${total_earnings:.2f}")
            
        except ValueError as e:
            messagebox.showerror("Input Error", f"Please enter valid times and numbers: {str(e)}")
    
    @handle_errors(show_message=True)
    def save_entry(self):
        """Save the current entry to the database and CSV"""
        # Calculate totals if not already done
        if not self.total_hours_var.get():
            self.calculate_totals()
            
        # Get all values
        date = self.cal.get_date()
        start_time = self.start_time_var.get()
        end_time = self.end_time_var.get()
        break_duration = self.break_var.get()
        hourly_rate = self.rate_var.get()
        total_hours = float(self.total_hours_var.get())
        total_earnings = float(self.total_earnings_var.get().replace('$', ''))
        notes = self.notes_var.get()
        
        # Convert date to DB_DATE_FORMAT for database storage
        db_date = DateUtils.format_date_for_db(date)
        
        # Create data dictionary for database insertion
        data = {
            'date': db_date,
            'start_time': start_time,
            'end_time': end_time,
            'break_duration': break_duration,
            'hourly_rate': hourly_rate,
            'total_hours': total_hours,
            'total_earnings': total_earnings,
            'notes': notes
        }
        
        # Insert into database using the utility
        if self.db_utils.insert_record('time_logs', data):
            # Add to CSV file
            csv_record = [db_date, start_time, end_time, break_duration, hourly_rate, total_hours, total_earnings, notes]
            self.add_record_to_csv(csv_record)
            
            messagebox.showinfo("Success", "Work record saved successfully!")
            self.reset_form()
            self.load_records()
            
            # Update date range
            self.update_date_range()
        else:
            messagebox.showerror("Error", "Failed to save entry to database")
    
    def reset_form(self):
        """Reset all form fields"""
        self.start_time_var.set("")
        self.end_time_var.set("")
        self.break_var.set(0)
        self.rate_var.set(0.0)
        self.notes_var.set("")
        self.total_hours_var.set("")
        self.total_earnings_var.set("")
    
    @handle_errors(show_message=True)
    def apply_filter(self):
        """Apply date filter to records"""
        # Clear existing records
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # Get filter dates
        from_date = self.from_date_var.get()
        to_date = self.to_date_var.get()
        
        # Convert dates for database query
        if from_date:
            db_from_date = self.convert_to_db_date_format(from_date)
        else:
            db_from_date = None
            
        if to_date:
            db_to_date = self.convert_to_db_date_format(to_date)
        else:
            db_to_date = None
        
        # Build query with support for both date formats
        query = "SELECT * FROM time_logs WHERE 1=1"
        params = []
        
        if from_date and to_date:
            # Handle both date formats with an OR condition
            query += " AND ((date BETWEEN ? AND ?) OR (date BETWEEN ? AND ?))"
            params.extend([from_date, to_date, db_from_date, db_to_date])
        elif from_date:
            # Just from_date - handle both formats
            query += " AND (date >= ? OR date >= ?)"
            params.extend([from_date, db_from_date])
        elif to_date:
            # Just to_date - handle both formats
            query += " AND (date <= ? OR date <= ?)"
            params.extend([to_date, db_to_date])
            
        query += " ORDER BY date DESC"
        
        # Execute query
        self.cursor.execute(query, params)
        records = self.cursor.fetchall()
        
        # Insert into treeview
        for record in records:
            formatted_record = self.format_record_for_treeview(record)
            self.tree.insert("", "end", values=formatted_record)
            
        # Update summary statistics
        self.update_record_summary(records)
        
        # Update date range display
        if from_date and to_date:
            self.date_range_var.set(f"{from_date} to {to_date}")
        elif from_date:
            self.date_range_var.set(f"From {from_date} onwards")
        elif to_date:
            self.date_range_var.set(f"Until {to_date}")
        else:
            self.date_range_var.set("All dates")
    
    def reset_filter(self):
        """Reset date filters and reload all records"""
        self.from_date_var.set("")
        self.to_date_var.set("")
        self.load_records()
    
    def edit_record(self):
        """Edit the selected record"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a record to edit")
            return
            
        # Get the selected record
        record_id = self.tree.item(selected[0])['values'][0]
        
        # Create edit window
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Work Record")
        edit_window.geometry("400x400")
        
        # Get record data
        self.cursor.execute("SELECT * FROM time_logs WHERE id = ?", (record_id,))
        record = self.cursor.fetchone()
        
        # Convert date format for display if needed
        try:
            if record[1] and '-' in record[1]:
                date_obj = datetime.strptime(record[1], DB_DATE_FORMAT).date()
                display_date = date_obj.strftime(DATE_FORMAT)
            else:
                display_date = record[1]
        except ValueError:
            display_date = record[1]
        
        # Create edit form
        edit_frame = ttk.Frame(edit_window, padding=10)
        edit_frame.pack(fill="both", expand=True)
        
        # Date
        ttk.Label(edit_frame, text="Date (dd/mm/yyyy):").grid(row=0, column=0, sticky="w", pady=5)
        date_var = tk.StringVar(value=display_date)
        ttk.Entry(edit_frame, textvariable=date_var).grid(row=0, column=1, sticky="ew", pady=5)
        
        # Start time
        ttk.Label(edit_frame, text="Start Time (HH:MM):").grid(row=1, column=0, sticky="w", pady=5)
        start_var = tk.StringVar(value=record[2])
        ttk.Entry(edit_frame, textvariable=start_var).grid(row=1, column=1, sticky="ew", pady=5)
        
        # End time
        ttk.Label(edit_frame, text="End Time (HH:MM):").grid(row=2, column=0, sticky="w", pady=5)
        end_var = tk.StringVar(value=record[3])
        ttk.Entry(edit_frame, textvariable=end_var).grid(row=2, column=1, sticky="ew", pady=5)
        
        # Break duration
        ttk.Label(edit_frame, text="Break Duration (min):").grid(row=3, column=0, sticky="w", pady=5)
        break_var = tk.IntVar(value=record[4])
        ttk.Entry(edit_frame, textvariable=break_var).grid(row=3, column=1, sticky="ew", pady=5)
        
        # Hourly rate
        ttk.Label(edit_frame, text="Hourly Rate ($):").grid(row=4, column=0, sticky="w", pady=5)
        rate_var = tk.DoubleVar(value=record[5])
        ttk.Entry(edit_frame, textvariable=rate_var).grid(row=4, column=1, sticky="ew", pady=5)
        
        # Total hours
        ttk.Label(edit_frame, text="Total Hours:").grid(row=5, column=0, sticky="w", pady=5)
        hours_var = tk.DoubleVar(value=record[6])
        ttk.Entry(edit_frame, textvariable=hours_var).grid(row=5, column=1, sticky="ew", pady=5)
        
        # Total earnings
        ttk.Label(edit_frame, text="Total Earnings ($):").grid(row=6, column=0, sticky="w", pady=5)
        earnings_var = tk.DoubleVar(value=record[7])
        ttk.Entry(edit_frame, textvariable=earnings_var).grid(row=6, column=1, sticky="ew", pady=5)
        
        # Notes
        ttk.Label(edit_frame, text="Notes:").grid(row=7, column=0, sticky="w", pady=5)
        notes_var = tk.StringVar(value=record[8] if record[8] else "")
        ttk.Entry(edit_frame, textvariable=notes_var).grid(row=7, column=1, sticky="ew", pady=5)
        
        # Save button
        def save_changes():
            try:
                self.cursor.execute('''
                    UPDATE time_logs
                    SET date=?, start_time=?, end_time=?, break_duration=?,
                        hourly_rate=?, total_hours=?, total_earnings=?, notes=?
                    WHERE id=?
                ''', (
                    date_var.get(), start_var.get(), end_var.get(), break_var.get(),
                    rate_var.get(), hours_var.get(), earnings_var.get(), notes_var.get(),
                    record_id
                ))
                self.conn.commit()
                
                # Update CSV file after database update
                self.sync_to_csv()
                
                messagebox.showinfo("Success", "Record updated successfully!")
                edit_window.destroy()
                self.load_records()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update record: {str(e)}")
        
        # Add recalculate function
        def recalculate():
            try:
                # Parse times
                start_dt = datetime.strptime(start_var.get(), "%H:%M")
                end_dt = datetime.strptime(end_var.get(), "%H:%M")
                
                # Handle overnight shifts
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                
                # Calculate duration in hours
                duration = (end_dt - start_dt).total_seconds() / 3600
                
                # Subtract break duration
                break_duration = break_var.get() / 60  # Convert minutes to hours
                total_hours = duration - break_duration
                
                # Calculate earnings
                hourly_rate = rate_var.get()
                total_earnings = total_hours * hourly_rate
                
                # Update variables
                hours_var.set(round(total_hours, 2))
                earnings_var.set(round(total_earnings, 2))
                
            except ValueError as e:
                messagebox.showerror("Input Error", f"Please enter valid times and numbers: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(edit_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Recalculate", command=recalculate).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.LEFT, padx=5)
        
    @handle_errors(show_message=True)
    def delete_record(self):
        """Delete the selected record"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a record to delete")
            return
            
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            # Get the selected record ID
            record_id = self.tree.item(selected[0])['values'][0]
            
            # Delete using the utility
            condition = ("id = ?", (record_id,))
            if self.db_utils.delete_record('time_logs', condition):
                # Update CSV file after deletion
                self.sync_to_csv()
                messagebox.showinfo("Success", "Record deleted successfully!")
                self.load_records()
            else:
                messagebox.showerror("Error", "Failed to delete record")
    
    def generate_report(self):
        """Generate a report based on the selected options"""
        report_type = self.report_type_var.get()
        
        # Determine date range based on report type
        today = datetime.now().date()
        if report_type == "Daily Summary":
            from_date = today.strftime(DATE_FORMAT)
            to_date = today.strftime(DATE_FORMAT)
        elif report_type == "Weekly Summary":
            # Start of the week (Monday)
            monday = today - timedelta(days=today.weekday())
            from_date = monday.strftime(DATE_FORMAT)
            to_date = (monday + timedelta(days=6)).strftime(DATE_FORMAT)
        elif report_type == "Monthly Summary":
            # Start of the month
            from_date = today.replace(day=1).strftime(DATE_FORMAT)
            # Last day of the month
            if today.month == 12:
                to_date = today.replace(day=31).strftime(DATE_FORMAT)
            else:
                to_date = (today.replace(month=today.month+1, day=1) - timedelta(days=1)).strftime(DATE_FORMAT)
        elif report_type == "Current Payroll Period":
            # Get the default payroll period
            self.cursor.execute("SELECT start_date, end_date FROM payroll_periods WHERE is_default = 1")
            payroll_period = self.cursor.fetchone()
            
            if not payroll_period:
                messagebox.showwarning("No Default Payroll Period", 
                                    "Please set a default payroll period in the Payroll Periods tab")
                return
                
            from_date = payroll_period[0]
            to_date = payroll_period[1]
            
            # Update the date fields for visual feedback
            self.report_from_var.set(from_date)
            self.report_to_var.set(to_date)
        else:  # Custom Range
            from_date = self.report_from_var.get()
            to_date = self.report_to_var.get()
            
            if not from_date or not to_date:
                messagebox.showwarning("Missing Dates", "Please enter both From and To dates for custom range")
                return
        
        try:
            # For debugging - print dates before conversion
            print(f"Original dates - From: {from_date}, To: {to_date}")
            
            # Ensure date format is correct before conversion to DB format
            # This is important especially for "Last Year" filter
            if '/' in from_date:
                try:
                    # First validate that the date string can be parsed
                    from_date_obj = datetime.strptime(from_date, DATE_FORMAT).date()
                    to_date_obj = datetime.strptime(to_date, DATE_FORMAT).date()
                    
                    # Force re-formatting to ensure consistent format
                    from_date = from_date_obj.strftime(DATE_FORMAT)
                    to_date = to_date_obj.strftime(DATE_FORMAT)
                except ValueError:
                    print(f"Date parsing error with {from_date} or {to_date}")
                    # Keep as is if parsing fails
            
            # Convert dates to database format for querying
            db_from_date = self.convert_to_db_date_format(from_date)
            db_to_date = self.convert_to_db_date_format(to_date)
                
            # For debugging - print converted dates
            print(f"Database dates - From: {db_from_date}, To: {db_to_date}")
            
            # Build a more flexible query that can handle both date formats
            query = """
                SELECT date, start_time, end_time, break_duration, hourly_rate, total_hours, total_earnings, notes
                FROM time_logs 
                WHERE (
                    (date BETWEEN ? AND ?) OR
                    (date BETWEEN ? AND ?)
                )
            """
            
            # For the first condition, use DD/MM/YYYY format
            display_from = from_date
            display_to = to_date
            
            # For the second condition, use YYYY-MM-DD format
            db_format_from = db_from_date
            db_format_to = db_to_date
            
            # Add rate filter if specified
            min_rate = self.min_rate_var.get().strip()
            max_rate = self.max_rate_var.get().strip()
            keyword_filter = self.keyword_filter_var.get().strip()
            
            params = [display_from, display_to, db_format_from, db_format_to]
            
            if min_rate:
                try:
                    float_min_rate = float(min_rate)
                    query += " AND hourly_rate >= ?"
                    params.append(float_min_rate)
                except ValueError:
                    pass
                    
            if max_rate:
                try:
                    float_max_rate = float(max_rate)
                    query += " AND hourly_rate <= ?"
                    params.append(float_max_rate)
                except ValueError:
                    pass
            
            # Add keyword filter if specified
            if keyword_filter:
                query += " AND notes LIKE ?"
                params.append(f"%{keyword_filter}%")
                
            query += " ORDER BY date"
            print(f"Query: {query}")
            print(f"Parameters: {params}")
            
            self.cursor.execute(query, params)
            all_records = self.cursor.fetchall()
            
            # If no records, try to get any records to check if there's data in the database
            if not all_records:
                self.cursor.execute("SELECT COUNT(*) FROM time_logs")
                count = self.cursor.fetchone()[0]
                if count > 0:
                    print(f"No records found for date range, but database has {count} total records")
                    # Check all date entries to see their format
                    self.cursor.execute("SELECT DISTINCT date FROM time_logs ORDER BY date")
                    all_dates = self.cursor.fetchall()
                    print(f"Available dates in database: {all_dates}")
                    
                    # Show a more informative message to the user with suggestion
                    date_list = ", ".join([d[0] for d in all_dates])
                    messagebox.showinfo("No Data For Selected Period", 
                                       f"No records found for the period {from_date} to {to_date}.\n\n"
                                       f"The database contains {count} records with dates: {date_list}\n\n"
                                       f"Try selecting 'All Data' from the Quick Select menu to view all records.")
                    return
                else:
                    print("No records found in database")
                    messagebox.showinfo("No Data", "No records found in the database")
                    return
            
            # Extract additional data for the new statistics
            start_times = []
            end_times = []
            rates = []
            dates = set()
            
            # If we have detailed records, extract information from them
            if all_records:
                for record in all_records:
                    if record[1] and record[2]:  # If start_time and end_time exist
                        start_times.append(record[1])
                        end_times.append(record[2])
                    if record[4]:  # If hourly_rate exists
                        rates.append(record[4])
                    if record[0]:  # If date exists
                        dates.add(record[0])
                
                print(f"Found {len(all_records)} records for the date range")
            
            # Prepare summary query with the same flexible date handling
            summary_query = """
                SELECT date, SUM(total_hours) as hours, SUM(total_earnings) as earnings, AVG(hourly_rate) as avg_rate
                FROM time_logs 
                WHERE (
                    (date BETWEEN ? AND ?) OR
                    (date BETWEEN ? AND ?)
                )
            """
            
            summary_params = [display_from, display_to, db_format_from, db_format_to]
            
            # Apply the same filters
            if min_rate:
                try:
                    float_min_rate = float(min_rate)
                    summary_query += " AND hourly_rate >= ?"
                    summary_params.append(float_min_rate)
                except ValueError:
                    pass
                    
            if max_rate:
                try:
                    float_max_rate = float(max_rate)
                    summary_query += " AND hourly_rate <= ?"
                    summary_params.append(float_max_rate)
                except ValueError:
                    pass
                
            # Add keyword filter if specified
            if keyword_filter:
                summary_query += " AND notes LIKE ?"
                summary_params.append(f"%{keyword_filter}%")
                
            summary_query += " GROUP BY date ORDER BY date"
            
            self.cursor.execute(summary_query, summary_params)
            data = self.cursor.fetchall()
            
            if not data:
                # If no data, try a fallback query to get all records from any date
                print("No aggregated data found. Using fallback query for all records.")
                self.cursor.execute("""
                    SELECT date, SUM(total_hours) as hours, SUM(total_earnings) as earnings, AVG(hourly_rate) as avg_rate
                    FROM time_logs 
                    GROUP BY date
                    ORDER BY date
                """)
                data = self.cursor.fetchall()
                
                if not data:
                    # Get a list of all dates in the database for debugging
                    self.cursor.execute("SELECT DISTINCT date FROM time_logs")
                    dates = self.cursor.fetchall()
                    dates_str = ', '.join([str(d[0]) for d in dates])
                    print(f"Available dates in DB: {dates_str}")
                    messagebox.showinfo("No Data", f"No records found. Available dates: {dates_str}")
                    return
            
            # Calculate summary statistics
            total_hours = sum(row[1] for row in data)
            total_earnings = sum(row[2] for row in data)
            avg_daily_hours = total_hours / len(data) if len(data) > 0 else 0
            avg_rate = sum(row[3] for row in data) / len(data) if len(data) > 0 else 0
            
            # Calculate period length
            from_date_obj = self.convert_date_string_to_date(from_date)
            to_date_obj = self.convert_date_string_to_date(to_date)
            period_days = (to_date_obj - from_date_obj).days + 1  # +1 to include both start and end days
            
            # Calculate work days (days with logged hours)
            work_days = len(dates)
            
            # Calculate average daily earnings (on days worked)
            avg_daily_earnings = total_earnings / work_days if work_days > 0 else 0
            
            # Find most productive day
            most_productive_idx = max(range(len(data)), key=lambda i: data[i][1]) if data else 0
            most_productive_date = data[most_productive_idx][0] if data else "N/A"
            most_productive_hours = data[most_productive_idx][1] if data else 0
            
            # Find least productive day
            least_productive_idx = min(range(len(data)), key=lambda i: data[i][1]) if data else 0
            least_productive_date = data[least_productive_idx][0] if data else "N/A"
            least_productive_hours = data[least_productive_idx][1] if data else 0
            
            # Calculate hourly rate range
            if rates:
                min_rate = min(rates)
                max_rate = max(rates)
                rate_range = f"${min_rate:.2f} - ${max_rate:.2f}"
            else:
                rate_range = "N/A"
            
            # Determine peak working hours
            if start_times and end_times:
                # Convert to hours for easier analysis
                start_hours = [int(time.split(':')[0]) if ':' in time else 0 for time in start_times]
                end_hours = [int(time.split(':')[0]) if ':' in time else 0 for time in end_times]
                
                if start_hours and end_hours:
                    avg_start = sum(start_hours) / len(start_hours)
                    avg_end = sum(end_hours) / len(end_hours)
                    peak_hours = f"{int(avg_start):02d}:00 - {int(avg_end):02d}:00"
                else:
                    peak_hours = "N/A"
            else:
                peak_hours = "N/A"
            
            # Convert productive date to display format if needed
            if most_productive_date and most_productive_date != "N/A" and '-' in most_productive_date:
                try:
                    date_obj = datetime.strptime(most_productive_date, DB_DATE_FORMAT).date()
                    most_productive_date = date_obj.strftime(DATE_FORMAT)
                except ValueError:
                    pass
                    
            # Convert least productive date to display format if needed
            if least_productive_date and least_productive_date != "N/A" and '-' in least_productive_date:
                try:
                    date_obj = datetime.strptime(least_productive_date, DB_DATE_FORMAT).date()
                    least_productive_date = date_obj.strftime(DATE_FORMAT)
                except ValueError:
                    pass
            
            # Calculate projected monthly earnings based on current rate and hours
            try:
                # Calculate daily average earnings
                daily_avg_earnings = total_earnings / period_days if period_days > 0 else 0
                
                # Project for a 30-day month
                projected_monthly = daily_avg_earnings * 30
            except (ValueError, ZeroDivisionError):
                projected_monthly = 0
            
            # Update statistics display
            self.stats_hours_var.set(f"{total_hours:.2f}")
            self.stats_earnings_var.set(f"${total_earnings:.2f}")
            self.stats_avg_hours_var.set(f"{avg_daily_hours:.2f}")
            self.stats_avg_rate_var.set(f"${avg_rate:.2f}")
            self.stats_projected_var.set(f"${projected_monthly:.2f}")
            self.stats_productive_var.set(f"{most_productive_date} ({most_productive_hours:.2f} hrs)")
            
            # Update new statistics fields
            self.stats_period_length_var.set(f"{period_days} days")
            self.stats_work_days_var.set(f"{work_days} days")
            self.stats_daily_earnings_var.set(f"${avg_daily_earnings:.2f}")
            self.stats_rate_range_var.set(rate_range)
            self.stats_peak_hours_var.set(peak_hours)
            self.stats_least_productive_var.set(f"{least_productive_date} ({least_productive_hours:.2f} hrs)")
            
            # Calculate trend indicators
            if len(data) >= 2:
                # Sort data by date for trend analysis
                sorted_data = sorted(data, key=lambda x: x[0])
                
                # Calculate overall trends using linear regression
                x = list(range(len(sorted_data)))
                y_hours = [row[1] for row in sorted_data]
                y_earnings = [row[2] for row in sorted_data]
                
                # Simple trend calculation (positive slope = increasing, negative = decreasing)
                hours_trend = self.calculate_trend(x, y_hours)
                earnings_trend = self.calculate_trend(x, y_earnings)
                
                # Calculate rate trend
                rates_by_date = [row[3] for row in sorted_data]
                rate_trend = self.calculate_trend(x, rates_by_date)
                
                # Calculate productivity trend (hours per day trend)
                productivity_trend = hours_trend  # Simplified for now
                
                # Set trend indicators with emojis and colors
                self.hours_trend_var.set(self.get_trend_indicator(hours_trend))
                self.earnings_trend_var.set(self.get_trend_indicator(earnings_trend))
                self.rate_trend_var.set(self.get_trend_indicator(rate_trend))
                self.productivity_var.set(self.get_trend_indicator(productivity_trend))
            else:
                # Not enough data for trend analysis
                self.hours_trend_var.set("Insufficient data")
                self.earnings_trend_var.set("Insufficient data")
                self.rate_trend_var.set("Insufficient data")
                self.productivity_var.set("Insufficient data")
            
            # Generate comparison with previous period if enabled
            self.generate_period_comparison(db_from_date, db_to_date)
            
            # Generate charts
            self.generate_charts(data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Report Error", f"Error generating report: {str(e)}")
    
    def calculate_trend(self, x, y):
        """Calculate the trend direction using linear regression"""
        if len(x) != len(y) or len(x) < 2:
            return 0
        
        try:
            n = len(x)
            mean_x = sum(x) / n
            mean_y = sum(y) / n
            
            # Calculate slope using least squares method
            numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
            denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
            
            if denominator == 0:
                return 0
                
            slope = numerator / denominator
            return slope
        except Exception:
            return 0
    
    def get_trend_indicator(self, trend_value):
        """Convert a trend value to a visual indicator"""
        if abs(trend_value) < 0.01:  # Nearly flat
            return "→ Stable"
        elif trend_value > 0.05:  # Strong positive
            return "↑↑ Strong Increase"
        elif trend_value > 0:  # Mild positive
            return "↑ Increasing"
        elif trend_value < -0.05:  # Strong negative
            return "↓↓ Strong Decrease"
        else:  # Mild negative
            return "↓ Decreasing"
    
    def generate_period_comparison(self, from_date, to_date):
        """Generate comparison statistics with previous period"""
        try:
            # Parse dates, handle both formats
            try:
                from_date_obj = self.convert_date_string_to_date(from_date)
                to_date_obj = self.convert_date_string_to_date(to_date)
            except ValueError as e:
                print(f"Date parsing error: {e}")
                return  # Exit if dates can't be parsed
            
            # Calculate period duration in days
            period_days = (to_date_obj - from_date_obj).days + 1
            
            # Calculate previous period date range (same length)
            prev_to_date_obj = from_date_obj - timedelta(days=1)
            prev_from_date_obj = from_date_obj - timedelta(days=period_days)
            
            # Convert to database format for queries
            prev_to_date = prev_to_date_obj.strftime(DB_DATE_FORMAT)
            prev_from_date = prev_from_date_obj.strftime(DB_DATE_FORMAT)
            
            # Get data for previous period
            query = '''
                SELECT SUM(total_hours) as hours, SUM(total_earnings) as earnings
                FROM time_logs 
                WHERE date BETWEEN ? AND ?
            '''
            self.cursor.execute(query, (prev_from_date, prev_to_date))
            prev_data = self.cursor.fetchone()
            
            if prev_data and prev_data[0] is not None:
                prev_hours = prev_data[0]
                prev_earnings = prev_data[1]
                
                # Set absolute values for display
                self.prev_hours_var.set(f"{prev_hours:.2f}")
                self.prev_earnings_var.set(f"${prev_earnings:.2f}")
                
                # Get current period totals
                current_from_date = from_date_obj.strftime(DB_DATE_FORMAT)
                current_to_date = to_date_obj.strftime(DB_DATE_FORMAT)
                self.cursor.execute(query, (current_from_date, current_to_date))
                curr_data = self.cursor.fetchone()
                curr_hours = curr_data[0] if curr_data and curr_data[0] else 0
                curr_earnings = curr_data[1] if curr_data and curr_data[1] else 0
                
                # Calculate changes
                hours_change = ((curr_hours - prev_hours) / prev_hours * 100) if prev_hours else 0
                earnings_change = ((curr_earnings - prev_earnings) / prev_earnings * 100) if prev_earnings else 0
                
                # Format with up/down indicators
                hours_prefix = "▲" if hours_change >= 0 else "▼"
                earnings_prefix = "▲" if earnings_change >= 0 else "▼"
                
                # Update comparison display
                self.compare_hours_var.set(f"{hours_prefix} {abs(hours_change):.1f}%")
                self.compare_earnings_var.set(f"{earnings_prefix} {abs(earnings_change):.1f}%")
                
                # Set text color based on trend (green for positive, red for negative)
                hours_color = "green" if hours_change >= 0 else "red"
                earnings_color = "green" if earnings_change >= 0 else "red"
                
                self.compare_hours_label.configure(foreground=hours_color)
                self.compare_earnings_label.configure(foreground=earnings_color)
            else:
                self.compare_hours_var.set("No previous data")
                self.compare_earnings_var.set("No previous data")
                self.prev_hours_var.set("--")
                self.prev_earnings_var.set("--")
        except Exception as e:
            print(f"Error generating comparison: {str(e)}")
            self.compare_hours_var.set("--")
            self.compare_earnings_var.set("--")
            self.prev_hours_var.set("--")
            self.prev_earnings_var.set("--")
    
    def generate_charts(self, data):
        """Generate charts based on the report data"""
        # Clear previous charts from all frames
        for frame in [self.bar_chart_frame, self.line_chart_frame, self.pie_chart_frame, self.weekly_chart_frame]:
            for widget in frame.winfo_children():
                widget.destroy()
                
        # Convert data to DataFrame
        df = pd.DataFrame(data, columns=['date', 'hours', 'earnings', 'avg_rate'])
        
        # Close all existing figures to prevent memory leaks
        plt.close('all')
        
        # Generate all chart types
        self._generate_bar_charts(df)
        self._generate_line_charts(df)
        self._generate_pie_charts(df)
        self._generate_weekly_charts(df)
        
        # Show appropriate tab based on the selected chart type
        chart_type = self.chart_type_var.get()
        chart_tab_mapping = {
            "Bar Chart": 0,
            "Line Chart": 1,
            "Pie Chart": 2,
            "Weekly Distribution": 3
        }
        self.chart_notebook.select(chart_tab_mapping.get(chart_type, 0))
    
    def update_chart_type(self):
        """Update the chart display based on the selected chart type"""
        chart_type = self.chart_type_var.get()
        if chart_type == "Bar Chart":
            self.chart_notebook.select(0)  # Bar chart tab
        elif chart_type == "Line Chart":
            self.chart_notebook.select(1)  # Line chart tab
        elif chart_type == "Pie Chart":
            self.chart_notebook.select(2)  # Pie chart tab
        elif chart_type == "Weekly Distribution":
            self.chart_notebook.select(3)  # Weekly distribution tab
    
    @handle_errors(show_message=False)
    def _generate_bar_charts(self, df):
        """Generate bar charts for hours and earnings"""
        # Create figure with subplots - adjust size for right-side panel layout
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 10), dpi=100)
        
        # Set larger font sizes for better readability
        plt.rcParams.update({'font.size': 10})  # Reduced font size for better fit
        
        # Plot hours by date with enhanced appearance
        bars = ax1.bar(df['date'], df['hours'], color='skyblue', width=0.7)
        ax1.set_title('Hours Worked by Date', fontweight='bold', fontsize=14)
        ax1.set_ylabel('Hours', fontweight='bold', fontsize=12)
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # Ensure y-axis starts from 0 and has enough headroom
        max_hours = max(df['hours']) if not df['hours'].empty else 0
        ax1.set_ylim(0, max_hours * 1.2)  # Add 20% headroom
        
        # Add data labels
        for bar in bars:
            height = bar.get_height()
            ax1.annotate(f'{height:.1f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=9)  # Smaller font size for labels
        
        # Plot earnings by date with enhanced appearance
        bars = ax2.bar(df['date'], df['earnings'], color='lightgreen', width=0.7)
        ax2.set_title('Earnings by Date', fontweight='bold', fontsize=14)
        ax2.set_ylabel('Earnings ($)', fontweight='bold', fontsize=12)
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        # Ensure y-axis starts from 0 and has enough headroom
        max_earnings = max(df['earnings']) if not df['earnings'].empty else 0
        ax2.set_ylim(0, max_earnings * 1.2)  # Add 20% headroom
        
        # Add data labels
        for bar in bars:
            height = bar.get_height()
            ax2.annotate(f'${height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=8)  # Smaller font size for earnings labels
        
        # Improve spacing for better label fit
        plt.subplots_adjust(hspace=0.4, bottom=0.25, top=0.95, left=0.1, right=0.95)
        
        # Adjust x-axis labels for better readability
        if len(df) > 5:
            # For many dates, use every other tick or a subset
            for ax in [ax1, ax2]:
                # Get current tick positions and labels
                locs, labels = plt.xticks()
                # Show fewer ticks if there are too many
                step = max(1, len(df) // 5)  # Show about 5 labels
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
                # Make more horizontal space
                ax.set_xticklabels(labels, fontsize=8)
        
        # Format ticks with smaller font
        for ax in [ax1, ax2]:
            ax.tick_params(axis='x', labelsize=8)
            ax.tick_params(axis='y', labelsize=9)
        
        # Make chart interactive
        def on_bar_click(event):
            if event.inaxes in [ax1, ax2]:
                # Find which bar was clicked
                bars_to_check = ax1.patches if event.inaxes == ax1 else ax2.patches
                for i, bar in enumerate(bars_to_check):
                    if bar.contains(event)[0]:
                        # Show details for this day
                        date = df['date'].iloc[i]
                        self.show_day_details(date)
                        break
        
        # Connect the event
        fig.canvas.mpl_connect('button_press_event', on_bar_click)
        
        # Create the canvas using the helper method
        canvas = self.create_chart_canvas(self.bar_chart_frame, fig)
        
        return canvas
    
    def prepare_chart_data(self, df, sort_by_date=True):
        """Prepare data for chart generation
        
        Args:
            df (DataFrame): DataFrame with chart data
            sort_by_date (bool): Whether to sort by date
            
        Returns:
            DataFrame: Processed DataFrame ready for charting
        """
        if df.empty:
            return df
            
        try:
            if sort_by_date:
                # Convert date strings to datetime objects for proper sorting
                date_objects = []
                for date_str in df['date']:
                    date_objects.append(DateUtils.string_to_date(date_str))
                
                df['date_obj'] = date_objects
                df = df.sort_values(by='date_obj')
            
            return df
        except Exception as e:
            print(f"Error preparing chart data: {str(e)}")
            return df
    
    def _generate_line_charts(self, df):
        """Generate line charts for hours and earnings over time"""
        try:
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 10), dpi=100)
            
            # Set style for line charts
            plt.rcParams.update({'font.size': 10})  # Reduced font size for better fit
            
            # Sort by date for proper line progression
            if not df.empty:
                try:
                    # Convert date strings to datetime objects for proper sorting
                    # Handle both date formats (DB and display)
                    date_objects = []
                    for date_str in df['date']:
                        try:
                            if '-' in date_str:  # YYYY-MM-DD format
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            else:  # DD/MM/YYYY format
                                date_obj = datetime.strptime(date_str, DATE_FORMAT).date()
                            date_objects.append(date_obj)
                        except ValueError:
                            # If conversion fails, use the original string
                            date_objects.append(date_str)
                    
                    df['date_obj'] = date_objects
                    df = df.sort_values(by='date_obj')
                    
                    # Plot hours trend
                    ax1.plot(df['date'], df['hours'], marker='o', linestyle='-', color='royalblue', 
                            linewidth=2, markersize=8)
                    ax1.set_title('Hours Trend Over Time', fontweight='bold', fontsize=14)
                    ax1.set_ylabel('Hours', fontweight='bold', fontsize=12)
                    ax1.tick_params(axis='x', rotation=45)
                    ax1.grid(True, linestyle='--', alpha=0.7)
                    
                    # Add data labels for hours
                    for i, (x, y) in enumerate(zip(df['date'], df['hours'])):
                        ax1.annotate(f'{y:.1f}',
                                    xy=(x, y),
                                    xytext=(0, 10),
                                    textcoords="offset points",
                                    ha='center', fontsize=8)  # Smaller font size
                    
                    # Plot earnings trend
                    ax2.plot(df['date'], df['earnings'], marker='o', linestyle='-', color='forestgreen', 
                            linewidth=2, markersize=8)
                    ax2.set_title('Earnings Trend Over Time', fontweight='bold', fontsize=14)
                    ax2.set_ylabel('Earnings ($)', fontweight='bold', fontsize=12)
                    ax2.tick_params(axis='x', rotation=45)
                    ax2.grid(True, linestyle='--', alpha=0.7)
                    
                    # Add data labels for earnings
                    for i, (x, y) in enumerate(zip(df['date'], df['earnings'])):
                        ax2.annotate(f'${y:.2f}',
                                    xy=(x, y),
                                    xytext=(0, 10),
                                    textcoords="offset points",
                                    ha='center', fontsize=8)  # Smaller font size
                    
                    # Adjust x-axis labels for better readability
                    if len(df) > 5:
                        # For many dates, use better spacing
                        for ax in [ax1, ax2]:
                            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
                            ax.set_xticklabels(df['date'], fontsize=8)
                
                except Exception as e:
                    print(f"Error processing dates for line chart: {str(e)}")
            
            # Adjust spacing and layout for better fit
            plt.subplots_adjust(hspace=0.4, bottom=0.25, top=0.95, left=0.1, right=0.95)
            
            # Format ticks with smaller font
            for ax in [ax1, ax2]:
                ax.tick_params(axis='x', labelsize=8)
                ax.tick_params(axis='y', labelsize=9)
            
            # Create a frame for the chart container
            chart_container = ttk.Frame(self.line_chart_frame)
            chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=chart_container)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill=tk.BOTH, expand=True)
            
            # Add toolbar
            toolbar_frame = ttk.Frame(self.line_chart_frame)
            toolbar_frame.pack(fill=tk.X, padx=5)
            
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
        except Exception as e:
            print(f"Error generating line charts: {str(e)}")
            ttk.Label(self.line_chart_frame, text="Unable to display line charts. Error: " + str(e)).pack(pady=20)
    
    def _generate_pie_charts(self, df):
        """Generate pie charts for hours and earnings distribution"""
        try:
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 6), dpi=100)
            
            # Calculate total hours and earnings
            total_hours = df['hours'].sum()
            total_earnings = df['earnings'].sum()
            
            if not df.empty and total_hours > 0 and total_earnings > 0:
                # Create shortened labels if necessary for better visualization
                if len(df) > 5:
                    # If too many dates, group smaller values
                    # Sort by hours in descending order
                    df_sorted = df.sort_values(by='hours', ascending=False)
                    
                    # Take top 4 and group the rest as "Other"
                    top_dates = df_sorted.head(4)
                    other_hours = df_sorted.iloc[4:]['hours'].sum()
                    other_earnings = df_sorted.iloc[4:]['earnings'].sum()
                    
                    # Create new dataframes for pie charts
                    hours_data = pd.concat([
                        top_dates[['date', 'hours']],
                        pd.DataFrame({'date': ['Other'], 'hours': [other_hours]})
                    ])
                    
                    earnings_data = pd.concat([
                        top_dates[['date', 'earnings']],
                        pd.DataFrame({'date': ['Other'], 'earnings': [other_earnings]})
                    ])
                else:
                    hours_data = df[['date', 'hours']]
                    earnings_data = df[['date', 'earnings']]
                
                # Plot hours distribution
                wedges1, texts1, autotexts1 = ax1.pie(
                    hours_data['hours'],
                    labels=hours_data['date'],
                    autopct='%1.1f%%',
                    startangle=90,
                    shadow=False,
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
                    textprops={'fontsize': 8}  # Smaller font size for labels
                )
                
                # Add legend and title for hours
                ax1.set_title('Hours Distribution', fontweight='bold', fontsize=14)
                
                # Plot earnings distribution
                wedges2, texts2, autotexts2 = ax2.pie(
                    earnings_data['earnings'],
                    labels=earnings_data['date'],
                    autopct='%1.1f%%',
                    startangle=90,
                    shadow=False,
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
                    textprops={'fontsize': 8}  # Smaller font size for labels
                )
                
                # Add legend and title for earnings
                ax2.set_title('Earnings Distribution', fontweight='bold', fontsize=14)
                
                # Style the percentage text
                for autotext in autotexts1 + autotexts2:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                    autotext.set_fontsize(8)  # Smaller font size
                
                # Add legend for better readability when there are many slices
                if len(hours_data) > 3:
                    ax1.legend(
                        wedges1, 
                        hours_data['date'], 
                        loc='center left', 
                        bbox_to_anchor=(-0.1, 0.5),
                        fontsize=8
                    )
                    ax2.legend(
                        wedges2, 
                        earnings_data['date'], 
                        loc='center right', 
                        bbox_to_anchor=(1.1, 0.5),
                        fontsize=8
                    )
            else:
                ax1.text(0.5, 0.5, 'No data available for pie charts', 
                         ha='center', va='center', fontsize=12)
                ax2.text(0.5, 0.5, 'No data available for pie charts', 
                         ha='center', va='center', fontsize=12)
            
            plt.tight_layout(pad=2.0)  # More padding
            
            # Create a frame for the chart container
            chart_container = ttk.Frame(self.pie_chart_frame)
            chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=chart_container)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill=tk.BOTH, expand=True)
            
            # Add toolbar
            toolbar_frame = ttk.Frame(self.pie_chart_frame)
            toolbar_frame.pack(fill=tk.X, padx=5)
            
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
        except Exception as e:
            print(f"Error generating pie charts: {str(e)}")
            ttk.Label(self.pie_chart_frame, text="Unable to display pie charts. Error: " + str(e)).pack(pady=20)
    
    def _generate_weekly_charts(self, df):
        """Generate charts showing distribution of work by days of week"""
        try:
            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 10), dpi=100)
            
            # Set smaller font size for better fit
            plt.rcParams.update({'font.size': 10})
            
            # Prepare weekly data
            if not df.empty:
                try:
                    # Initialize dictionaries to hold data by day of week
                    days_of_week = {
                        0: {"name": "Monday", "hours": 0, "earnings": 0},
                        1: {"name": "Tuesday", "hours": 0, "earnings": 0},
                        2: {"name": "Wednesday", "hours": 0, "earnings": 0},
                        3: {"name": "Thursday", "hours": 0, "earnings": 0},
                        4: {"name": "Friday", "hours": 0, "earnings": 0},
                        5: {"name": "Saturday", "hours": 0, "earnings": 0},
                        6: {"name": "Sunday", "hours": 0, "earnings": 0}
                    }
                    
                    # Parse dates and aggregate by day of week
                    for _, row in df.iterrows():
                        date_str = row['date']
                        try:
                            if '-' in date_str:  # YYYY-MM-DD format
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            else:  # DD/MM/YYYY format
                                date_obj = datetime.strptime(date_str, DATE_FORMAT).date()
                            
                            day_of_week = date_obj.weekday()  # 0 is Monday, 6 is Sunday
                            days_of_week[day_of_week]["hours"] += row['hours']
                            days_of_week[day_of_week]["earnings"] += row['earnings']
                        except ValueError:
                            print(f"Could not parse date: {date_str}")
                            continue
                    
                    # Convert to lists for plotting
                    day_names = [day["name"] for day in days_of_week.values()]
                    hours = [day["hours"] for day in days_of_week.values()]
                    earnings = [day["earnings"] for day in days_of_week.values()]
                    
                    # Plot hours by day of week
                    bars1 = ax1.bar(day_names, hours, color='skyblue', width=0.7)
                    ax1.set_title('Hours by Day of Week', fontweight='bold', fontsize=14)
                    ax1.set_ylabel('Total Hours', fontweight='bold', fontsize=12)
                    ax1.tick_params(axis='x', rotation=30, labelsize=9)  # Reduced rotation and size
                    ax1.grid(True, linestyle='--', alpha=0.7)
                    
                    # Add data labels
                    for bar in bars1:
                        height = bar.get_height()
                        ax1.annotate(f'{height:.1f}',
                                    xy=(bar.get_x() + bar.get_width() / 2, height),
                                    xytext=(0, 3),
                                    textcoords="offset points",
                                    ha='center', va='bottom',
                                    fontsize=9)  # Smaller font size
                    
                    # Plot earnings by day of week
                    bars2 = ax2.bar(day_names, earnings, color='lightgreen', width=0.7)
                    ax2.set_title('Earnings by Day of Week', fontweight='bold', fontsize=14)
                    ax2.set_ylabel('Total Earnings ($)', fontweight='bold', fontsize=12)
                    ax2.tick_params(axis='x', rotation=30, labelsize=9)  # Reduced rotation and size
                    ax2.grid(True, linestyle='--', alpha=0.7)
                    
                    # Add data labels
                    for bar in bars2:
                        height = bar.get_height()
                        ax2.annotate(f'${height:.2f}',
                                    xy=(bar.get_x() + bar.get_width() / 2, height),
                                    xytext=(0, 3),
                                    textcoords="offset points",
                                    ha='center', va='bottom',
                                    fontsize=8)  # Smaller font size
                
                except Exception as e:
                    print(f"Error processing dates for weekly chart: {str(e)}")
                    ax1.text(0.5, 0.5, f'Error processing weekly data: {str(e)}', 
                             ha='center', va='center', fontsize=12, transform=ax1.transAxes)
                    ax2.text(0.5, 0.5, f'Error processing weekly data: {str(e)}', 
                             ha='center', va='center', fontsize=12, transform=ax2.transAxes)
            else:
                ax1.text(0.5, 0.5, 'No data available for weekly charts', 
                         ha='center', va='center', fontsize=12, transform=ax1.transAxes)
                ax2.text(0.5, 0.5, 'No data available for weekly charts', 
                         ha='center', va='center', fontsize=12, transform=ax2.transAxes)
            
            # Adjust spacing and layout for better fit
            plt.subplots_adjust(hspace=0.4, bottom=0.15, top=0.95, left=0.1, right=0.95)
            
            # Format ticks with smaller font
            for ax in [ax1, ax2]:
                ax.tick_params(axis='y', labelsize=9)
            
            # Create a frame for the chart container
            chart_container = ttk.Frame(self.weekly_chart_frame)
            chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=chart_container)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill=tk.BOTH, expand=True)
            
            # Add toolbar
            toolbar_frame = ttk.Frame(self.weekly_chart_frame)
            toolbar_frame.pack(fill=tk.X, padx=5)
            
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
        except Exception as e:
            print(f"Error generating weekly charts: {str(e)}")
            ttk.Label(self.weekly_chart_frame, text="Unable to display weekly charts. Error: " + str(e)).pack(pady=20)
    
    def show_day_details(self, date):
        """Show detailed information for a specific day"""
        # Create a popup window with details
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Details for {date}")
        detail_window.geometry("500x400")
        detail_window.transient(self.root)
        
        # Get records for the selected date
        self.cursor.execute("""
            SELECT start_time, end_time, break_duration, hourly_rate, total_hours, total_earnings, notes 
            FROM time_logs 
            WHERE date = ?
            ORDER BY start_time
        """, (date,))
        records = self.cursor.fetchall()
        
        if not records:
            ttk.Label(detail_window, text="No detailed records found for this date.").pack(padx=20, pady=20)
            return
        
        # Create a frame for the details
        detail_frame = ttk.Frame(detail_window, padding=10)
        detail_frame.pack(fill="both", expand=True)
        
        # Add a treeview for the records
        columns = ("start", "end", "break", "rate", "hours", "earnings", "notes")
        tree = ttk.Treeview(detail_frame, columns=columns, show="headings")
        
        # Setup column headings
        tree.heading("start", text="Start Time")
        tree.heading("end", text="End Time")
        tree.heading("break", text="Break (min)")
        tree.heading("rate", text="Rate ($/hr)")
        tree.heading("hours", text="Hours")
        tree.heading("earnings", text="Earnings")
        tree.heading("notes", text="Notes")
        
        # Setup column widths
        tree.column("start", width=70)
        tree.column("end", width=70)
        tree.column("break", width=70)
        tree.column("rate", width=70)
        tree.column("hours", width=70)
        tree.column("earnings", width=80)
        tree.column("notes", width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Make treeview expandable
        detail_frame.rowconfigure(0, weight=1)
        detail_frame.columnconfigure(0, weight=1)
        
        # Insert records
        for record in records:
            formatted_record = list(record)
            formatted_record[5] = f"${formatted_record[5]:.2f}"  # Format earnings
            tree.insert("", "end", values=formatted_record)
        
        # Add a summary frame
        summary_frame = ttk.LabelFrame(detail_window, text="Summary", padding=10)
        summary_frame.pack(fill="x", padx=10, pady=10)
        
        # Calculate totals
        total_hours = sum(record[4] for record in records)
        total_earnings = sum(record[5] for record in records)
        avg_rate = sum(record[3] for record in records) / len(records)
        
        # Add summary labels
        ttk.Label(summary_frame, text=f"Total Hours: {total_hours:.2f}").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(summary_frame, text=f"Total Earnings: ${total_earnings:.2f}").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(summary_frame, text=f"Average Hourly Rate: ${avg_rate:.2f}").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # Add a close button
        ttk.Button(detail_window, text="Close", command=detail_window.destroy).pack(pady=10)
    
    def export_to_csv(self):
        """Export the current filtered data to CSV"""
        try:
            # Get data based on current filter
            from_date = self.report_from_var.get() if self.report_type_var.get() == "Custom Range" else self.from_date_var.get()
            to_date = self.report_to_var.get() if self.report_type_var.get() == "Custom Range" else self.to_date_var.get()
            
            query = "SELECT * FROM time_logs WHERE 1=1"
            params = []
            
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
                
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
                
            query += " ORDER BY date DESC"
            
            self.cursor.execute(query, params)
            data = self.cursor.fetchall()
            
            if not data:
                messagebox.showinfo("No Data", "No records to export")
                return
                
            # Get file path for saving
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export to CSV"
            )
            
            if not file_path:
                return  # User cancelled
                
            # Create DataFrame and save to CSV
            columns = ["id", "date", "start_time", "end_time", "break_duration", 
                       "hourly_rate", "total_hours", "total_earnings", "notes"]
            df = pd.DataFrame(data, columns=columns)
            df.to_csv(file_path, index=False)
            
            messagebox.showinfo("Export Successful", f"Data exported to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
    
    def export_to_excel(self):
        """Export the current filtered data to Excel"""
        try:
            # Get data based on current filter
            from_date = self.report_from_var.get() if self.report_type_var.get() == "Custom Range" else self.from_date_var.get()
            to_date = self.report_to_var.get() if self.report_type_var.get() == "Custom Range" else self.to_date_var.get()
            
            query = "SELECT * FROM time_logs WHERE 1=1"
            params = []
            
            if from_date:
                query += " AND date >= ?"
                params.append(from_date)
                
            if to_date:
                query += " AND date <= ?"
                params.append(to_date)
                
            query += " ORDER BY date DESC"
            
            self.cursor.execute(query, params)
            data = self.cursor.fetchall()
            
            if not data:
                messagebox.showinfo("No Data", "No records to export")
                return
                
            # Get file path for saving
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Export to Excel"
            )
            
            if not file_path:
                return  # User cancelled
                
            # Create DataFrame and save to Excel
            columns = ["id", "date", "start_time", "end_time", "break_duration", 
                       "hourly_rate", "total_hours", "total_earnings", "notes"]
            df = pd.DataFrame(data, columns=columns)
            
            # Format earnings column with currency
            df["total_earnings"] = df["total_earnings"].apply(lambda x: f"${x:.2f}")
            
            # Create Excel writer
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Work Records', index=False)
                
                # Get the worksheet
                workbook = writer.book
                worksheet = writer.sheets['Work Records']
                
                # Format headers
                for col in range(1, len(columns) + 1):
                    cell = worksheet.cell(row=1, column=col)
                    cell.font = Font(bold=True)
            
            messagebox.showinfo("Export Successful", f"Data exported to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
            
    def add_payroll_period(self):
        """Add a new payroll period to the database"""
        try:
            # Get values from form
            period_name = self.period_name_var.get()
            start_date = self.period_start_var.get()
            end_date = self.period_end_var.get()
            is_default = 1 if self.default_period_var.get() else 0
            
            # Validate inputs
            if not period_name or not start_date or not end_date:
                messagebox.showwarning("Missing Information", "Please provide a name, start date, and end date.")
                return
                
            # Validate dates format
            try:
                datetime.strptime(start_date, "%d/%m/%Y")
                datetime.strptime(end_date, "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning("Invalid Date Format", "Please use dd/mm/yyyy format for dates.")
                return
                
            # If setting as default, clear other defaults
            if is_default:
                self.cursor.execute("UPDATE payroll_periods SET is_default = 0")
                
            # Insert new period
            self.cursor.execute('''
                INSERT INTO payroll_periods (period_name, start_date, end_date, is_default)
                VALUES (?, ?, ?, ?)
            ''', (period_name, start_date, end_date, is_default))
            self.conn.commit()
            
            messagebox.showinfo("Success", "Payroll period added successfully!")
            self.load_payroll_periods()
            
            # Clear form
            self.period_name_var.set("")
            self.period_start_var.set("")
            self.period_end_var.set("")
            self.default_period_var.set(False)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add payroll period: {str(e)}")
    
    def generate_recurring_periods(self):
        """Generate multiple recurring payroll periods based on the specified pattern"""
        try:
            # Get values from form
            base_name = self.period_name_var.get()
            start_date_str = self.period_start_var.get()
            end_date_str = self.period_end_var.get()
            num_periods = self.num_periods_var.get()
            
            # Validate inputs
            if not base_name or not start_date_str or not end_date_str:
                messagebox.showwarning("Missing Information", "Please provide a name, start date, and end date.")
                return
                
            # Parse dates
            try:
                start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
                end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning("Invalid Date Format", "Please use dd/mm/yyyy format for dates.")
                return
                
            # Calculate period duration
            period_duration = (end_date - start_date).days + 1
            
            # Begin a transaction
            self.conn.execute("BEGIN TRANSACTION")
            
            # Set first period as default if requested
            if self.default_period_var.get():
                self.cursor.execute("UPDATE payroll_periods SET is_default = 0")
                is_default = 1
            else:
                is_default = 0
                
            # Generate and insert periods
            for i in range(num_periods):
                # Calculate dates for this period
                current_start = start_date + timedelta(days=i * period_duration)
                current_end = end_date + timedelta(days=i * period_duration)
                
                # Generate period name
                if base_name.startswith("Payroll") or base_name.startswith("Weekly") or base_name.startswith("Biweekly"):
                    # For auto-generated names, recreate the name with proper dates
                    current_name = f"{base_name.split(' ')[0]} {current_start.strftime('%b %d')} - {current_end.strftime('%b %d, %Y')}"
                else:
                    # For custom names, append a number
                    current_name = f"{base_name} ({i+1})"
                
                # Insert period
                self.cursor.execute('''
                    INSERT INTO payroll_periods (period_name, start_date, end_date, is_default)
                    VALUES (?, ?, ?, ?)
                ''', (current_name, current_start.strftime("%d/%m/%Y"), 
                      current_end.strftime("%d/%m/%Y"), 1 if i == 0 and is_default else 0))
            
            # Commit transaction
            self.conn.commit()
            
            messagebox.showinfo("Success", f"Generated {num_periods} payroll periods!")
            self.load_payroll_periods()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Failed to generate payroll periods: {str(e)}")
    
    def load_payroll_periods(self):
        """Load payroll periods from database into the treeview"""
        # Clear existing items
        for item in self.period_tree.get_children():
            self.period_tree.delete(item)
            
        # Get payroll periods
        self.cursor.execute("SELECT id, period_name, start_date, end_date, is_default FROM payroll_periods ORDER BY start_date DESC")
        periods = self.cursor.fetchall()
        
        # Insert into treeview
        for period in periods:
            # Format default status
            period_list = list(period)
            period_list[4] = "Yes" if period[4] else "No"
            self.period_tree.insert("", "end", values=period_list)
    
    def set_default_period(self):
        """Set the selected payroll period as default"""
        selected = self.period_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a payroll period")
            return
            
        # Get the selected period ID
        period_id = self.period_tree.item(selected[0])['values'][0]
        
        try:
            # Clear all defaults
            self.cursor.execute("UPDATE payroll_periods SET is_default = 0")
            
            # Set new default
            self.cursor.execute("UPDATE payroll_periods SET is_default = 1 WHERE id = ?", (period_id,))
            self.conn.commit()
            
            messagebox.showinfo("Success", "Default payroll period updated!")
            self.load_payroll_periods()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update default period: {str(e)}")
    
    def delete_period(self):
        """Delete the selected payroll period"""
        selected = self.period_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a payroll period")
            return
            
        # Get the selected period ID
        period_id = self.period_tree.item(selected[0])['values'][0]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this payroll period?"):
            return
            
        try:
            # Delete the period
            self.cursor.execute("DELETE FROM payroll_periods WHERE id = ?", (period_id,))
            self.conn.commit()
            
            messagebox.showinfo("Success", "Payroll period deleted!")
            self.load_payroll_periods()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete period: {str(e)}")
    
    def report_for_period(self):
        """Generate a report for the selected payroll period"""
        selected = self.period_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Required", "Please select a payroll period")
            return
            
        # Get the selected period details
        period_data = self.period_tree.item(selected[0])['values']
        period_id = period_data[0]
        period_name = period_data[1]
        start_date = period_data[2]
        end_date = period_data[3]
        
        # Set the report dates and switch to Reports tab
        self.report_type_var.set("Custom Range")
        self.report_from_var.set(start_date)
        self.report_to_var.set(end_date)
        
        # Switch to report tab
        self.notebook.select(3)  # Index of the Reports tab
        
        # Generate the report
        self.generate_report()
    
    def apply_period_type(self):
        """Apply the selected period type to set appropriate dates"""
        period_type = self.period_type_var.get()
        today = datetime.now()
        
        if period_type == "Monthly":
            # 26th of current month to 25th of next month
            if today.day < 26:
                # If today is before 26th, start from 26th of last month
                start_month = today.month - 1 if today.month > 1 else 12
                start_year = today.year if today.month > 1 else today.year - 1
                start_date = datetime(start_year, start_month, 26)
            else:
                # Start from 26th of current month
                start_date = datetime(today.year, today.month, 26)
                
            # End date is the 25th of next month
            if start_date.month == 12:
                end_date = datetime(start_date.year + 1, 1, 25)
            else:
                end_date = datetime(start_date.year, start_date.month + 1, 25)
            
            period_name = f"Monthly Payroll {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
            
        elif period_type == "Bi-weekly":
            # Current day to 14 days later
            start_date = today
            end_date = today + timedelta(days=13)
            period_name = f"Bi-weekly {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
            
        elif period_type == "Weekly":
            # Monday to Sunday
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            period_name = f"Weekly {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
            
        elif period_type == "Yearly":
            # January 1 to December 31
            start_date = datetime(today.year, 1, 1)
            end_date = datetime(today.year, 12, 31)
            period_name = f"Yearly {today.year}"
            
        else:  # Custom - don't change dates
            return
            
        # Update form fields
        self.period_start_var.set(start_date.strftime(DATE_FORMAT))
        self.period_end_var.set(end_date.strftime(DATE_FORMAT))
        self.period_name_var.set(period_name)
    
    def open_csv_file(self):
        """Open the CSV file with the default application"""
        try:
            # Make sure CSV is up to date
            self.sync_to_csv()
            
            # Open CSV file with default application
            if os.path.exists(self.csv_file_path):
                if os.name == 'nt':  # Windows
                    os.startfile(self.csv_file_path)
                else:  # macOS and Linux
                    import subprocess
                    subprocess.call(['open' if os.name == 'posix' else 'xdg-open', self.csv_file_path])
                    
                messagebox.showinfo("CSV File", f"CSV file opened: {self.csv_file_path}")
            else:
                messagebox.showwarning("File Not Found", "CSV file does not exist. Try adding some records first.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open CSV file: {str(e)}")
    
    def show_calendar_popup(self, date_var_name):
        """
        Display an improved calendar popup for date selection
        
        Args:
            date_var_name: String identifier for which date variable to update ('report_from' or 'report_to')
        """
        # Get the actual StringVar based on the passed identifier
        if date_var_name == "report_from":
            date_var = self.report_from_var
        elif date_var_name == "report_to":
            date_var = self.report_to_var
        elif hasattr(self, date_var_name):
            # If the name directly matches an attribute that is a StringVar
            date_var = getattr(self, date_var_name)
        else:
            print(f"Error: Unknown date variable identifier: {date_var_name}")
            return
        
        def set_date():
            # Get selected date from calendar
            selected_date = cal.get_date()
            print(f"Selected date from calendar: {selected_date}")
            
            # Format the date consistently
            try:
                # Ensure date is in dd/mm/yyyy format regardless of how it was returned
                if isinstance(selected_date, str):
                    if '-' in selected_date:  # YYYY-MM-DD format
                        date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
                    elif '/' in selected_date:  # DD/MM/YYYY format
                        date_obj = datetime.strptime(selected_date, DATE_FORMAT).date()
                    else:
                        # Unknown format - try common formats
                        try:
                            date_obj = datetime.strptime(selected_date, "%m/%d/%Y").date()
                        except ValueError:
                            # Last resort - current date
                            date_obj = datetime.now().date()
                else:
                    # It's already a date object
                    date_obj = selected_date
                    
                # Set the formatted date
                formatted_date = date_obj.strftime(DATE_FORMAT)
                date_var.set(formatted_date)
                print(f"Setting {date_var_name} to: {formatted_date}")
            except Exception as e:
                print(f"Error formatting date: {e}")
                # If all else fails, just set whatever we received
                date_var.set(str(selected_date))
                
            # Destroy the popup
            top.destroy()
            
            # Regenerate report with the new date
            self.generate_report()
            
        # Create the popup window
        top = tk.Toplevel(self.root)
        top.title("Select Date")
        top.geometry("320x380")  # Increased height for additional elements
        top.resizable(False, False)
        
        # Add a header with instructions
        header_frame = ttk.Frame(top)
        header_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(header_frame, text=f"Select date for {date_var_name.replace('_', ' ').title()}", 
                 font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        # Add date format reminder
        format_frame = ttk.Frame(top)
        format_frame.pack(fill="x", padx=10, pady=2)
        ttk.Label(format_frame, text="Date format: dd/mm/yyyy", foreground="blue").pack(side=tk.LEFT)
        
        # Create the calendar with explicit date pattern
        cal = Calendar(top, selectmode='day', date_pattern='dd/mm/yyyy')
        cal.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Try to set the calendar to the currently selected date
        current_date = date_var.get()
        if current_date:
            try:
                if '/' in current_date:  # DD/MM/YYYY format
                    date_obj = datetime.strptime(current_date, DATE_FORMAT).date()
                else:  # Assume YYYY-MM-DD format
                    date_obj = datetime.strptime(current_date, DB_DATE_FORMAT).date()
                    
                cal.selection_set(date_obj)
            except (ValueError, TypeError) as e:
                print(f"Error setting calendar date: {e}")
                # If invalid, don't set a selection
        
        # Add buttons for quick selection of today, this week, this month
        quick_frame = ttk.Frame(top)
        quick_frame.pack(fill="x", padx=10, pady=5)
        
        today = datetime.now().date()
        
        ttk.Button(quick_frame, text="Today", 
                  command=lambda: cal.selection_set(today)).pack(side=tk.LEFT, padx=5)
        
        # First day of month
        first_of_month = today.replace(day=1)
        ttk.Button(quick_frame, text="Month Start", 
                  command=lambda: cal.selection_set(first_of_month)).pack(side=tk.LEFT, padx=5)
        
        # Last day of month
        if today.month == 12:
            last_of_month = today.replace(day=31)
        else:
            next_month = today.replace(month=today.month+1, day=1)
            last_of_month = next_month - timedelta(days=1)
            
        ttk.Button(quick_frame, text="Month End", 
                  command=lambda: cal.selection_set(last_of_month)).pack(side=tk.LEFT, padx=5)
        
        # Add confirm button
        button_frame = ttk.Frame(top)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Confirm", command=set_date, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=top.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Make the dialog modal
        top.transient(self.root)
        top.grab_set()
        self.root.wait_window(top)
    
    def show_overview_report(self):
        """Show a comprehensive overview report in a popup window"""
        try:
            # Create popup window
            overview_window = tk.Toplevel(self.root)
            overview_window.title("Comprehensive Work Overview")
            overview_window.geometry("800x600")
            overview_window.transient(self.root)
            
            # Get current date range
            from_date = self.report_from_var.get() if self.report_from_var.get() else "01/04/2025" 
            to_date = self.report_to_var.get() if self.report_to_var.get() else "30/04/2025"
            
            # Convert dates if needed
            if '/' in from_date:
                db_from_date = from_date.split('/')
                db_from_date = f"{db_from_date[2]}-{db_from_date[1]}-{db_from_date[0]}"
            else:
                db_from_date = from_date
                
            if '/' in to_date:
                db_to_date = to_date.split('/')
                db_to_date = f"{db_to_date[2]}-{db_to_date[1]}-{db_to_date[0]}"
            else:
                db_to_date = to_date
            
            # Create a notebook for different overview sections
            notebook = ttk.Notebook(overview_window)
            notebook.pack(fill="both", expand=True, padx=10, pady=10)
            
            # 1. Summary Tab
            summary_frame = ttk.Frame(notebook)
            notebook.add(summary_frame, text="Summary")
            
            # Add title
            title_frame = ttk.Frame(summary_frame)
            title_frame.pack(fill="x", padx=10, pady=10)
            
            ttk.Label(title_frame, text=f"Work Summary: {from_date} to {to_date}", 
                     font=("Arial", 14, "bold")).pack(pady=5)
            
            # Get overall statistics
            query = f"""
                SELECT 
                    COUNT(DISTINCT date) as work_days,
                    SUM(total_hours) as total_hours,
                    SUM(total_earnings) as total_earnings,
                    AVG(hourly_rate) as avg_rate,
                    MIN(hourly_rate) as min_rate,
                    MAX(hourly_rate) as max_rate
                FROM time_logs 
                WHERE date BETWEEN '{db_from_date}' AND '{db_to_date}'
            """
            self.cursor.execute(query)
            stats = self.cursor.fetchone()
            
            if not stats or stats[0] == 0:
                ttk.Label(summary_frame, text="No data available for the selected period.", 
                         font=("Arial", 12)).pack(pady=50)
                return
                
            work_days, total_hours, total_earnings, avg_rate, min_rate, max_rate = stats
            
            # Create stats frame
            stats_frame = ttk.LabelFrame(summary_frame, text="Key Statistics")
            stats_frame.pack(fill="x", padx=10, pady=10)
            
            # First row of stats
            row1 = ttk.Frame(stats_frame)
            row1.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(row1, text="Work Days:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, sticky="w")
            ttk.Label(row1, text=f"{work_days}").grid(row=0, column=1, padx=10, sticky="w")
            
            ttk.Label(row1, text="Total Hours:", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=10, sticky="w")
            ttk.Label(row1, text=f"{total_hours:.2f}").grid(row=0, column=3, padx=10, sticky="w")
            
            ttk.Label(row1, text="Total Earnings:", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=10, sticky="w")
            ttk.Label(row1, text=f"${total_earnings:.2f}").grid(row=0, column=5, padx=10, sticky="w")
            
            # Second row of stats
            row2 = ttk.Frame(stats_frame)
            row2.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(row2, text="Avg. Daily Hours:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, sticky="w")
            ttk.Label(row2, text=f"{(total_hours/work_days):.2f}" if work_days else "0.00").grid(row=0, column=1, padx=10, sticky="w")
            
            ttk.Label(row2, text="Avg. Hourly Rate:", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=10, sticky="w")
            ttk.Label(row2, text=f"${avg_rate:.2f}").grid(row=0, column=3, padx=10, sticky="w")
            
            ttk.Label(row2, text="Rate Range:", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=10, sticky="w")
            ttk.Label(row2, text=f"${min_rate:.2f} - ${max_rate:.2f}").grid(row=0, column=5, padx=10, sticky="w")
            
            # Third row - Daily average
            row3 = ttk.Frame(stats_frame)
            row3.pack(fill="x", padx=10, pady=5)
            
            ttk.Label(row3, text="Avg. Daily Earnings:", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=10, sticky="w")
            ttk.Label(row3, text=f"${(total_earnings/work_days):.2f}" if work_days else "$0.00").grid(row=0, column=1, padx=10, sticky="w")
            
            # Get dates for period duration calculation
            from_date_obj = datetime.strptime(from_date, DATE_FORMAT).date() if '/' in from_date else datetime.strptime(from_date, DB_DATE_FORMAT).date()
            to_date_obj = datetime.strptime(to_date, DATE_FORMAT).date() if '/' in to_date else datetime.strptime(to_date, DB_DATE_FORMAT).date()
            period_days = (to_date_obj - from_date_obj).days + 1
            
            ttk.Label(row3, text="Period Duration:", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=10, sticky="w")
            ttk.Label(row3, text=f"{period_days} days").grid(row=0, column=3, padx=10, sticky="w")
            
            ttk.Label(row3, text="Work Coverage:", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=10, sticky="w")
            coverage = work_days / period_days * 100 if period_days > 0 else 0
            ttk.Label(row3, text=f"{coverage:.1f}%").grid(row=0, column=5, padx=10, sticky="w")
            
            # Add mini chart for hours by day
            query = f"""
                SELECT date, SUM(total_hours) as hours
                FROM time_logs 
                WHERE date BETWEEN '{db_from_date}' AND '{db_to_date}'
                GROUP BY date
                ORDER BY date
            """
            self.cursor.execute(query)
            daily_data = self.cursor.fetchall()
            
            # Create a mini chart
            if daily_data:
                chart_frame = ttk.LabelFrame(summary_frame, text="Hours by Day")
                chart_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                fig, ax = plt.subplots(figsize=(7, 3), dpi=100)
                
                dates = [row[0] for row in daily_data]
                hours = [row[1] for row in daily_data]
                
                ax.bar(dates, hours, color='skyblue')
                ax.set_ylabel('Hours')
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                canvas = FigureCanvasTkAgg(fig, master=chart_frame)
                canvas.draw()
                canvas_widget = canvas.get_tk_widget()
                canvas_widget.pack(fill=tk.BOTH, expand=True)
            
            # 2. Weekly Trends Tab
            weekly_frame = ttk.Frame(notebook)
            notebook.add(weekly_frame, text="Weekly Analysis")
            
            # Query data grouped by day of week
            query = f"""
                SELECT date, total_hours, total_earnings
                FROM time_logs 
                WHERE date BETWEEN '{db_from_date}' AND '{db_to_date}'
                ORDER BY date
            """
            self.cursor.execute(query)
            records = self.cursor.fetchall()
            
            if records:
                # Process data by day of week
                days_of_week = {i: {"name": day, "hours": 0, "earnings": 0, "count": 0} 
                               for i, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])}
                
                for record in records:
                    date_str = record[0]
                    hours = record[1]
                    earnings = record[2]
                    
                    try:
                        if '-' in date_str:  # YYYY-MM-DD format
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        else:  # DD/MM/YYYY format
                            date_obj = datetime.strptime(date_str, DATE_FORMAT).date()
                        
                        day_idx = date_obj.weekday()  # 0 is Monday, 6 is Sunday
                        days_of_week[day_idx]["hours"] += hours
                        days_of_week[day_idx]["earnings"] += earnings
                        days_of_week[day_idx]["count"] += 1
                    except ValueError:
                        print(f"Could not parse date: {date_str}")
                
                # Create two side-by-side charts
                week_charts_frame = ttk.Frame(weekly_frame)
                week_charts_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Hours by day of week
                hours_frame = ttk.LabelFrame(week_charts_frame, text="Hours by Day of Week")
                hours_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)
                
                fig1, ax1 = plt.subplots(figsize=(4, 3), dpi=100)
                
                day_names = [day["name"] for day in days_of_week.values()]
                hours = [day["hours"] for day in days_of_week.values()]
                
                ax1.bar(day_names, hours, color='skyblue')
                ax1.tick_params(axis='x', rotation=45)
                ax1.set_ylabel('Total Hours')
                ax1.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                canvas1 = FigureCanvasTkAgg(fig1, master=hours_frame)
                canvas1.draw()
                canvas1_widget = canvas1.get_tk_widget()
                canvas1_widget.pack(fill=tk.BOTH, expand=True)
                
                # Earnings by day of week
                earnings_frame = ttk.LabelFrame(week_charts_frame, text="Earnings by Day of Week")
                earnings_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=5, pady=5)
                
                fig2, ax2 = plt.subplots(figsize=(4, 3), dpi=100)
                
                earnings = [day["earnings"] for day in days_of_week.values()]
                
                ax2.bar(day_names, earnings, color='lightgreen')
                ax2.tick_params(axis='x', rotation=45)
                ax2.set_ylabel('Total Earnings ($)')
                ax2.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                canvas2 = FigureCanvasTkAgg(fig2, master=earnings_frame)
                canvas2.draw()
                canvas2_widget = canvas2.get_tk_widget()
                canvas2_widget.pack(fill=tk.BOTH, expand=True)
                
                # Add most productive day info
                info_frame = ttk.Frame(weekly_frame)
                info_frame.pack(fill="x", padx=10, pady=10)
                
                # Most productive day (by hours)
                most_hours_idx = max(range(len(hours)), key=lambda i: 0 if days_of_week[i]["count"] == 0 else hours[i])
                most_hours_day = days_of_week[most_hours_idx]["name"]
                avg_hours = hours[most_hours_idx] / days_of_week[most_hours_idx]["count"] if days_of_week[most_hours_idx]["count"] > 0 else 0
                
                # Most profitable day (by earnings)
                most_earnings_idx = max(range(len(earnings)), key=lambda i: 0 if days_of_week[i]["count"] == 0 else earnings[i])
                most_earnings_day = days_of_week[most_earnings_idx]["name"]
                avg_earnings = earnings[most_earnings_idx] / days_of_week[most_earnings_idx]["count"] if days_of_week[most_earnings_idx]["count"] > 0 else 0
                
                ttk.Label(info_frame, text=f"Most Productive Day: {most_hours_day} (Avg: {avg_hours:.2f} hours)", 
                         font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
                
                ttk.Label(info_frame, text=f"Most Profitable Day: {most_earnings_day} (Avg: ${avg_earnings:.2f})", 
                         font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=10)
                
            else:
                ttk.Label(weekly_frame, text="No data available for weekly analysis.", 
                         font=("Arial", 12)).pack(pady=50)
                
            # 3. Recommendations Tab
            recommend_frame = ttk.Frame(notebook)
            notebook.add(recommend_frame, text="Recommendations")
            
            recommend_text = tk.Text(recommend_frame, wrap=tk.WORD, width=80, height=20)
            recommend_text.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Generate some basic recommendations based on the data
            recommendations = ["# Work Insights and Recommendations\n\n"]
            
            if work_days > 0:
                # Add recommendation about working hours
                avg_daily_hours = total_hours / work_days
                if avg_daily_hours > 8:
                    recommendations.append("⚠️ **Your average daily hours (%.2f) exceed 8 hours**. Consider taking more breaks to prevent burnout.\n" % avg_daily_hours)
                elif avg_daily_hours < 4:
                    recommendations.append("📊 **Your average daily hours (%.2f) are below 4**. Consider increasing work hours if you want to boost earnings.\n" % avg_daily_hours)
                else:
                    recommendations.append("✅ **Your average daily hours (%.2f) are in a healthy range**.\n" % avg_daily_hours)
                    
                # Add recommendation about hourly rate
                if max_rate > avg_rate * 1.5:
                    recommendations.append("💡 **Your hourly rate varies significantly** (from $%.2f to $%.2f). Try to prioritize higher-paying work when possible.\n" % (min_rate, max_rate))
                
                # Add recommendation about work coverage
                if coverage < 50:
                    recommendations.append("📅 **Your work coverage is low (%.1f%%)**. Consider distributing work more evenly throughout the period.\n" % coverage)
                
                # Add recommendation based on day of week analysis if we have that data
                if 'most_hours_day' in locals():
                    recommendations.append("📈 **%s is your most productive day** in terms of hours worked.\n" % most_hours_day)
                    
                if 'most_earnings_day' in locals() and most_earnings_day != most_hours_day:
                    recommendations.append("💰 **%s is your most profitable day**, which differs from your most productive day. Consider focusing more on high-value work on %s.\n" % (most_earnings_day, most_earnings_day))
                    
                # Add projected earnings
                monthly_projection = (total_earnings / period_days) * 30
                recommendations.append("\n## Projections\n\n")
                recommendations.append("💼 **Monthly projection**: At your current rate, you would earn approximately $%.2f per month.\n" % monthly_projection)
                yearly_projection = monthly_projection * 12
                recommendations.append("🗓️ **Yearly projection**: This translates to roughly $%.2f per year.\n" % yearly_projection)
                
                # Add section about next steps
                recommendations.append("\n## Next Steps\n\n")
                recommendations.append("1. Review your hourly rates and consider if adjustments are needed\n")
                recommendations.append("2. Plan your work schedule to maximize your most productive days\n")
                recommendations.append("3. Set specific goals for the next period based on these insights\n")
                
            else:
                recommendations.append("No sufficient data available to generate recommendations.")
                
            # Add the recommendations to the text widget
            recommend_text.insert(tk.END, '\n'.join(recommendations))
            recommend_text.config(state=tk.DISABLED)  # Make it read-only
            
            # 4. Export Options
            ttk.Button(overview_window, text="Print Report", 
                    command=lambda: messagebox.showinfo("Print", "Printing functionality would be implemented here")).pack(side=tk.LEFT, padx=10, pady=10)
            
            ttk.Button(overview_window, text="Close", 
                    command=overview_window.destroy).pack(side=tk.RIGHT, padx=10, pady=10)
            
        except Exception as e:
            messagebox.showerror("Report Error", f"Error generating overview report: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def export_to_pdf(self):
        """Export the current data as a PDF report"""
        try:
            # First, check if we have any data to report
            from_date = self.report_from_var.get() if self.report_type_var.get() == "Custom Range" else self.from_date_var.get()
            to_date = self.report_to_var.get() if self.report_type_var.get() == "Custom Range" else self.to_date_var.get()
            
            if not from_date or not to_date:
                # Use default date range if none specified
                from_date = "01/04/2025"
                to_date = "30/04/2025"
            
            # Get data for the report - convert dates to database format
            db_from_date = self.convert_to_db_date_format(from_date)
            db_to_date = self.convert_to_db_date_format(to_date)
            
            query = """
                SELECT date, start_time, end_time, break_duration, hourly_rate, total_hours, total_earnings, notes
                FROM time_logs 
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """
            
            self.cursor.execute(query, (db_from_date, db_to_date))
            records = self.cursor.fetchall()
            
            # Process dates for display in PDF - convert DB format to dd/mm/yyyy
            display_records = []
            for record in records:
                record_list = list(record)
                if record[0] and '-' in record[0]:  # If date is in YYYY-MM-DD format
                    try:
                        date_obj = datetime.strptime(record[0], DB_DATE_FORMAT).date()
                        record_list[0] = date_obj.strftime(DATE_FORMAT)
                    except ValueError:
                        pass  # Keep original if conversion fails
                display_records.append(record_list)
            
            if not display_records:
                messagebox.showinfo("No Data", "No records to export")
                return
                
            # Get file path for saving
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Save PDF Report"
            )
            
            if not file_path:
                return  # User cancelled
            
            try:
                # Try to import ReportLab - we'll need to make sure this package is installed
                from reportlab.lib.pagesizes import letter, landscape
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib import colors
                from reportlab.graphics.shapes import Drawing
                from reportlab.graphics.charts.barcharts import VerticalBarChart
                from reportlab.lib.units import inch
            except ImportError:
                messagebox.showinfo("Missing Package", 
                                   "The ReportLab package is required for PDF export. Please install it using: pip install reportlab")
                return
                
            # Create PDF document
            doc = SimpleDocTemplate(file_path, pagesize=landscape(letter))
            styles = getSampleStyleSheet()
            elements = []
            
            # Add title
            title_style = styles["Title"]
            report_title = f"Work Time Report: {from_date} - {to_date}"
            elements.append(Paragraph(report_title, title_style))
            elements.append(Spacer(1, 0.25*inch))
            
            # Add summary section
            summary_style = styles["Heading2"]
            elements.append(Paragraph("Summary", summary_style))
            
            # Calculate summary statistics
            total_hours = sum(record[5] for record in display_records) if display_records else 0
            total_earnings = sum(record[6] for record in display_records) if display_records else 0
            
            # Create summary table
            summary_data = [
                ["Total Hours", "Total Earnings", "Period", "Number of Records"],
                [f"{total_hours:.2f}", f"${total_earnings:.2f}", f"{from_date} - {to_date}", f"{len(display_records)}"]
            ]
            
            summary_table = Table(summary_data, colWidths=[1.5*inch, 1.5*inch, 2*inch, 1.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(summary_table)
            elements.append(Spacer(1, 0.25*inch))
            
            # Add detailed records section
            elements.append(Paragraph("Detailed Records", summary_style))
            
            # Create detailed table
            detailed_data = [["Date", "Start", "End", "Break", "Rate", "Hours", "Earnings", "Notes"]]
            
            for record in display_records:
                # Format values for better display
                row_data = [
                    record[0],  # Date (already in dd/mm/yyyy format)
                    record[1],  # Start time
                    record[2],  # End time
                    f"{record[3]} min",  # Break
                    f"${record[4]:.2f}",  # Rate
                    f"{record[5]:.2f}",  # Hours
                    f"${record[6]:.2f}",  # Earnings
                    record[7] if record[7] else ""  # Notes
                ]
                detailed_data.append(row_data)
            
            # Create the table with column widths
            col_widths = [1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch, 3*inch]
            detailed_table = Table(detailed_data, colWidths=col_widths)
            
            # Set the table style
            detailed_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                # Left-align the notes column
                ('ALIGN', (7, 1), (7, -1), 'LEFT')
            ]))
            
            elements.append(detailed_table)
            
            # Try to include a simple bar chart if we have data
            if len(display_records) > 0:
                elements.append(Spacer(1, 0.5*inch))
                elements.append(Paragraph("Hours by Date", summary_style))
                
                # Create a simple bar chart
                drawing = Drawing(600, 200)
                chart = VerticalBarChart()
                chart.x = 50
                chart.y = 50
                chart.height = 125
                chart.width = 500
                
                # Gather data by date
                dates = {}
                for record in display_records:
                    date = record[0]  # Date in dd/mm/yyyy format
                    hours = record[5]
                    if date in dates:
                        dates[date] += hours
                    else:
                        dates[date] = hours
                
                # Sort dates - need special handling for dd/mm/yyyy format
                def date_key(date_str):
                    try:
                        return datetime.strptime(date_str, DATE_FORMAT).date()
                    except ValueError:
                        return datetime.now().date()  # Fallback
                        
                sorted_dates = sorted(dates.keys(), key=date_key)
                hours_data = [[dates[date] for date in sorted_dates]]
                
                chart.data = hours_data
                chart.categoryAxis.categoryNames = sorted_dates
                chart.categoryAxis.labels.boxAnchor = 'ne'
                chart.categoryAxis.labels.angle = 45
                chart.categoryAxis.labels.dx = -8
                chart.categoryAxis.labels.dy = -2
                
                chart.bars[0].fillColor = colors.lightblue
                
                drawing.add(chart)
                elements.append(drawing)
            
            # Build the PDF
            doc.build(elements)
            
            messagebox.showinfo("Export Successful", f"PDF report saved to {file_path}")
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export PDF: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def toggle_comparison(self):
        """Toggle comparison to previous period on/off"""
        # Get current state of the checkbox
        is_enabled = self.compare_enabled_var.get()
        
        # Enable/disable the comparison display
        state = "normal" if is_enabled else "disabled"
        
        # Update the labels
        for widget in self.comparison_frame.winfo_children():
            if isinstance(widget, ttk.Label) and widget not in [self.compare_hours_label, self.compare_earnings_label]:
                widget.configure(state=state)
        
        # If enabled and we have a valid date range, generate the comparison now
        if is_enabled and self.report_from_var.get() and self.report_to_var.get():
            self.generate_report()  # This will update the comparison section
    
    def update_date_range(self):
        """
        Get min and max dates from database and update date fields.
        Renamed from update_date_slider.
        """
        # Get min and max dates from database
        self.cursor.execute("SELECT MIN(date), MAX(date) FROM time_logs")
        result = self.cursor.fetchone()
        
        if result[0] is not None and result[1] is not None:
            try:
                print(f"Database date range: {result[0]} to {result[1]}")
                # Parse dates with the utility class
                min_date = DateUtils.string_to_date(result[0])
                max_date = DateUtils.string_to_date(result[1])
                
                # Convert to display format for labels
                min_date_display = DateUtils.date_to_string(min_date)
                max_date_display = DateUtils.date_to_string(max_date)
                
                print(f"Parsed min_date: {min_date}, max_date: {max_date}")
                
                # Store the date range for later use
                self.min_date = min_date
                self.max_date = max_date
                
                # Set default date range if we don't have one yet
                if not self.report_from_var.get():
                    self.report_from_var.set(min_date_display)
                if not self.report_to_var.get():
                    self.report_to_var.set(max_date_display)
                    
            except Exception as e:
                print(f"Error setting up date range: {str(e)}")
                # Fall back to default dates
                self.set_fallback_dates()
        else:
            # No records, fallback to default dates
            self.set_fallback_dates()
    
    def set_fallback_dates(self):
        """Set fallback dates when no database dates are available"""
        self.min_date = DateUtils.string_to_date(DEFAULT_DATE_RANGE[0])
        self.max_date = DateUtils.string_to_date(DEFAULT_DATE_RANGE[1])
        
        # Set default date range
        self.report_from_var.set(DEFAULT_DATE_RANGE[0])
        self.report_to_var.set(DEFAULT_DATE_RANGE[1])
    
    def set_quick_date_range(self, option):
        """
        Set date range based on quick selection options.
        All options dynamically adjust based on the current system date.
        """
        # Get date range from utility class
        start_date, end_date = DateUtils.get_date_range(option)
        
        # Set the StringVars with properly formatted dates
        self.report_from_var.set(DateUtils.date_to_string(start_date))
        self.report_to_var.set(DateUtils.date_to_string(end_date))
        
        # After setting the date range, regenerate the report
        self.generate_report()
    
    def set_all_data_range(self):
        """Set date range to cover all available data"""
        try:
            # Query all records to find actual min and max dates
            self.cursor.execute("SELECT MIN(date), MAX(date) FROM time_logs")
            min_max_dates = self.cursor.fetchone()
            
            if min_max_dates and min_max_dates[0] and min_max_dates[1]:
                min_date_str = min_max_dates[0]
                max_date_str = min_max_dates[1]
                
                print(f"Min date from DB: {min_date_str}, Max date: {max_date_str}")
                
                # Convert both dates to display format consistently
                # Handle both potential formats
                try:
                    if '-' in min_date_str:  # YYYY-MM-DD format
                        min_date = datetime.strptime(min_date_str, DB_DATE_FORMAT).date()
                    else:  # Assume DD/MM/YYYY format
                        min_date = datetime.strptime(min_date_str, DATE_FORMAT).date()
                        
                    if '-' in max_date_str:  # YYYY-MM-DD format
                        max_date = datetime.strptime(max_date_str, DB_DATE_FORMAT).date()
                    else:  # Assume DD/MM/YYYY format
                        max_date = datetime.strptime(max_date_str, DATE_FORMAT).date()
                    
                    # Set the date range using the consistent date format
                    self.report_from_var.set(min_date.strftime(DATE_FORMAT))
                    self.report_to_var.set(max_date.strftime(DATE_FORMAT))
                    
                    # Generate the report
                    self.generate_report()
                    
                except ValueError as e:
                    print(f"Error parsing date: {e}")
                    # Fall back to showing all records using a direct query
                    self.cursor.execute("SELECT COUNT(*) FROM time_logs")
                    count = self.cursor.fetchone()[0]
                    
                    if count > 0:
                        messagebox.showinfo("Date Format Issue", 
                                          f"Found {count} records, but couldn't parse date formats. Showing all records.")
                        
                        # Clear date filters to show all
                        self.report_from_var.set("")
                        self.report_to_var.set("")
                        self.generate_report()
                    else:
                        messagebox.showinfo("No Data", "No records found in the database")
            else:
                # No records found
                messagebox.showinfo("No Data", "No records found in the database")
                
        except Exception as e:
            print(f"Error in set_all_data_range: {str(e)}")
            # Leave the current date range as is
            messagebox.showerror("Error", f"Error retrieving date range: {str(e)}")

    def convert_to_db_date_format(self, date_str):
        """Convert a date string to the database date format.
        Maintained for backward compatibility."""
        return DateUtils.format_date_for_db(date_str)
            
    def convert_date_string_to_date(self, date_str):
        """Convert a date string to a datetime.date object.
        Maintained for backward compatibility."""
        return DateUtils.string_to_date(date_str)

    def set_date_range(self, from_date, to_date, regenerate_report=True):
        """
        Set the date range fields and optionally regenerate the report.
        
        Args:
            from_date: Start date (datetime.date object or string in DATE_FORMAT)
            to_date: End date (datetime.date object or string in DATE_FORMAT)
            regenerate_report: Whether to regenerate the report after setting dates
        """
        try:
            # Convert dates to strings in the correct format if needed
            if isinstance(from_date, datetime.date):
                from_date_str = from_date.strftime(DATE_FORMAT)
            else:
                from_date_str = from_date
                
            if isinstance(to_date, datetime.date):
                to_date_str = to_date.strftime(DATE_FORMAT)
            else:
                to_date_str = to_date
            
            # Update date fields
            self.report_from_var.set(from_date_str)
            self.report_to_var.set(to_date_str)
            
            # Regenerate report if requested
            if regenerate_report:
                self.generate_report()
                
        except Exception as e:
            print(f"Error setting date range: {str(e)}")
            # Keep current values if there's an error

    def format_record_for_treeview(self, record):
        """Format a database record for display in the treeview
        
        Args:
            record: Record tuple from database
            
        Returns:
            list: Formatted record for display
        """
        # Create a mutable copy of the record
        formatted = list(record)
        
        # Convert date from DB format to display format if needed
        if formatted[1] and '-' in formatted[1]:  # If in YYYY-MM-DD format
            formatted[1] = DateUtils.format_date_for_display(formatted[1])
        
        # Format earnings with dollar sign
        formatted[7] = f"${formatted[7]:.2f}"
        
        return formatted

    def create_chart_canvas(self, parent_frame, fig):
        """Create a chart canvas within the parent frame
        
        Args:
            parent_frame: The parent frame to contain the chart
            fig: The matplotlib figure to embed
            
        Returns:
            FigureCanvasTkAgg: The canvas widget
        """
        # Create a frame for the chart container
        chart_container = ttk.Frame(parent_frame)
        chart_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=chart_container)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar
        toolbar_frame = ttk.Frame(parent_frame)
        toolbar_frame.pack(fill=tk.X, padx=5)
        
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        
        return canvas

def main(): 
    root = tk.Tk()
    app = TimeLoggerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 
