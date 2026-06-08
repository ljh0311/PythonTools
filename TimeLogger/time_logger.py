import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import sqlite3
import csv
from datetime import datetime, timedelta, date
import calendar
import re
import matplotlib
matplotlib.use('TkAgg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import Calendar
from date_picker import open_date_picker, add_date_picker_button
from openpyxl.styles import Font
import traceback
import functools
import threading

import report_ai_insights

# Constants
DATE_FORMAT = "%d-%m-%Y"
DB_DATE_FORMAT = "%d-%m-%Y"  # Format for dates stored in the database
DEFAULT_DATE_RANGE = ("01-04-2025", "30-04-2025")  # Fallback dates
# SQLite TEXT dd-mm-yyyy does not sort chronologically; use this in ORDER BY / comparisons.
CHRONO_ORDER_BY_DATE_ASC = (
    "ORDER BY (substr(date, 7, 4) || substr(date, 4, 2) || substr(date, 1, 2))"
)
CHRONO_ORDER_BY_DATE_DESC = (
    "ORDER BY (substr(date, 7, 4) || substr(date, 4, 2) || substr(date, 1, 2)) DESC"
)

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
    def parse_date_string(date_str):
        """Parse supported date strings and return a date object or None."""
        if not date_str:
            return None
        for fmt in (DATE_FORMAT, DB_DATE_FORMAT, "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None
    
    @staticmethod
    def format_date_for_display(date_str):
        """Convert a date string to display format (dd-mm-yyyy)."""
        if not date_str:
            return ""
            
        parsed_date = DateUtils.parse_date_string(date_str)
        if parsed_date:
            return parsed_date.strftime(DATE_FORMAT)
        else:
            return date_str
    
    @staticmethod
    def format_date_for_db(date_str):
        """Convert a date string to database format (dd-mm-yyyy)."""
        if not date_str:
            return date_str
            
        parsed_date = DateUtils.parse_date_string(date_str)
        if parsed_date:
            return parsed_date.strftime(DB_DATE_FORMAT)
        else:
            return date_str
    
    @staticmethod
    def string_to_date(date_str):
        """Convert a date string to a datetime.date object"""
        if not date_str:
            return datetime.now().date()
            
        parsed_date = DateUtils.parse_date_string(date_str)
        if parsed_date:
            return parsed_date
        else:
            return datetime.now().date()
    
    @staticmethod
    def date_to_string(date_obj, for_db=False):
        """Convert a date object to string in the appropriate format"""
        if not isinstance(date_obj, (date, datetime)):
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

    @staticmethod
    def sql_chrono_key(column="date"):
        """Chronological ordering / comparison for TEXT dates stored as dd-mm-yyyy."""
        return f"(substr({column}, 7, 4) || substr({column}, 4, 2) || substr({column}, 1, 2))"

    @staticmethod
    def chrono_sort_bounds(from_str, to_str):
        """Return (low_yyyymmdd, high_yyyymmdd) for SQL comparison, or (None, None)."""
        d1 = DateUtils.parse_date_string((from_str or "").strip())
        d2 = DateUtils.parse_date_string((to_str or "").strip())
        if not d1 or not d2:
            return None, None
        lo, hi = (d1, d2) if d1 <= d2 else (d2, d1)
        return lo.strftime("%Y%m%d"), hi.strftime("%Y%m%d")

    @staticmethod
    def time_logs_where_chrono(from_date, to_date):
        """SQL fragment + params for chronological filter on time_logs.date (dd-mm-yyyy TEXT)."""
        chrono = DateUtils.sql_chrono_key("date")
        params = []
        parts = []
        fd = (from_date or "").strip()
        td = (to_date or "").strip()
        if fd and td:
            lo, hi = DateUtils.chrono_sort_bounds(fd, td)
            if lo and hi:
                parts.append(f" AND ({chrono} >= ? AND {chrono} <= ?)")
                params.extend([lo, hi])
        elif fd:
            d = DateUtils.parse_date_string(fd)
            if d:
                parts.append(f" AND {chrono} >= ?")
                params.append(d.strftime("%Y%m%d"))
        elif td:
            d = DateUtils.parse_date_string(td)
            if d:
                parts.append(f" AND {chrono} <= ?")
                params.append(d.strftime("%Y%m%d"))
        return "".join(parts), params

    @staticmethod
    def migrate_stored_dates_to_db_format(cursor, conn):
        """Rewrite mixed-format date TEXT columns to dd-mm-yyyy (DB_DATE_FORMAT)."""
        updates = 0
        for table, col, pk in (
            ("time_logs", "date", "id"),
            ("payroll_periods", "start_date", "id"),
            ("payroll_periods", "end_date", "id"),
        ):
            cursor.execute(
                f"SELECT {pk}, {col} FROM {table} WHERE {col} IS NOT NULL AND TRIM({col}) != ''"
            )
            for pk_val, raw in cursor.fetchall():
                parsed = DateUtils.parse_date_string(str(raw).strip())
                if not parsed:
                    continue
                normalized = parsed.strftime(DB_DATE_FORMAT)
                if normalized != str(raw).strip():
                    cursor.execute(
                        f"UPDATE {table} SET {col} = ? WHERE {pk} = ?",
                        (normalized, pk_val),
                    )
                    updates += 1
        if updates:
            conn.commit()
            print(f"Normalized {updates} date value(s) to {DB_DATE_FORMAT} in database")

    @staticmethod
    def min_max_dates_in_time_logs(cursor):
        """Chronological min/max of time_logs.date (parses mixed legacy TEXT)."""
        cursor.execute(
            "SELECT date FROM time_logs WHERE date IS NOT NULL AND TRIM(date) != ''"
        )
        parsed = []
        for (s,) in cursor.fetchall():
            d = DateUtils.parse_date_string(str(s).strip())
            if d:
                parsed.append(d)
        if not parsed:
            return None, None
        return min(parsed), max(parsed)


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
            # Build query
            query = f"SELECT * FROM {table} WHERE 1=1"
            params = []

            if table == "time_logs":
                clause, extra = DateUtils.time_logs_where_chrono(from_date or "", to_date or "")
                query += clause
                params.extend(extra)
            else:
                db_from_date = DateUtils.format_date_for_db(from_date) if from_date else None
                db_to_date = DateUtils.format_date_for_db(to_date) if to_date else None
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
        self.root.geometry("1280x820")
        self.root.resizable(True, True)
        
        # Configure matplotlib to avoid memory leaks
        plt.rcParams['figure.max_open_warning'] = 10
        matplotlib.rcParams['figure.figsize'] = [12, 8]
        
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

    def _validate_time_entry_chars(self, proposed):
        """Allow only partial HH:MM typing states."""
        if proposed == "":
            return True
        return bool(re.fullmatch(r"\d{0,2}:?\d{0,2}", proposed))

    def normalize_time_text(self, raw_value):
        """Normalize flexible time input into HH:MM."""
        value = (raw_value or "").strip()
        if not value:
            raise ValueError("Time cannot be empty")

        # Accept compact forms like 930 or 0830.
        if value.isdigit():
            if len(value) in (1, 2):
                hours = int(value)
                minutes = 0
            elif len(value) == 3:
                hours = int(value[0])
                minutes = int(value[1:])
            elif len(value) == 4:
                hours = int(value[:2])
                minutes = int(value[2:])
            else:
                raise ValueError("Use HH:MM format (example: 09:30)")
        else:
            match = re.fullmatch(r"(\d{1,2}):(\d{1,2})", value)
            if not match:
                raise ValueError("Use HH:MM format (example: 09:30)")
            hours = int(match.group(1))
            minutes = int(match.group(2))

        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Time must be between 00:00 and 23:59")

        return f"{hours:02d}:{minutes:02d}"

    def _on_time_entry_focus_out(self, time_var):
        """Normalize time input when user leaves the field."""
        value = (time_var.get() or "").strip()
        if not value:
            return
        try:
            time_var.set(self.normalize_time_text(value))
        except ValueError:
            # Keep user input unchanged; hard validation happens on calculate/save.
            pass

    def _increment_time_var(self, time_var, minutes_delta):
        """Adjust a time field in minute increments via keyboard."""
        try:
            normalized = self.normalize_time_text(time_var.get() or "00:00")
            time_value = datetime.strptime(normalized, "%H:%M")
            updated = time_value + timedelta(minutes=minutes_delta)
            time_var.set(updated.strftime("%H:%M"))
        except ValueError:
            time_var.set("00:00")

    def _bind_time_entry(self, entry_widget, time_var):
        """Attach validation and keyboard helpers to a time entry."""
        validate_cmd = (self.root.register(self._validate_time_entry_chars), "%P")
        entry_widget.configure(validate="key", validatecommand=validate_cmd)
        entry_widget.bind("<FocusOut>", lambda _e, var=time_var: self._on_time_entry_focus_out(var))
        entry_widget.bind("<Up>", lambda _e, var=time_var: (self._increment_time_var(var, 15), "break")[1])
        entry_widget.bind("<Down>", lambda _e, var=time_var: (self._increment_time_var(var, -15), "break")[1])
        
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
        DateUtils.migrate_stored_dates_to_db_format(self.cursor, self.conn)
        
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
            self.cursor.execute(
                "SELECT date, start_time, end_time, break_duration, hourly_rate, total_hours, total_earnings, notes FROM time_logs "
                + CHRONO_ORDER_BY_DATE_ASC
            )
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
        self.cal = Calendar(date_frame, selectmode='day', date_pattern='dd-mm-yyyy', 
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
        self._bind_time_entry(start_entry, self.start_time_var)
        
        # End time
        end_label = ttk.Label(time_section, text="End Time (HH:MM):", font=("Arial", 10, "bold"))
        end_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.end_time_var = tk.StringVar()
        end_entry = ttk.Entry(time_section, textvariable=self.end_time_var, width=12)
        end_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self._bind_time_entry(end_entry, self.end_time_var)

        time_hint = ttk.Label(
            time_section,
            text="Tip: accepts 930 or 9:30. Use Up/Down for ±15 min.",
            font=("Arial", 8)
        )
        time_hint.grid(row=0, column=2, rowspan=2, padx=(10, 5), pady=5, sticky="w")
        
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
        add_date_picker_button(
            date_section, self.from_date_var, self.root, title="Filter — From date"
        ).grid(row=0, column=3, padx=2, pady=5)

        ttk.Label(date_section, text="To:").grid(row=0, column=4, padx=(10, 2), pady=5, sticky="w")
        self.to_date_var = tk.StringVar()
        to_entry = ttk.Entry(date_section, textvariable=self.to_date_var, width=12)
        to_entry.grid(row=0, column=5, padx=2, pady=5, sticky="w")
        add_date_picker_button(
            date_section, self.to_date_var, self.root, title="Filter — To date"
        ).grid(row=0, column=6, padx=2, pady=5)
        
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
        records = self.db_utils.execute_query("SELECT * FROM time_logs " + CHRONO_ORDER_BY_DATE_DESC)
        
        # Insert into treeview
        for record in records:
            formatted_record = self.format_record_for_treeview(record)
            self.tree.insert("", "end", values=formatted_record)

        # Keep current/default sort after reloading data
        self.apply_current_tree_sort()
            
        # Update summary statistics
        self.update_record_summary(records)

    def _tree_sort_key(self, column, raw_value):
        """Build a comparable key for a treeview column value."""
        value = "" if raw_value is None else str(raw_value).strip()

        if column in ("id", "break_duration"):
            try:
                return int(float(value))
            except ValueError:
                return -1

        if column in ("hourly_rate", "total_hours", "total_earnings"):
            cleaned = value.replace("$", "").replace(",", "")
            try:
                return float(cleaned)
            except ValueError:
                return float("-inf")

        if column == "date":
            parsed = DateUtils.parse_date_string(value)
            if parsed:
                return datetime.combine(parsed, datetime.min.time())
            return datetime.min

        if column in ("start_time", "end_time"):
            try:
                return datetime.strptime(value, "%H:%M")
            except ValueError:
                return datetime.min

        return value.lower()

    def update_treeview_sort_headers(self):
        """Update treeview header text to reflect active sort state."""
        arrow = "▼" if self.tree_sort_desc else "▲"
        label_map = {
            "id": "ID",
            "date": "Date",
            "start_time": "Start Time",
            "end_time": "End Time",
            "break_duration": "Break (min)",
            "hourly_rate": "Rate ($/hr)",
            "total_hours": "Hours",
            "total_earnings": "Earnings ($)",
            "notes": "Notes",
        }

        for col, label in label_map.items():
            text = f"{label} {arrow}" if col == self.tree_sort_column else label
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_treeview_by_column(c))

    def sort_treeview_by_column(self, column):
        """Sort treeview rows by a selected column."""
        if self.tree_sort_column == column:
            self.tree_sort_desc = not self.tree_sort_desc
        else:
            self.tree_sort_column = column
            self.tree_sort_desc = (column == "date")

        self.apply_current_tree_sort()

    def apply_current_tree_sort(self):
        """Apply current sorting state to visible treeview rows."""
        if not hasattr(self, "tree"):
            return

        items = []
        for item_id in self.tree.get_children(""):
            values = self.tree.item(item_id, "values")
            value_map = dict(zip(self.tree_columns, values))
            key_value = self._tree_sort_key(self.tree_sort_column, value_map.get(self.tree_sort_column))
            items.append((key_value, item_id))

        items.sort(key=lambda x: x[0], reverse=self.tree_sort_desc)

        for index, (_, item_id) in enumerate(items):
            self.tree.move(item_id, "", index)

        self.update_treeview_sort_headers()
    
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
        
        # Determine date range from records (chronological, not lexicographic on strings)
        try:
            parsed_dates = []
            for record in records:
                d = DateUtils.parse_date_string(str(record[1]).strip()) if record[1] else None
                if d:
                    parsed_dates.append(d)
            if parsed_dates:
                lo, hi = min(parsed_dates), max(parsed_dates)
                self.date_range_var.set(
                    f"{lo.strftime(DATE_FORMAT)} to {hi.strftime(DATE_FORMAT)}"
                )
            else:
                self.date_range_var.set("All dates")
        except (ValueError, TypeError):
            self.date_range_var.set("All dates")
    
    def create_payroll_tab(self):
        """Create a tab for managing payroll periods (form + list, date pickers)."""
        payroll_frame = ttk.Frame(self.notebook)
        self.notebook.add(payroll_frame, text="Payroll Periods")

        outer = ttk.Frame(payroll_frame, padding=10)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=2)
        outer.rowconfigure(0, weight=1)

        # --- Left: create / plan ---
        add_frame = ttk.LabelFrame(outer, text="New payroll period", padding=12)
        add_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)
        add_frame.columnconfigure(1, weight=1)

        ttk.Label(
            add_frame,
            text="Use the calendar buttons or type dates as dd-mm-yyyy.",
            foreground="gray",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(add_frame, text="Period name").grid(row=1, column=0, sticky="nw", pady=4)
        self.period_name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.period_name_var, width=28).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4
        )

        ttk.Label(add_frame, text="Period type").grid(row=2, column=0, sticky="nw", pady=4)
        self.period_type_var = tk.StringVar(value="Monthly")
        period_types = ["Monthly", "Bi-weekly", "Weekly", "Yearly", "Custom"]
        type_row = ttk.Frame(add_frame)
        type_row.grid(row=2, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)
        ttk.Combobox(
            type_row,
            textvariable=self.period_type_var,
            values=period_types,
            state="readonly",
            width=18,
        ).pack(side=tk.LEFT)
        ttk.Button(type_row, text="Apply type", command=self.apply_period_type).pack(
            side=tk.LEFT, padx=(10, 0)
        )

        ttk.Label(add_frame, text="Start").grid(row=3, column=0, sticky="nw", pady=4)
        self.period_start_var = tk.StringVar()
        start_row = ttk.Frame(add_frame)
        start_row.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)
        start_row.columnconfigure(0, weight=1)
        ttk.Entry(start_row, textvariable=self.period_start_var, width=14).grid(
            row=0, column=0, sticky="ew"
        )
        add_date_picker_button(
            start_row, self.period_start_var, self.root, title="Payroll start date"
        ).grid(row=0, column=1, padx=(6, 0))

        ttk.Label(add_frame, text="End").grid(row=4, column=0, sticky="nw", pady=4)
        self.period_end_var = tk.StringVar()
        end_row = ttk.Frame(add_frame)
        end_row.grid(row=4, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=4)
        end_row.columnconfigure(0, weight=1)
        ttk.Entry(end_row, textvariable=self.period_end_var, width=14).grid(
            row=0, column=0, sticky="ew"
        )
        add_date_picker_button(
            end_row, self.period_end_var, self.root, title="Payroll end date"
        ).grid(row=0, column=1, padx=(6, 0))

        self.default_period_var = tk.BooleanVar()
        ttk.Checkbutton(
            add_frame,
            text="Set as default (used by “Current Payroll Period” in Reports)",
            variable=self.default_period_var,
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 4))

        ttk.Label(add_frame, text="Bulk generate").grid(row=6, column=0, sticky="nw", pady=4)
        gen_row = ttk.Frame(add_frame)
        gen_row.grid(row=6, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=4)
        self.num_periods_var = tk.IntVar(value=6)
        ttk.Spinbox(gen_row, from_=1, to=24, textvariable=self.num_periods_var, width=6).pack(
            side=tk.LEFT
        )
        ttk.Label(gen_row, text="periods ahead").pack(side=tk.LEFT, padx=(6, 0))

        pattern_frame = ttk.LabelFrame(add_frame, text="Quick presets", padding=8)
        pattern_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(14, 8))

        def set_monthly_pattern():
            self.period_type_var.set("Monthly")
            self.apply_period_type()

        def set_biweekly_pattern():
            self.period_type_var.set("Bi-weekly")
            self.apply_period_type()

        def set_weekly_pattern():
            self.period_type_var.set("Weekly")
            self.apply_period_type()

        def set_yearly_pattern():
            self.period_type_var.set("Yearly")
            self.apply_period_type()

        ttk.Button(pattern_frame, text="Monthly (26th–25th)", command=set_monthly_pattern).grid(
            row=0, column=0, padx=4, pady=4
        )
        ttk.Button(pattern_frame, text="Bi-weekly", command=set_biweekly_pattern).grid(
            row=0, column=1, padx=4, pady=4
        )
        ttk.Button(pattern_frame, text="Weekly", command=set_weekly_pattern).grid(
            row=0, column=2, padx=4, pady=4
        )
        ttk.Button(pattern_frame, text="Yearly", command=set_yearly_pattern).grid(
            row=0, column=3, padx=4, pady=4
        )

        actions = ttk.Frame(add_frame)
        actions.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(
            actions,
            text="Add period",
            command=self.add_payroll_period,
            style="Accent.TButton",
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(actions, text="Generate recurring", command=self.generate_recurring_periods).pack(
            side=tk.LEFT
        )

        # --- Right: saved periods ---
        list_frame = ttk.LabelFrame(outer, text="Saved periods", padding=10)
        list_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)
        list_frame.rowconfigure(1, weight=1)
        list_frame.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(list_frame)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(toolbar, text="Set default", command=self.set_default_period).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(toolbar, text="Delete", command=self.delete_period).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Refresh", command=self.load_payroll_periods).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Use in report", command=self.report_for_period).pack(
            side=tk.LEFT, padx=4
        )

        tree_wrap = ttk.Frame(list_frame)
        tree_wrap.grid(row=1, column=0, sticky="nsew")
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(0, weight=1)

        columns = ("id", "period_name", "start_date", "end_date", "is_default")
        self.period_tree = ttk.Treeview(
            tree_wrap, columns=columns, show="headings", height=18
        )
        self.period_tree.heading("id", text="ID")
        self.period_tree.heading("period_name", text="Name")
        self.period_tree.heading("start_date", text="Start")
        self.period_tree.heading("end_date", text="End")
        self.period_tree.heading("is_default", text="Default")
        self.period_tree.column("id", width=44, anchor="center")
        self.period_tree.column("period_name", width=220)
        self.period_tree.column("start_date", width=100, anchor="center")
        self.period_tree.column("end_date", width=100, anchor="center")
        self.period_tree.column("is_default", width=70, anchor="center")

        period_scroll = ttk.Scrollbar(
            tree_wrap, orient="vertical", command=self.period_tree.yview
        )
        self.period_tree.configure(yscrollcommand=period_scroll.set)
        self.period_tree.grid(row=0, column=0, sticky="nsew")
        period_scroll.grid(row=0, column=1, sticky="ns")

        self.load_payroll_periods()

    def create_report_tab(self):
        """Create the tab for generating reports and visualizations"""
        report_frame = ttk.Frame(self.notebook)
        self.notebook.add(report_frame, text="Reports & Statistics")

        main_container = ttk.Frame(report_frame)
        main_container.pack(fill="both", expand=True, padx=8, pady=6)

        # Compact controls: primary row + optional tab for shortcuts/filters
        options_notebook = ttk.Notebook(main_container)
        options_notebook.pack(fill=tk.X, pady=(0, 4))

        run_tab = ttk.Frame(options_notebook)
        filters_tab = ttk.Frame(options_notebook)
        options_notebook.add(run_tab, text="Report")
        options_notebook.add(filters_tab, text="Shortcuts & filters")

        run_row = ttk.Frame(run_tab)
        run_row.pack(fill=tk.X, padx=6, pady=4)

        ttk.Label(run_row, text="Type:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.report_type_var = tk.StringVar()
        report_types = ["Daily Summary", "Weekly Summary", "Monthly Summary", "Current Payroll Period", "Custom Range"]
        report_type_combo = ttk.Combobox(
            run_row, textvariable=self.report_type_var, values=report_types, state="readonly", width=18
        )
        report_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        report_type_combo.current(0)

        ttk.Label(run_row, text="From:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 2))
        self.report_from_var = tk.StringVar()
        ttk.Entry(run_row, textvariable=self.report_from_var, width=11).pack(side=tk.LEFT, padx=2)
        ttk.Button(run_row, text="📅", width=3, command=lambda: self.show_calendar_popup("report_from")).pack(side=tk.LEFT, padx=1)

        ttk.Label(run_row, text="To:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(8, 2))
        self.report_to_var = tk.StringVar()
        ttk.Entry(run_row, textvariable=self.report_to_var, width=11).pack(side=tk.LEFT, padx=2)
        ttk.Button(run_row, text="📅", width=3, command=lambda: self.show_calendar_popup("report_to")).pack(side=tk.LEFT, padx=1)

        self.comparison_frame = ttk.Frame(run_row)
        self.comparison_frame.pack(side=tk.LEFT, padx=(12, 6))
        self.compare_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.comparison_frame,
            text="Compare previous period",
            variable=self.compare_enabled_var,
            command=self.toggle_comparison,
        ).pack(side=tk.LEFT)

        ttk.Button(run_row, text="Generate Report", command=self.generate_report, style="Accent.TButton").pack(
            side=tk.RIGHT, padx=4, ipadx=6, ipady=2
        )

        fq = ttk.Frame(filters_tab)
        fq.pack(fill=tk.X, padx=6, pady=4)
        quick_specs = [
            ("Today", "today"),
            ("Yesterday", "yesterday"),
            ("This Week", "this_week"),
            ("Last Week", "last_week"),
            ("This Month", "this_month"),
            ("Last Month", "last_month"),
            ("This Year", "this_year"),
            ("Last Year", "last_year"),
        ]
        for i, (label, key) in enumerate(quick_specs):
            ttk.Button(fq, text=label, command=lambda k=key: self.set_quick_date_range(k), width=11).grid(
                row=i // 5, column=i % 5, padx=3, pady=2, sticky="w"
            )
        ttk.Button(fq, text="All Data", command=self.set_all_data_range, style="Accent.TButton", width=11).grid(
            row=1, column=4, padx=3, pady=2, sticky="w"
        )

        filter_row = ttk.Frame(filters_tab)
        filter_row.pack(fill=tk.X, padx=6, pady=(0, 6))
        ttk.Label(filter_row, text="Rate min").pack(side=tk.LEFT, padx=(0, 2))
        self.min_rate_var = tk.StringVar()
        ttk.Entry(filter_row, textvariable=self.min_rate_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(filter_row, text="max").pack(side=tk.LEFT, padx=(10, 2))
        self.max_rate_var = tk.StringVar()
        ttk.Entry(filter_row, textvariable=self.max_rate_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(filter_row, text="Keyword").pack(side=tk.LEFT, padx=(14, 2))
        self.keyword_filter_var = tk.StringVar()
        ttk.Entry(filter_row, textvariable=self.keyword_filter_var, width=24).pack(side=tk.LEFT, padx=4)

        self.report_paned = ttk.Panedwindow(main_container, orient=tk.HORIZONTAL)
        self.report_paned.pack(fill=tk.BOTH, expand=True, pady=(2, 4))

        self.report_stats_nb = ttk.Notebook(self.report_paned)
        self.report_paned.add(self.report_stats_nb, weight=1)

        summary_tab = ttk.Frame(self.report_stats_nb)
        proj_tab = ttk.Frame(self.report_stats_nb)
        ai_tab = ttk.Frame(self.report_stats_nb)
        self.report_stats_nb.add(summary_tab, text="Summary")
        self.report_stats_nb.add(proj_tab, text="Projection")
        self.report_stats_nb.add(ai_tab, text="AI coach")

        summary_tab.columnconfigure(0, weight=1)
        proj_tab.columnconfigure(0, weight=1)
        proj_tab.rowconfigure(0, weight=1)
        ai_tab.columnconfigure(0, weight=1)
        ai_tab.rowconfigure(1, weight=1)

        self._last_ai_ctx = None
        self._report_ai_busy = False

        # Current Period Statistics
        current_stats = ttk.LabelFrame(summary_tab, text="Current period")
        current_stats.grid(row=0, column=0, padx=6, pady=4, sticky="ew")
        
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

        # Earnings projection — dedicated tab for space
        projection_box = ttk.LabelFrame(proj_tab, text="Earnings projection (forward model)")
        projection_box.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        projection_box.columnconfigure(0, weight=1)

        self.stats_projection_headline_var = tk.StringVar(value="—")
        tk.Label(
            projection_box,
            textvariable=self.stats_projection_headline_var,
            font=("Arial", 18, "bold"),
            fg="#1565C0",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 0))
        ttk.Label(
            projection_box,
            text="30 days after report end · weekday work rate × recent $/day (see below)",
            foreground="gray",
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 4))

        self.stats_projection_text = scrolledtext.ScrolledText(
            projection_box,
            height=22,
            width=72,
            wrap=tk.WORD,
            font=("Courier New", 9),
            state="disabled",
        )
        self.stats_projection_text.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        projection_box.rowconfigure(2, weight=1)

        advanced_stats = ttk.LabelFrame(summary_tab, text="Productivity & pay")
        advanced_stats.grid(row=1, column=0, padx=6, pady=4, sticky="ew")

        ttk.Label(advanced_stats, text="Avg. daily earnings:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.stats_daily_earnings_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_daily_earnings_var).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(advanced_stats, text="Hourly rate range:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.stats_rate_range_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_rate_range_var).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(advanced_stats, text="Most productive day:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.stats_productive_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_productive_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(advanced_stats, text="Least productive day:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.stats_least_productive_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_least_productive_var).grid(row=1, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(advanced_stats, text="Peak hours (avg):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.stats_peak_hours_var = tk.StringVar()
        ttk.Label(advanced_stats, textvariable=self.stats_peak_hours_var).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        comparison_stats = ttk.LabelFrame(summary_tab, text="Comparison to previous period")
        comparison_stats.grid(row=2, column=0, padx=6, pady=4, sticky="ew")

        ttk.Label(comparison_stats, text="Hours change:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.compare_hours_var = tk.StringVar()
        self.compare_hours_label = ttk.Label(comparison_stats, textvariable=self.compare_hours_var)
        self.compare_hours_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(comparison_stats, text="Earnings change:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.compare_earnings_var = tk.StringVar()
        self.compare_earnings_label = ttk.Label(comparison_stats, textvariable=self.compare_earnings_var)
        self.compare_earnings_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(comparison_stats, text="Previous hours:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.prev_hours_var = tk.StringVar()
        ttk.Label(comparison_stats, textvariable=self.prev_hours_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(comparison_stats, text="Previous earnings:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.prev_earnings_var = tk.StringVar()
        ttk.Label(comparison_stats, textvariable=self.prev_earnings_var).grid(row=1, column=3, padx=5, pady=5, sticky="w")

        trend_frame = ttk.LabelFrame(summary_tab, text="Performance trends")
        trend_frame.grid(row=3, column=0, padx=6, pady=4, sticky="ew")

        ttk.Label(trend_frame, text="Hours trend:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.hours_trend_var = tk.StringVar()
        ttk.Label(trend_frame, textvariable=self.hours_trend_var).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(trend_frame, text="Earnings trend:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.earnings_trend_var = tk.StringVar()
        ttk.Label(trend_frame, textvariable=self.earnings_trend_var).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(trend_frame, text="Rate trend:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.rate_trend_var = tk.StringVar()
        ttk.Label(trend_frame, textvariable=self.rate_trend_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(trend_frame, text="Productivity:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.productivity_var = tk.StringVar()
        ttk.Label(trend_frame, textvariable=self.productivity_var).grid(row=1, column=3, padx=5, pady=5, sticky="w")

        ai_hdr = ttk.Frame(ai_tab)
        ai_hdr.grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        ttk.Label(
            ai_hdr,
            text="Habit notes & 2-week planning. Optional: run Ollama locally; set TIMELOGGER_OLLAMA_URL / TIMELOGGER_OLLAMA_MODEL.",
            wraplength=520,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ai_hdr, text="Refresh insights", command=self.refresh_report_ai_insights).pack(side=tk.RIGHT, padx=4)

        self.report_ai_text = scrolledtext.ScrolledText(
            ai_tab, height=16, wrap=tk.WORD, font=("Segoe UI", 10), state="disabled"
        )
        self.report_ai_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        # Charts (right pane — no fixed min size so the paned window can grow charts)
        self.chart_frame = ttk.LabelFrame(self.report_paned, text="Charts")
        self.report_paned.add(self.chart_frame, weight=5)

        chart_controls = ttk.Frame(self.chart_frame)
        chart_controls.pack(fill="x", padx=8, pady=6)

        ttk.Label(chart_controls, text="Chart Type:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.chart_type_var = tk.StringVar(value="Bar Chart")
        chart_types = ["Bar Chart", "Line Chart", "Pie Chart", "Weekly Distribution"]
        chart_type_combo = ttk.Combobox(
            chart_controls, textvariable=self.chart_type_var, values=chart_types, state="readonly", width=20
        )
        chart_type_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(chart_controls, text="Apply", command=lambda: self.update_chart_type(), style="TButton").pack(
            side=tk.LEFT, padx=5
        )

        self.chart_notebook = ttk.Notebook(self.chart_frame)
        self.chart_notebook.pack(fill="both", expand=True, padx=5, pady=4)

        self.bar_chart_frame = ttk.Frame(self.chart_notebook)
        self.line_chart_frame = ttk.Frame(self.chart_notebook)
        self.pie_chart_frame = ttk.Frame(self.chart_notebook)
        self.weekly_chart_frame = ttk.Frame(self.chart_notebook)

        self.chart_notebook.add(self.bar_chart_frame, text="Bar")
        self.chart_notebook.add(self.line_chart_frame, text="Line")
        self.chart_notebook.add(self.pie_chart_frame, text="Pie")
        self.chart_notebook.add(self.weekly_chart_frame, text="Weekly")

        export_frame = ttk.Frame(main_container)
        export_frame.pack(fill="x", pady=(6, 4))

        export_label = ttk.Label(export_frame, text="Export & Reports:", font=("Arial", 10, "bold"))
        export_label.pack(side=tk.LEFT, padx=(0, 10))

        export_buttons = [
            ("Open CSV File", self.open_csv_file, "TButton"),
            ("Export to CSV", self.export_to_csv, "TButton"),
            ("Export to Excel", self.export_to_excel, "TButton"),
            ("Save PDF Report", self.export_to_pdf, "TButton"),
            ("Overview Report", self.show_overview_report, "Accent.TButton"),
        ]

        for text, cmd, style in export_buttons:
            ttk.Button(export_frame, text=text, command=cmd, style=style).pack(side=tk.LEFT, padx=5)
    
    def create_treeview(self, parent):
        """Create a treeview widget for displaying time log records"""
        # Frame to contain the treeview and scrollbar
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create the treeview
        self.tree_columns = ("id", "date", "start_time", "end_time", "break_duration",
                             "hourly_rate", "total_hours", "total_earnings", "notes")
        self.tree_sort_column = "date"
        self.tree_sort_desc = True
        self.tree = ttk.Treeview(tree_frame, columns=self.tree_columns, show="headings")
        
        # Configure column headings
        self.update_treeview_sort_headers()
        
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
            start_time = self.normalize_time_text(self.start_time_var.get())
            end_time = self.normalize_time_text(self.end_time_var.get())
            self.start_time_var.set(start_time)
            self.end_time_var.set(end_time)
            
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
        start_time = self.normalize_time_text(self.start_time_var.get())
        end_time = self.normalize_time_text(self.end_time_var.get())
        self.start_time_var.set(start_time)
        self.end_time_var.set(end_time)
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

        # Build query: compare chronologically (TEXT dd-mm-yyyy is not lexically ordered by time)
        query = "SELECT * FROM time_logs WHERE 1=1"
        params = []
        clause, extra = DateUtils.time_logs_where_chrono(from_date, to_date)
        query += clause
        params.extend(extra)

        query += " " + CHRONO_ORDER_BY_DATE_DESC
        
        # Execute query
        self.cursor.execute(query, params)
        records = self.cursor.fetchall()
        
        # Insert into treeview
        for record in records:
            formatted_record = self.format_record_for_treeview(record)
            self.tree.insert("", "end", values=formatted_record)

        # Keep current/default sort for filtered results too
        self.apply_current_tree_sort()
            
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
        
        # Convert date for display
        try:
            if record[1]:
                parsed = DateUtils.parse_date_string(str(record[1]).strip())
                display_date = parsed.strftime(DATE_FORMAT) if parsed else record[1]
            else:
                display_date = record[1]
        except (ValueError, TypeError):
            display_date = record[1]
        
        # Create edit form
        edit_frame = ttk.Frame(edit_window, padding=10)
        edit_frame.pack(fill="both", expand=True)
        edit_frame.columnconfigure(1, weight=1)
        
        # Date
        ttk.Label(edit_frame, text="Date (dd-mm-yyyy):").grid(row=0, column=0, sticky="w", pady=5)
        date_var = tk.StringVar(value=display_date)
        date_row = ttk.Frame(edit_frame)
        date_row.grid(row=0, column=1, sticky="ew", pady=5)
        date_row.columnconfigure(0, weight=1)
        ttk.Entry(date_row, textvariable=date_var).grid(row=0, column=0, sticky="ew")
        add_date_picker_button(
            date_row, date_var, edit_window, title="Edit — work date"
        ).grid(row=0, column=1, padx=(6, 0))
        
        # Start time
        ttk.Label(edit_frame, text="Start Time (HH:MM):").grid(row=1, column=0, sticky="w", pady=5)
        start_var = tk.StringVar(value=record[2])
        start_entry = ttk.Entry(edit_frame, textvariable=start_var)
        start_entry.grid(row=1, column=1, sticky="ew", pady=5)
        self._bind_time_entry(start_entry, start_var)
        
        # End time
        ttk.Label(edit_frame, text="End Time (HH:MM):").grid(row=2, column=0, sticky="w", pady=5)
        end_var = tk.StringVar(value=record[3])
        end_entry = ttk.Entry(edit_frame, textvariable=end_var)
        end_entry.grid(row=2, column=1, sticky="ew", pady=5)
        self._bind_time_entry(end_entry, end_var)
        
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
                normalized_start = self.normalize_time_text(start_var.get())
                normalized_end = self.normalize_time_text(end_var.get())
                start_var.set(normalized_start)
                end_var.set(normalized_end)

                self.cursor.execute('''
                    UPDATE time_logs
                    SET date=?, start_time=?, end_time=?, break_duration=?,
                        hourly_rate=?, total_hours=?, total_earnings=?, notes=?
                    WHERE id=?
                ''', (
                    DateUtils.format_date_for_db(date_var.get()),
                    normalized_start, normalized_end, break_var.get(),
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
                normalized_start = self.normalize_time_text(start_var.get())
                normalized_end = self.normalize_time_text(end_var.get())
                start_var.set(normalized_start)
                end_var.set(normalized_end)
                start_dt = datetime.strptime(normalized_start, "%H:%M")
                end_dt = datetime.strptime(normalized_end, "%H:%M")
                
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
            print(f"Original dates - From: {from_date}, To: {to_date}")

            from_parsed = DateUtils.parse_date_string(str(from_date).strip())
            to_parsed = DateUtils.parse_date_string(str(to_date).strip())
            if not from_parsed or not to_parsed:
                messagebox.showwarning(
                    "Invalid Dates",
                    "Could not read the From/To dates. Use dd-mm-yyyy (e.g. 26-04-2026).",
                )
                return

            from_date = from_parsed.strftime(DATE_FORMAT)
            to_date = to_parsed.strftime(DATE_FORMAT)
            self.report_from_var.set(from_date)
            self.report_to_var.set(to_date)

            db_from_date = from_parsed.strftime(DB_DATE_FORMAT)
            db_to_date = to_parsed.strftime(DB_DATE_FORMAT)
            print(f"Database dates - From: {db_from_date}, To: {db_to_date}")

            lo, hi = DateUtils.chrono_sort_bounds(from_date, to_date)
            if not lo or not hi:
                messagebox.showwarning("Invalid Dates", "Could not build date range for query.")
                return

            chrono = DateUtils.sql_chrono_key("date")
            query = f"""
                SELECT date, start_time, end_time, break_duration, hourly_rate, total_hours, total_earnings, notes
                FROM time_logs
                WHERE ({chrono} >= ? AND {chrono} <= ?)
            """
            params = [lo, hi]

            # Add rate filter if specified
            min_rate = self.min_rate_var.get().strip()
            max_rate = self.max_rate_var.get().strip()
            keyword_filter = self.keyword_filter_var.get().strip()
            
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
                
            query += " " + CHRONO_ORDER_BY_DATE_ASC
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
                    self.cursor.execute(
                        "SELECT DISTINCT date FROM time_logs " + CHRONO_ORDER_BY_DATE_ASC
                    )
                    all_dates = self.cursor.fetchall()
                    print(f"Available dates in database: {all_dates}")
                    
                    # Show a more informative message to the user with suggestion
                    date_list = ", ".join([d[0] for d in all_dates])
                    messagebox.showinfo("No Data For Selected Period", 
                                       f"No records found for the period {from_date} to {to_date}.\n\n"
                                       f"The database contains {count} records with dates: {date_list}\n\n"
                                       f"Try the 'Shortcuts & filters' tab, then All Data, to view all records.")
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
            summary_query = f"""
                SELECT date, SUM(total_hours) as hours, SUM(total_earnings) as earnings, AVG(hourly_rate) as avg_rate
                FROM time_logs
                WHERE ({chrono} >= ? AND {chrono} <= ?)
            """

            summary_params = [lo, hi]
            
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
                
            summary_query += (
                " GROUP BY date ORDER BY "
                "(substr(date, 7, 4) || substr(date, 4, 2) || substr(date, 1, 2))"
            )
            
            self.cursor.execute(summary_query, summary_params)
            data = self.cursor.fetchall()
            
            if not data:
                # If no data, try a fallback query to get all records from any date
                print("No aggregated data found. Using fallback query for all records.")
                self.cursor.execute("""
                    SELECT date, SUM(total_hours) as hours, SUM(total_earnings) as earnings, AVG(hourly_rate) as avg_rate
                    FROM time_logs 
                    GROUP BY date
                    """ + " ORDER BY (substr(date, 7, 4) || substr(date, 4, 2) || substr(date, 1, 2))"
                )
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
            if most_productive_date and most_productive_date != "N/A":
                most_productive_date = DateUtils.format_date_for_display(str(most_productive_date))

            # Convert least productive date to display format if needed
            if least_productive_date and least_productive_date != "N/A":
                least_productive_date = DateUtils.format_date_for_display(str(least_productive_date))
            
            # Calculate projected monthly earnings using recent trend + expected workdays.
            daily_earnings_data = []
            for row in data:
                parsed_date = DateUtils.parse_date_string(row[0])
                if parsed_date:
                    daily_earnings_data.append((parsed_date, float(row[2] or 0)))

            proj = self.compute_earnings_projection(
                daily_earnings_data=daily_earnings_data,
                period_start=from_date_obj,
                period_end=to_date_obj,
                recent_window_days=28,
                projection_days=30,
            )
            projected_monthly = proj["total"]

            self.stats_projection_headline_var.set(f"${projected_monthly:,.2f}")
            detail = "\n".join(proj["summary_lines"] + [""] + proj["weekday_lines"])
            self.stats_projection_text.configure(state="normal")
            self.stats_projection_text.delete("1.0", tk.END)
            self.stats_projection_text.insert(tk.END, detail)
            self.stats_projection_text.configure(state="disabled")

            self.stats_hours_var.set(f"{total_hours:.2f}")
            self.stats_earnings_var.set(f"${total_earnings:.2f}")
            self.stats_avg_hours_var.set(f"{avg_daily_hours:.2f}")
            self.stats_avg_rate_var.set(f"${avg_rate:.2f}")
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

            self._last_ai_ctx = {
                "from_date": from_date,
                "to_date": to_date,
                "daily_rows": list(data),
                "total_hours": float(total_hours),
                "total_earnings_value": float(total_earnings),
                "work_days": int(work_days),
                "period_days": int(period_days),
                "avg_daily_hours": float(avg_daily_hours),
                "avg_daily_earnings_value": float(avg_daily_earnings),
                "avg_rate_value": float(avg_rate),
                "most_productive": self.stats_productive_var.get(),
                "least_productive": self.stats_least_productive_var.get(),
                "peak_hours": peak_hours,
                "hours_trend": self.hours_trend_var.get(),
                "earnings_trend": self.earnings_trend_var.get(),
                "rate_trend": self.rate_trend_var.get(),
                "productivity_trend": self.productivity_var.get(),
                "projected_total": float(projected_monthly),
                "projection_detail": detail,
                "compare_enabled": bool(self.compare_enabled_var.get()),
                "compare_hours": self.compare_hours_var.get(),
                "compare_earnings": self.compare_earnings_var.get(),
                "prev_hours": self.prev_hours_var.get(),
                "prev_earnings": self.prev_earnings_var.get(),
            }
            report_ai_insights.normalize_context(self._last_ai_ctx)
            self._start_report_ai_thread()

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

    def refresh_report_ai_insights(self):
        """Regenerate AI / heuristic coaching from the last successful report."""
        if not getattr(self, "_last_ai_ctx", None):
            messagebox.showinfo("AI coach", "Generate a report first.")
            return
        if getattr(self, "_report_ai_busy", False):
            return
        self._start_report_ai_thread()

    def _start_report_ai_thread(self):
        ctx = getattr(self, "_last_ai_ctx", None)
        if not ctx:
            return
        if getattr(self, "_report_ai_busy", False):
            return
        self._report_ai_busy = True
        if hasattr(self, "report_ai_text"):
            self.report_ai_text.configure(state="normal")
            self.report_ai_text.delete("1.0", tk.END)
            self.report_ai_text.insert(tk.END, "Generating insights…")
            self.report_ai_text.configure(state="disabled")

        def worker():
            try:
                body, foot = report_ai_insights.generate_insights(ctx)
                text = f"{body}\n\n{foot}"
            except Exception as e:
                text = report_ai_insights.heuristic_insights(ctx)
                text = f"{text}\n\n— Source: built-in rules (error: {e}) —"
            self.root.after(0, functools.partial(self._finish_report_ai, text))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_report_ai(self, text: str):
        self._report_ai_busy = False
        if hasattr(self, "report_ai_text"):
            self.report_ai_text.configure(state="normal")
            self.report_ai_text.delete("1.0", tk.END)
            self.report_ai_text.insert(tk.END, text)
            self.report_ai_text.configure(state="disabled")

    def _expected_weekday_work_probability(self, weekday, period_start, period_end, worked_weekday_counts):
        """Estimate work probability for a weekday from observed period behavior."""
        weekday_occurrences = 0
        current_day = period_start
        while current_day <= period_end:
            if current_day.weekday() == weekday:
                weekday_occurrences += 1
            current_day += timedelta(days=1)

        if weekday_occurrences <= 0:
            return 0.0
        return worked_weekday_counts.get(weekday, 0) / weekday_occurrences

    @staticmethod
    def _weekday_slots_in_range(weekday, period_start, period_end):
        n = 0
        cur = period_start
        while cur <= period_end:
            if cur.weekday() == weekday:
                n += 1
            cur += timedelta(days=1)
        return n

    def compute_earnings_projection(
        self,
        daily_earnings_data,
        period_start,
        period_end,
        recent_window_days=28,
        projection_days=30,
    ):
        """
        Project earnings for projection_days immediately after period_end, and return
        a breakdown for the UI (recent window, weekday work rates, dollar averages).
        """
        empty = {
            "total": 0.0,
            "summary_lines": [
                "Not enough data: need at least one day with earnings in the report range.",
            ],
            "weekday_lines": [],
        }
        if not daily_earnings_data or period_end < period_start:
            return empty

        sorted_data = sorted(daily_earnings_data, key=lambda item: item[0])
        overall_avg = sum(earnings for _, earnings in sorted_data) / len(sorted_data)

        latest_date = sorted_data[-1][0]
        recent_cutoff = latest_date - timedelta(days=max(1, recent_window_days) - 1)

        recent_earnings = []
        worked_weekday_counts = {i: 0 for i in range(7)}
        recent_weekday_earnings = {i: [] for i in range(7)}

        for work_date, earnings in sorted_data:
            weekday = work_date.weekday()
            worked_weekday_counts[weekday] += 1

            if work_date >= recent_cutoff:
                recent_earnings.append(earnings)
                recent_weekday_earnings[weekday].append(earnings)

        baseline_recent_avg = (
            sum(recent_earnings) / len(recent_earnings) if recent_earnings else overall_avg
        )

        projected_total = 0.0
        for offset in range(1, max(1, projection_days) + 1):
            target_day = period_end + timedelta(days=offset)
            weekday = target_day.weekday()

            work_probability = self._expected_weekday_work_probability(
                weekday, period_start, period_end, worked_weekday_counts
            )
            weekday_recent_values = recent_weekday_earnings.get(weekday, [])
            weekday_trend_earnings = (
                sum(weekday_recent_values) / len(weekday_recent_values)
                if weekday_recent_values
                else baseline_recent_avg
            )

            projected_total += work_probability * weekday_trend_earnings

        horizon_start = period_end + timedelta(days=1)
        horizon_end = period_end + timedelta(days=projection_days)
        recent_start = recent_cutoff
        recent_end = latest_date

        day_names = list(calendar.day_name)
        weekday_lines = []
        for wd in range(7):
            p = self._expected_weekday_work_probability(
                wd, period_start, period_end, worked_weekday_counts
            )
            slots = self._weekday_slots_in_range(wd, period_start, period_end)
            wcount = worked_weekday_counts.get(wd, 0)
            rv = recent_weekday_earnings.get(wd, [])
            ravg = sum(rv) / len(rv) if rv else baseline_recent_avg
            if rv:
                src = f"{len(rv)} sample(s) in last {recent_window_days}d window"
            else:
                src = "no samples; uses recent overall avg"
            weekday_lines.append(
                f"{day_names[wd]:9}  P(work) {p:.0%}  ({wcount}/{slots} logged days in report)  "
                f"${ravg:.2f}/day when working  ({src})"
            )

        summary_lines = [
            "What this is",
            f"• Adds expected earnings for the {projection_days} days right after your report end "
            f"({period_end.strftime(DATE_FORMAT)}), not a full calendar month.",
            "• Each future day = P(you work that weekday in the report) × (avg earnings on that weekday in the recent window, or recent overall avg).",
            "",
            "Inputs",
            f"• Report range: {period_start.strftime(DATE_FORMAT)} → {period_end.strftime(DATE_FORMAT)}",
            f"• Recent window: {recent_start.strftime(DATE_FORMAT)} → {recent_end.strftime(DATE_FORMAT)} "
            f"({recent_window_days} days ending on the latest day in this report)",
            f"• Avg earnings per reported day (full range): ${overall_avg:.2f}",
            f"• Avg earnings per day in recent window: ${baseline_recent_avg:.2f}",
            f"• Horizon summed: {horizon_start.strftime(DATE_FORMAT)} → {horizon_end.strftime(DATE_FORMAT)}",
            "",
            "By weekday",
        ]

        return {
            "total": projected_total,
            "summary_lines": summary_lines,
            "weekday_lines": weekday_lines,
        }

    def calculate_projected_monthly_earnings(
        self, daily_earnings_data, period_start, period_end, recent_window_days=28, projection_days=30
    ):
        """Backward-compatible: return only the projected total (same model as compute_earnings_projection)."""
        return self.compute_earnings_projection(
            daily_earnings_data,
            period_start,
            period_end,
            recent_window_days=recent_window_days,
            projection_days=projection_days,
        )["total"]
    
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
            
            prev_lo, prev_hi = DateUtils.chrono_sort_bounds(prev_from_date, prev_to_date)
            chrono = DateUtils.sql_chrono_key("date")
            query = f'''
                SELECT SUM(total_hours) as hours, SUM(total_earnings) as earnings
                FROM time_logs 
                WHERE ({chrono} >= ? AND {chrono} <= ?)
            '''
            if not prev_lo or not prev_hi:
                return
            self.cursor.execute(query, (prev_lo, prev_hi))
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
                cur_lo, cur_hi = DateUtils.chrono_sort_bounds(current_from_date, current_to_date)
                if not cur_lo or not cur_hi:
                    return
                self.cursor.execute(query, (cur_lo, cur_hi))
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
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), dpi=100)
        
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
                    d = DateUtils.parse_date_string(str(date_str).strip())
                    date_objects.append(d if d else date.min)
                
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
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), dpi=100)
            
            # Set style for line charts
            plt.rcParams.update({'font.size': 10})  # Reduced font size for better fit
            
            # Sort by date for proper line progression
            if not df.empty:
                try:
                    # Convert date strings to datetime objects for proper sorting
                    # Handle both date formats (DB and display)
                    date_objects = []
                    for date_str in df['date']:
                        d = DateUtils.parse_date_string(str(date_str).strip())
                        if d:
                            date_objects.append(d)
                        else:
                            date_objects.append(str(date_str))
                    
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
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 7), dpi=100)
            
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
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), dpi=100)
            
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
                            date_obj = DateUtils.parse_date_string(str(date_str).strip())
                            if not date_obj:
                                raise ValueError("unparseable")

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
            clause, extra = DateUtils.time_logs_where_chrono(from_date, to_date)
            query += clause
            params.extend(extra)

            query += " " + CHRONO_ORDER_BY_DATE_DESC
            
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
            clause, extra = DateUtils.time_logs_where_chrono(from_date, to_date)
            query += clause
            params.extend(extra)

            query += " " + CHRONO_ORDER_BY_DATE_DESC
            
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
                datetime.strptime(start_date, DATE_FORMAT)
                datetime.strptime(end_date, DATE_FORMAT)
            except ValueError:
                messagebox.showwarning("Invalid Date Format", "Please use dd-mm-yyyy format for dates.")
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
                start_date = datetime.strptime(start_date_str, DATE_FORMAT)
                end_date = datetime.strptime(end_date_str, DATE_FORMAT)
            except ValueError:
                messagebox.showwarning("Invalid Date Format", "Please use dd-mm-yyyy format for dates.")
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
                
                # Generate readable, date-based period names for all recurring periods.
                current_name = self.build_recurring_period_name(base_name, current_start, current_end)
                
                # Insert period
                self.cursor.execute('''
                    INSERT INTO payroll_periods (period_name, start_date, end_date, is_default)
                    VALUES (?, ?, ?, ?)
                ''', (current_name, current_start.strftime(DATE_FORMAT), 
                      current_end.strftime(DATE_FORMAT), 1 if i == 0 and is_default else 0))
            
            # Commit transaction
            self.conn.commit()
            
            messagebox.showinfo("Success", f"Generated {num_periods} payroll periods!")
            self.load_payroll_periods()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Failed to generate payroll periods: {str(e)}")

    def build_recurring_period_name(self, base_name, start_date, end_date):
        """Build a clean recurring period name with an explicit date range."""
        cleaned_base = (base_name or "").strip()

        # Remove existing generated suffixes like "(3)".
        cleaned_base = re.sub(r"\s*\(\d+\)\s*$", "", cleaned_base)

        # Remove any existing date range text so we don't duplicate it.
        cleaned_base = re.sub(
            r"\s+[A-Za-z]{3}\s+\d{1,2}\s*-\s*[A-Za-z]{3}\s+\d{1,2},\s*\d{4}\s*$",
            "",
            cleaned_base
        ).strip()

        # Use selected period type as sensible default if base name is empty.
        if not cleaned_base:
            period_type = (self.period_type_var.get() or "Payroll").strip()
            cleaned_base = f"{period_type} Payroll" if period_type != "Custom" else "Payroll Period"

        range_text = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        return f"{cleaned_base} {range_text}"
    
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
        """Open the shared date picker for a StringVar (reports regenerate on confirm)."""
        if date_var_name == "report_from":
            date_var = self.report_from_var
            title = "Report range — From"
        elif date_var_name == "report_to":
            date_var = self.report_to_var
            title = "Report range — To"
        elif hasattr(self, date_var_name):
            date_var = getattr(self, date_var_name)
            title = date_var_name.replace("_", " ").title()
        else:
            print(f"Error: Unknown date variable identifier: {date_var_name}")
            return
        open_date_picker(self.root, date_var, title=title, on_confirm=self.generate_report)

    def show_overview_report(self):
        """Show a comprehensive overview report in a popup window"""
        try:
            # Get current date range
            from_date = self.report_from_var.get() if self.report_from_var.get() else DEFAULT_DATE_RANGE[0]
            to_date = self.report_to_var.get() if self.report_to_var.get() else DEFAULT_DATE_RANGE[1]

            lo, hi = DateUtils.chrono_sort_bounds(from_date, to_date)
            if not lo or not hi:
                messagebox.showwarning(
                    "Invalid Dates",
                    "Could not read the date range for the overview. Use dd-mm-yyyy.",
                )
                return

            chrono = DateUtils.sql_chrono_key("date")

            # Create popup window
            overview_window = tk.Toplevel(self.root)
            overview_window.title("Comprehensive Work Overview")
            overview_window.geometry("800x600")
            overview_window.transient(self.root)

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
                WHERE ({chrono} >= ? AND {chrono} <= ?)
            """
            self.cursor.execute(query, (lo, hi))
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
            from_date_obj = DateUtils.parse_date_string(str(from_date).strip())
            to_date_obj = DateUtils.parse_date_string(str(to_date).strip())
            if not from_date_obj or not to_date_obj:
                from_date_obj = DateUtils.string_to_date(from_date)
                to_date_obj = DateUtils.string_to_date(to_date)
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
                WHERE ({chrono} >= ? AND {chrono} <= ?)
                GROUP BY date
                ORDER BY (substr(date, 7, 4) || substr(date, 4, 2) || substr(date, 1, 2))
            """
            self.cursor.execute(query, (lo, hi))
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
                WHERE ({chrono} >= ? AND {chrono} <= ?)
                ORDER BY (substr(date, 7, 4) || substr(date, 4, 2) || substr(date, 1, 2))
            """
            self.cursor.execute(query, (lo, hi))
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
                        date_obj = DateUtils.parse_date_string(str(date_str))
                        if not date_obj:
                            raise ValueError("unparseable")
                        
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
                    
                # Add projected earnings from recent trend + expected workdays.
                daily_earnings_map = {}
                for record in records:
                    work_date = DateUtils.parse_date_string(record[0])
                    if not work_date:
                        continue
                    daily_earnings_map[work_date] = daily_earnings_map.get(work_date, 0.0) + float(record[2] or 0)

                proj_detail = self.compute_earnings_projection(
                    daily_earnings_data=list(daily_earnings_map.items()),
                    period_start=from_date_obj,
                    period_end=to_date_obj,
                    recent_window_days=28,
                    projection_days=30,
                )
                monthly_projection = proj_detail["total"]
                recommendations.append("\n## Projections\n\n")
                recommendations.append(
                    "💼 **Forward earnings estimate**: About **$%.2f** over the **30 days after** your report end, "
                    "using weekday work rates from this period and your **last 28 days** of daily earnings.\n"
                    % monthly_projection
                )
                clip = "\n".join(proj_detail["summary_lines"][:6])
                recommendations.append("\n<details>\n%s\n</details>\n" % clip)
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
                from_date = DEFAULT_DATE_RANGE[0]
                to_date = DEFAULT_DATE_RANGE[1]
            
            # Get data for the report - convert dates to database format
            db_from_date = self.convert_to_db_date_format(from_date)
            db_to_date = self.convert_to_db_date_format(to_date)
            lo, hi = DateUtils.chrono_sort_bounds(from_date, to_date)
            if not lo or not hi:
                messagebox.showinfo("No Data", "Invalid date range for export")
                return

            chrono = DateUtils.sql_chrono_key("date")
            query = f"""
                SELECT date, start_time, end_time, break_duration, hourly_rate, total_hours, total_earnings, notes
                FROM time_logs 
                WHERE ({chrono} >= ? AND {chrono} <= ?)
                {CHRONO_ORDER_BY_DATE_ASC}
            """

            self.cursor.execute(query, (lo, hi))
            records = self.cursor.fetchall()
            
            # Process dates for display in PDF - convert DB format to dd-mm-yyyy
            display_records = []
            for record in records:
                record_list = list(record)
                if record[0]:
                    record_list[0] = DateUtils.format_date_for_display(str(record[0]))
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
                    record[0],  # Date (already in dd-mm-yyyy format)
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
                    date = record[0]  # Date in dd-mm-yyyy format
                    hours = record[5]
                    if date in dates:
                        dates[date] += hours
                    else:
                        dates[date] = hours
                
                # Sort dates - need special handling for dd-mm-yyyy format
                def date_key(date_str):
                    d = DateUtils.parse_date_string(str(date_str))
                    return d or datetime.now().date()
                        
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
        # Get min and max dates from database (chronological, not SQLite MIN/MAX on TEXT)
        min_date, max_date = DateUtils.min_max_dates_in_time_logs(self.cursor)

        if min_date is not None and max_date is not None:
            try:
                print(f"Database date range: {min_date.strftime(DATE_FORMAT)} to {max_date.strftime(DATE_FORMAT)}")
                min_date_display = min_date.strftime(DATE_FORMAT)
                max_date_display = max_date.strftime(DATE_FORMAT)

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
            min_date, max_date = DateUtils.min_max_dates_in_time_logs(self.cursor)

            if min_date is not None and max_date is not None:
                min_date_str = min_date.strftime(DATE_FORMAT)
                max_date_str = max_date.strftime(DATE_FORMAT)

                print(f"Min date from DB: {min_date_str}, Max date: {max_date_str}")

                self.report_from_var.set(min_date_str)
                self.report_to_var.set(max_date_str)

                # Generate the report
                self.generate_report()
            else:
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
        if date_str is None:
            return DateUtils.get_today()
        parsed = DateUtils.parse_date_string(str(date_str).strip())
        if parsed:
            return parsed
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
            if isinstance(from_date, date):
                from_date_str = from_date.strftime(DATE_FORMAT)
            else:
                from_date_str = from_date
                
            if isinstance(to_date, date):
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
        
        # Normalize date to dd-mm-yyyy for the treeview
        if formatted[1]:
            formatted[1] = DateUtils.format_date_for_display(str(formatted[1]))
        
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
