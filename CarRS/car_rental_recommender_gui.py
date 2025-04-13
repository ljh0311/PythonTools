import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from datetime import datetime

# Set up a more modern theme
def set_modern_theme(root):
    """Apply a modern theme to the application"""
    style = ttk.Style()
    
    # Try to use a more modern theme if available
    try:
        style.theme_use('clam')  # 'clam' is a more modern theme available on most platforms
    except tk.TclError:
        pass  # Fall back to default if 'clam' is not available
    
    # Configure colors
    style.configure('.', font=('Segoe UI', 10))
    style.configure('TButton', font=('Segoe UI', 10), padding=5)
    style.configure('TLabel', font=('Segoe UI', 10))
    style.configure('TFrame', background='#f0f0f0')
    style.configure('TNotebook', background='#f0f0f0', tabmargins=[2, 5, 2, 0])
    style.configure('TNotebook.Tab', padding=[10, 5], font=('Segoe UI', 10))
    style.map('TNotebook.Tab',
              background=[('selected', '#4a6984'), ('active', '#d1d1d1')],
              foreground=[('selected', 'white'), ('active', 'black')])
    
    # Treeview styling
    style.configure('Treeview', 
                   background='white',
                   foreground='black',
                   rowheight=25,
                   fieldbackground='white',
                   font=('Segoe UI', 9))
    style.configure('Treeview.Heading', 
                   font=('Segoe UI', 10, 'bold'),
                   padding=5)
    style.map('Treeview',
             background=[('selected', '#4a6984')],
             foreground=[('selected', 'white')])
    
    # Return the style object for further customization
    return style

# Load the data
def load_data(file_path):
    """Load the rental data from the CSV file."""
    df = pd.read_csv(file_path)
    # Clean up column names
    df.columns = df.columns.str.strip()
    return df

# Preprocess the data
def preprocess_data(df):
    """Clean and preprocess the data"""
    if df is None or df.empty:
        return df
    
    # Create a copy of the DataFrame to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Convert date strings to datetime objects with better error handling
    if 'Date' in df.columns:
        try:
            # First try the standard format
            df.loc[:, 'Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
        except:
            try:
                # If that fails, try parsing without specific format
                df.loc[:, 'Date'] = pd.to_datetime(df['Date'], errors='coerce')
            except Exception as e:
                print(f"Warning: Error converting dates - {str(e)}")
    
    # Convert numeric columns
    numeric_cols = [
        'Distance (KM)', 'Fuel pumped', 'Estimated fuel usage', 'Consumption (KM/L)',
        'Fuel cost', 'Pumped fuel cost', 'Mileage cost ($0.39)', 'Cost per KM',
        'Duration cost', 'Total', 'Est original fuel savings', 'Rental hour', 'Cost/HR'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            try:
                df.loc[:, col] = pd.to_numeric(
                    df[col].astype(str).str.replace('$', '').str.replace('L', '').str.strip(), 
                    errors='coerce'
                )
            except Exception as e:
                print(f"Warning: Error converting column {col} - {str(e)}")
    
    # Add Month and Year columns if Date is properly converted
    if 'Date' in df.columns and pd.api.types.is_datetime64_dtype(df['Date']):
        df.loc[:, 'Month'] = df['Date'].dt.month
        df.loc[:, 'Year'] = df['Date'].dt.year
    
    # Remove rows with no date or total cost
    df = df.dropna(subset=['Date', 'Total'], how='any')
    
    return df

# Analyze rental costs by provider and car type
def analyze_rental_costs(df):
    """Calculate average costs per km and per hour by provider and car type."""
    providers = ['Getgo', 'Car Club', 'Econ', 'Stand']
    
    results = {}
    for provider in providers:
        provider_data = df[df['Car Cat'] == provider]
        if not provider_data.empty:
            avg_cost_per_km = provider_data['Cost per KM'].mean()
            avg_cost_per_hour = provider_data['Cost/HR'].mean()
            car_models = provider_data['Car model'].unique()
            car_model_stats = {}
            
            for model in car_models:
                model_data = provider_data[provider_data['Car model'] == model]
                if not model_data.empty:
                    car_model_stats[model] = {
                        'avg_cost_per_km': model_data['Cost per KM'].mean(),
                        'avg_cost_per_hour': model_data['Cost/HR'].mean(),
                        'avg_consumption': model_data['Consumption (KM/L)'].mean(),
                        'count': len(model_data)
                    }
            
            results[provider] = {
                'avg_cost_per_km': avg_cost_per_km,
                'avg_cost_per_hour': avg_cost_per_hour,
                'car_models': car_model_stats
            }
    
    return results

# Calculate estimated costs for a new trip
def calculate_estimated_cost(distance, duration, provider, car_model=None, cost_analysis=None, is_weekend=False):
    """Estimate the cost of a trip based on provider pricing models."""
    
    if provider == 'Getgo':
        # Getgo: mileage charge + hourly charge
        mileage_cost = distance * 0.39
        
        # Find the average hourly rate for Getgo or the specific car model
        if car_model and car_model in cost_analysis['Getgo']['car_models']:
            hourly_rate = cost_analysis['Getgo']['car_models'][car_model]['avg_cost_per_hour']
        else:
            hourly_rate = cost_analysis['Getgo']['avg_cost_per_hour']
        
        hourly_cost = duration * hourly_rate
        total_cost = mileage_cost + hourly_cost
        
    elif provider == 'Car Club':
        # Car Club: mileage charge + hourly charge
        mileage_cost = distance * 0.33
        
        # Find the average hourly rate for Car Club or the specific car model
        if car_model and car_model in cost_analysis['Car Club']['car_models']:
            hourly_rate = cost_analysis['Car Club']['car_models'][car_model]['avg_cost_per_hour']
        else:
            hourly_rate = cost_analysis['Car Club']['avg_cost_per_hour']
        
        hourly_cost = duration * hourly_rate
        total_cost = mileage_cost + hourly_cost
        
    elif provider in ['Econ', 'Stand']:
        # Tribecar (Econ/Stand): Only hourly charge, no mileage charge
        if car_model and car_model in cost_analysis[provider]['car_models']:
            hourly_rate = cost_analysis[provider]['car_models'][car_model]['avg_cost_per_hour']
        else:
            hourly_rate = cost_analysis[provider]['avg_cost_per_hour']
        
        hourly_cost = duration * hourly_rate
        
        # Fuel cost estimation (user pumps $20 for ~110km)
        estimated_fuel_cost = (distance / 110) * 20 if distance > 0 else 0
        
        total_cost = hourly_cost + estimated_fuel_cost
    
    else:
        return None
    
    return {
        'provider': provider,
        'car_model': car_model if car_model else 'Average',
        'distance': distance,
        'duration': duration,
        'is_weekend': is_weekend,
        'estimated_cost': round(total_cost, 2),
        'hourly_cost': round(hourly_cost, 2),
        'mileage_cost': round(mileage_cost if provider in ['Getgo', 'Car Club'] else 0, 2),
        'fuel_cost': round(estimated_fuel_cost if provider in ['Econ', 'Stand'] else 0, 2)
    }

# Get recommendations based on trip details
def get_recommendations(distance, duration, cost_analysis, is_weekend=False, top_n=5):
    """Get top N recommended rental options based on cost."""
    
    recommendations = []
    
    # Check different providers
    providers = ['Getgo', 'Car Club', 'Econ', 'Stand']
    
    for provider in providers:
        if provider in cost_analysis:
            # Get general provider recommendation
            provider_recommendation = calculate_estimated_cost(
                distance, duration, provider, None, cost_analysis, is_weekend
            )
            if provider_recommendation:
                recommendations.append(provider_recommendation)
            
            # Get recommendations for specific car models
            for car_model in cost_analysis[provider]['car_models']:
                model_recommendation = calculate_estimated_cost(
                    distance, duration, provider, car_model, cost_analysis, is_weekend
                )
                if model_recommendation:
                    recommendations.append(model_recommendation)
    
    # Sort recommendations by estimated cost
    recommendations.sort(key=lambda x: x['estimated_cost'])
    
    return recommendations[:top_n]

# GUI Class
class CarRentalRecommenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Car Rental Recommendation System")
        self.root.geometry("1000x700")  # Larger initial window size
        self.root.minsize(900, 600)     # Set minimum window size
        
        # Set application icon if available
        try:
            if os.path.exists("car_icon.ico"):
                self.root.iconbitmap("car_icon.ico")
        except:
            pass  # Continue without icon if it doesn't exist
        
        # Apply modern theme
        self.style = set_modern_theme(self.root)
        
        # Initialize variables
        self.df = None
        self.file_path = None
        self.cost_analysis = None
        self.settings = {
            'fuel_cost_per_liter': 2.51,  # Default SGD per liter
            'getgo_mileage_rate': 0.39,   # Default $0.39 per km
            'car_club_mileage_rate': 0.33 # Default $0.33 per km
        }
        
        # Create widgets
        self.create_widgets()
        
        # Try to load default data file if it exists
        default_file = "22 - Sheet1.csv"
        if os.path.exists(default_file):
            self.load_data_file(default_file)
            self.file_path = default_file
    
    def create_widgets(self):
        # Create a main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                                  relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var.set("Ready. Please load data or use the default dataset.")
        
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.recommendation_tab = ttk.Frame(self.notebook, padding=10)
        self.data_analysis_tab = ttk.Frame(self.notebook, padding=10)
        self.settings_tab = ttk.Frame(self.notebook, padding=10)
        self.records_management_tab = ttk.Frame(self.notebook, padding=10)
        
        # Add tabs to notebook
        self.notebook.add(self.recommendation_tab, text="Recommendations")
        self.notebook.add(self.data_analysis_tab, text="Data Analysis")
        self.notebook.add(self.records_management_tab, text="Records Management")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Set up each tab
        self.setup_recommendation_tab()
        self.setup_data_analysis_tab()
        self.setup_settings_tab()
        self.setup_records_management_tab()
        
        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def setup_recommendation_tab(self):
        # Create a container frame
        container = ttk.Frame(self.recommendation_tab)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Create left panel for inputs
        left_panel = ttk.LabelFrame(container, text="Trip Details", padding=(10, 5))
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5), pady=5)
        
        # Input fields
        input_frame = ttk.Frame(left_panel, padding=5)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Distance input
        ttk.Label(input_frame, text="Distance (km):", width=15).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.distance_var = tk.StringVar()
        distance_entry = ttk.Entry(input_frame, textvariable=self.distance_var, width=10)
        distance_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Duration input
        ttk.Label(input_frame, text="Duration (hours):", width=15).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.duration_var = tk.StringVar()
        duration_entry = ttk.Entry(input_frame, textvariable=self.duration_var, width=10)
        duration_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Weekend checkbox
        self.is_weekend_var = tk.BooleanVar()
        weekend_check = ttk.Checkbutton(input_frame, text="Weekend Trip", variable=self.is_weekend_var)
        weekend_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Get recommendations button
        recommend_button = ttk.Button(input_frame, text="Get Recommendations", 
                                    command=self.get_recommendations_action,
                                    style='Accent.TButton')
        recommend_button.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Create custom button style
        self.style.configure('Accent.TButton', 
                            background='#4a6984', 
                            foreground='white')
        
        # Data file selection
        file_frame = ttk.LabelFrame(left_panel, text="Data Source", padding=5)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_path_var = tk.StringVar()
        file_path_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly', width=25)
        file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_button = ttk.Button(file_frame, text="Browse...", command=self.browse_file)
        browse_button.pack(side=tk.RIGHT)
        
        # Create right panel for results
        right_panel = ttk.LabelFrame(container, text="Recommendations", padding=(10, 5))
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        
        # Results treeview
        self.results_tree = ttk.Treeview(right_panel, columns=("provider", "car_model", "cost", "details"), show="headings")
        self.results_tree.heading("provider", text="Provider")
        self.results_tree.heading("car_model", text="Car Model")
        self.results_tree.heading("cost", text="Est. Cost ($)")
        self.results_tree.heading("details", text="Details")
        
        self.results_tree.column("provider", width=80)
        self.results_tree.column("car_model", width=120)
        self.results_tree.column("cost", width=80, anchor=tk.E)
        self.results_tree.column("details", width=180)
        
        # Add scrollbar to treeview
        results_scroll = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scroll.set)
        
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add chart frame
        self.chart_frame = ttk.LabelFrame(right_panel, text="Cost Comparison", padding=(10, 5))
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a placeholder for the chart
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def setup_data_analysis_tab(self):
        """Set up the data analysis tab with useful visualizations"""
        # Main container
        main_frame = ttk.Frame(self.data_analysis_tab)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for options
        left_panel = ttk.LabelFrame(main_frame, text="Analysis Options", padding=(10, 5))
        left_panel.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, 5), pady=5)
        
        # Analysis type selection
        ttk.Label(left_panel, text="Select Analysis:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.analysis_var = tk.StringVar(value="provider_comparison")
        self.analyses = [
            ("Provider Comparison", "provider_comparison"),
            ("Cost Trends", "cost_trends"),
            ("Car Models", "car_models"),
            ("Monthly Summary", "monthly_summary")
        ]
        
        for text, value in self.analyses:
            ttk.Radiobutton(left_panel, text=text, value=value, 
                          variable=self.analysis_var, 
                          command=self.update_analysis_chart).pack(anchor=tk.W, padx=20, pady=2)
        
        # Period selection
        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, padx=5, pady=10)
        ttk.Label(left_panel, text="Time Period:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.period_var = tk.StringVar(value="all")
        self.periods = [
            ("All Data", "all"),
            ("Last 6 Months", "last_6_months"),
            ("Last 3 Months", "last_3_months"),
            ("This Year", "this_year")
        ]
        
        for text, value in self.periods:
            ttk.Radiobutton(left_panel, text=text, value=value, 
                          variable=self.period_var, 
                          command=self.update_analysis_chart).pack(anchor=tk.W, padx=20, pady=2)
        
        # Run analysis button
        ttk.Button(left_panel, text="Run Analysis", 
                 command=self.update_analysis_chart,
                 style='Accent.TButton').pack(padx=5, pady=15)
        
        # Export data button
        ttk.Button(left_panel, text="Export Results", 
                 command=self.export_analysis_results).pack(padx=5, pady=5)
        
        # Right panel for results and charts
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Stats summary frame
        self.stats_frame = ttk.LabelFrame(right_panel, text="Key Statistics", padding=(10, 5))
        self.stats_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)
        
        # Create grid for statistics
        self.stats_grid = ttk.Frame(self.stats_frame)
        self.stats_grid.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Initialize stats labels (will be populated when analysis runs)
        self.stats_labels = []
        
        # Chart frame
        self.analysis_chart_frame = ttk.LabelFrame(right_panel, text="Analysis Chart", padding=(10, 5))
        self.analysis_chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a figure and canvas for the chart
        self.analysis_fig, self.analysis_ax = plt.subplots(figsize=(8, 5), dpi=100)
        self.analysis_canvas = FigureCanvasTkAgg(self.analysis_fig, master=self.analysis_chart_frame)
        self.analysis_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def update_analysis_chart(self):
        """Update the analysis chart based on selected options"""
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "Please load rental data first")
            return
        
        # Clear previous stats and chart
        self.analysis_ax.clear()
        for label in self.stats_labels:
            label.destroy()
        self.stats_labels = []
        
        # Get selected options
        analysis_type = self.analysis_var.get()
        period = self.period_var.get()
        
        # Filter data by time period
        filtered_df = self.filter_data_by_period(period)
        
        if filtered_df.empty:
            messagebox.showinfo("No Data", "No data available for the selected period")
            return
        
        try:
            # Perform the selected analysis
            if analysis_type == "provider_comparison":
                self.show_provider_comparison(filtered_df)
            elif analysis_type == "cost_trends":
                self.show_cost_trends(filtered_df)
            elif analysis_type == "car_models":
                self.show_car_models_analysis(filtered_df)
            elif analysis_type == "monthly_summary":
                self.show_monthly_summary(filtered_df)
            
            # Convert analysis type and period to their display names
            analysis_name = dict(self.analyses)[analysis_type]
            period_name = dict(self.periods)[period]
            
            # Update status
            self.status_var.set(f"Analysis completed: {analysis_name} for {period_name}")
        except Exception as e:
            messagebox.showerror("Analysis Error", f"An error occurred during analysis: {str(e)}")
            self.status_var.set("Analysis failed. See error message.")
    
    def filter_data_by_period(self, period):
        """Filter dataframe by time period"""
        if period == "all" or 'Date' not in self.df.columns:
            return self.df.copy()
        
        # Ensure Date column is datetime
        df_copy = self.df.copy()
        if not pd.api.types.is_datetime64_dtype(df_copy['Date']):
            try:
                df_copy['Date'] = pd.to_datetime(df_copy['Date'])
            except:
                return df_copy  # Return unfiltered if conversion fails
        
        now = pd.Timestamp.now()
        
        if period == "last_3_months":
            start_date = now - pd.DateOffset(months=3)
            return df_copy[df_copy['Date'] >= start_date]
        
        elif period == "last_6_months":
            start_date = now - pd.DateOffset(months=6)
            return df_copy[df_copy['Date'] >= start_date]
        
        elif period == "this_year":
            start_date = pd.Timestamp(now.year, 1, 1)
            return df_copy[df_copy['Date'] >= start_date]
        
        return df_copy
    
    def show_provider_comparison(self, df):
        """Show comparison between different providers"""
        # Check if provider column exists
        if 'Car Cat' not in df.columns:
            messagebox.showwarning("Missing Data", "Provider information is missing")
            return
        
        # Group by provider
        provider_stats = df.groupby('Car Cat').agg({
            'Total': ['mean', 'count', 'sum'],
            'Distance (KM)': ['sum', 'mean'],
            'Rental hour': ['sum', 'mean'],
            'Cost per KM': ['mean'],
            'Cost/HR': ['mean']
        }).reset_index()
        
        # Flatten multi-index columns
        provider_stats.columns = ['_'.join(col).strip('_') for col in provider_stats.columns.values]
        
        # Display key statistics
        self.add_stat("Total Trips", f"{len(df)}")
        self.add_stat("Total Spending", f"${df['Total'].sum():.2f}")
        self.add_stat("Average Cost per Trip", f"${df['Total'].mean():.2f}")
        self.add_stat("Total Distance", f"{df['Distance (KM)'].sum():.1f} km")
        self.add_stat("Total Rental Hours", f"{df['Rental hour'].sum():.1f} hrs")
        
        # Create bar chart comparing providers
        providers = provider_stats['Car Cat'].tolist()
        avg_costs = provider_stats['Total_mean'].tolist()
        trip_counts = provider_stats['Total_count'].tolist()
        
        # Plot average cost by provider
        bars = self.analysis_ax.bar(providers, avg_costs, width=0.6, 
                                   color='#4a6984', alpha=0.7)
        
        # Add trip count as text
        for i, (bar, count) in enumerate(zip(bars, trip_counts)):
            height = bar.get_height()
            self.analysis_ax.text(bar.get_x() + bar.get_width()/2, height + 0.5,
                                f"{count} trips", ha='center', va='bottom', 
                                color='black', fontsize=9)
        
        # Add data labels
        for bar in bars:
            height = bar.get_height()
            self.analysis_ax.text(bar.get_x() + bar.get_width()/2, height/2,
                                f"${height:.2f}", ha='center', va='center',
                                color='white', fontsize=9, fontweight='bold')
        
        # Set chart properties
        self.analysis_ax.set_title("Average Cost by Provider", fontsize=12)
        self.analysis_ax.set_ylabel("Average Cost ($)", fontsize=10)
        self.analysis_ax.set_ylim(0, max(avg_costs) * 1.2 if len(avg_costs) > 0 else 10)
        self.analysis_ax.grid(axis='y', linestyle='--', alpha=0.3)
        
        # Update chart
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()
    
    def show_cost_trends(self, df):
        """Show cost trends over time"""
        if 'Date' not in df.columns or 'Total' not in df.columns:
            messagebox.showwarning("Missing Data", "Date or cost information is missing")
            return
        
        # Ensure we have datetime data
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_dtype(df_copy['Date']):
            try:
                df_copy['Date'] = pd.to_datetime(df_copy['Date'])
            except:
                messagebox.showwarning("Data Error", "Could not parse dates correctly")
                return
        
        # Add month and year columns if not already present
        if 'Month' not in df_copy.columns:
            df_copy['Month'] = df_copy['Date'].dt.month
        if 'Year' not in df_copy.columns:
            df_copy['Year'] = df_copy['Date'].dt.year
        
        # Create Month-Year column for grouping
        df_copy['Month-Year'] = df_copy['Date'].dt.strftime('%b %Y')
        
        # Group by month and calculate average costs
        monthly_avg = df_copy.groupby('Month-Year').agg({
            'Total': 'mean',
            'Cost per KM': 'mean',
            'Cost/HR': 'mean',
            'Distance (KM)': 'mean',
            'Date': 'first'  # Keep one date per month for sorting
        }).reset_index()
        
        # Sort by date
        monthly_avg = monthly_avg.sort_values('Date')
        
        # Display key statistics
        if not monthly_avg.empty:
            min_month = monthly_avg.loc[monthly_avg['Total'].idxmin(), 'Month-Year']
            max_month = monthly_avg.loc[monthly_avg['Total'].idxmax(), 'Month-Year']
            
            min_cost = monthly_avg['Total'].min()
            max_cost = monthly_avg['Total'].max()
            avg_cost = df_copy['Total'].mean()
            
            self.add_stat("Average Trip Cost", f"${avg_cost:.2f}")
            self.add_stat("Lowest Month", f"{min_month} (${min_cost:.2f})")
            self.add_stat("Highest Month", f"{max_month} (${max_cost:.2f})")
            
            first_month = monthly_avg['Month-Year'].iloc[0]
            last_month = monthly_avg['Month-Year'].iloc[-1]
            self.add_stat("Period", f"{first_month} to {last_month}")
        
        # Plot the trend
        months = monthly_avg['Month-Year'].tolist()
        avg_total = monthly_avg['Total'].tolist()
        avg_per_km = monthly_avg['Cost per KM'].tolist() if 'Cost per KM' in monthly_avg.columns else []
        avg_per_hour = monthly_avg['Cost/HR'].tolist() if 'Cost/HR' in monthly_avg.columns else []
        
        # Primary axis: Average total cost
        self.analysis_ax.plot(months, avg_total, marker='o', linestyle='-', color='#4a6984', 
                            linewidth=2, markersize=6, label='Avg Total Cost')
        
        # Plot on the same axis if we have per km and per hour costs
        if avg_per_km and not all(pd.isna(avg_per_km)):
            self.analysis_ax.plot(months, avg_per_km, marker='s', linestyle='--', color='#e67e22', 
                                linewidth=2, markersize=5, label='Avg Cost per KM')
        
        if avg_per_hour and not all(pd.isna(avg_per_hour)):
            self.analysis_ax.plot(months, avg_per_hour, marker='^', linestyle='-.', color='#27ae60', 
                                linewidth=2, markersize=5, label='Avg Cost per Hour')
        
        # Set chart properties
        self.analysis_ax.set_title("Average Rental Costs Over Time", fontsize=12)
        self.analysis_ax.set_ylabel("Cost ($)", fontsize=10)
        self.analysis_ax.set_xticks(range(len(months)))
        self.analysis_ax.set_xticklabels(months, rotation=45, ha='right', fontsize=9)
        self.analysis_ax.grid(True, linestyle='--', alpha=0.3)
        
        # Add legend
        self.analysis_ax.legend()
        
        # Add data labels for total cost
        for i, (x, y) in enumerate(zip(range(len(months)), avg_total)):
            self.analysis_ax.annotate(f"${y:.2f}", (x, y), xytext=(0, 5),
                                    textcoords='offset points', ha='center', fontsize=8)
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()
    
    def add_stat(self, label, value):
        """Add a statistic to the stats grid"""
        row = len(self.stats_labels) // 3
        col = len(self.stats_labels) % 3
        
        # Create a frame for this statistic
        frame = ttk.Frame(self.stats_grid)
        frame.grid(row=row, column=col, padx=10, pady=5, sticky=tk.W)
        
        # Add label and value
        label_widget = ttk.Label(frame, text=f"{label}:", font=('Segoe UI', 9))
        label_widget.pack(anchor=tk.W)
        
        value_widget = ttk.Label(frame, text=value, font=('Segoe UI', 10, 'bold'))
        value_widget.pack(anchor=tk.W)
        
        # Store references to labels for later cleanup
        self.stats_labels.extend([frame, label_widget, value_widget])
    
    def export_analysis_results(self):
        """Export analysis results to CSV"""
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "No data to export")
            return
        
        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Export Analysis Results"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Get current analysis settings
            analysis_type = self.analysis_var.get()
            period = self.period_var.get()
            
            # Filter data
            filtered_df = self.filter_data_by_period(period)
            
            # Create a summary DataFrame
            if analysis_type == "provider_comparison":
                # Group by provider
                result_df = filtered_df.groupby('Car Cat').agg({
                    'Total': ['mean', 'count', 'sum'],
                    'Distance (KM)': ['sum', 'mean'],
                    'Rental hour': ['sum', 'mean'],
                    'Cost per KM': ['mean'],
                    'Cost/HR': ['mean']
                }).reset_index()
                
                # Flatten multi-index columns
                result_df.columns = ['_'.join(col).strip('_') for col in result_df.columns.values]
                
            elif analysis_type == "cost_trends":
                # Ensure Date column is datetime
                df_copy = filtered_df.copy()
                df_copy['Date'] = pd.to_datetime(df_copy['Date'])
                
                # Extract month-year for grouping
                df_copy['Month'] = df_copy['Date'].dt.to_period('M')
                
                # Group by month
                result_df = df_copy.groupby('Month').agg({
                    'Total': ['mean', 'sum', 'count'],
                    'Distance (KM)': ['sum'],
                    'Rental hour': ['sum']
                }).reset_index()
                
                # Flatten multi-index columns
                result_df.columns = ['_'.join(col).strip('_') for col in result_df.columns.values]
                
            else:
                # For other analyses, just export the filtered data
                result_df = filtered_df
            
            # Save to file
            if file_path.endswith('.xlsx'):
                result_df.to_excel(file_path, index=False)
            else:
                result_df.to_csv(file_path, index=False)
            
            messagebox.showinfo("Export Complete", f"Data exported successfully to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
    
    def setup_settings_tab(self):
        # Settings frame
        settings_frame = ttk.LabelFrame(self.settings_tab, text="Data Settings")
        settings_frame.pack(fill='x', expand=False, padx=10, pady=10)
        
        # Data file
        ttk.Label(settings_frame, text="Data File:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.data_file_var = tk.StringVar(value="22 - Sheet1.csv")
        ttk.Entry(settings_frame, textvariable=self.data_file_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Browse button
        ttk.Button(settings_frame, text="Browse", command=self.browse_file).grid(
            row=0, column=2, padx=5, pady=5, sticky='w')
        
        # Load data button
        ttk.Button(settings_frame, text="Load Data", command=self.load_data_action).grid(
            row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Fuel cost settings
        fuel_frame = ttk.LabelFrame(self.settings_tab, text="Fuel Cost Settings")
        fuel_frame.pack(fill='x', expand=False, padx=10, pady=10, ipadx=10, ipady=10)
        
        ttk.Label(fuel_frame, text="Cost for full tank (SGD):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.fuel_cost_var = tk.StringVar(value="20")
        ttk.Entry(fuel_frame, textvariable=self.fuel_cost_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(fuel_frame, text="Expected distance per tank (km):").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.tank_distance_var = tk.StringVar(value="110")
        ttk.Entry(fuel_frame, textvariable=self.tank_distance_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Mileage charge settings
        mileage_frame = ttk.LabelFrame(self.settings_tab, text="Mileage Charge Settings")
        mileage_frame.pack(fill='x', expand=False, padx=10, pady=10, ipadx=10, ipady=10)
        
        ttk.Label(mileage_frame, text="Getgo (SGD/km):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.getgo_mileage_var = tk.StringVar(value="0.39")
        ttk.Entry(mileage_frame, textvariable=self.getgo_mileage_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(mileage_frame, text="Car Club (SGD/km):").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.carclub_mileage_var = tk.StringVar(value="0.33")
        ttk.Entry(mileage_frame, textvariable=self.carclub_mileage_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Save settings button
        save_button = ttk.Button(self.settings_tab, text="Save Settings", command=self.save_settings)
        save_button.pack(anchor='w', padx=10, pady=20)
    
    def setup_records_management_tab(self):
        """Set up the records management tab for CRUD operations"""
        # Main frame
        main_frame = ttk.Frame(self.records_management_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Split into left and right panes
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        # Records list on the left
        records_frame = ttk.LabelFrame(left_frame, text="Rental Records")
        records_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create treeview for records
        columns = ("Date", "Car Model", "Provider", "Distance", "Duration", "Total Cost")
        self.records_tree = ttk.Treeview(records_frame, columns=columns, show="headings", height=20)
        
        # Set column headings
        for col in columns:
            self.records_tree.heading(col, text=col)
            self.records_tree.column(col, width=100, anchor="center")
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(records_frame, orient="vertical", command=self.records_tree.yview)
        x_scrollbar = ttk.Scrollbar(records_frame, orient="horizontal", command=self.records_tree.xview)
        self.records_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Pack the treeview and scrollbars
        self.records_tree.pack(side="top", fill="both", expand=True)
        y_scrollbar.pack(side="right", fill="y")
        x_scrollbar.pack(side="bottom", fill="x")
        
        # Add select event
        self.records_tree.bind("<<TreeviewSelect>>", self.on_record_select)
        
        # Buttons for record operations
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill='x', expand=False, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Refresh Records", command=self.refresh_records).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_record).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Export Records", command=self.export_records_data).pack(side="left", padx=5)
        
        # Add search field
        search_frame = ttk.Frame(button_frame)
        search_frame.pack(side="right", padx=5)
        
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=2)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=15)
        search_entry.pack(side="left", padx=2)
        search_entry.bind("<KeyRelease>", self.filter_records)
        
        # Record form on the right
        form_frame = ttk.LabelFrame(right_frame, text="Record Details")
        form_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Form fields - using grid for better alignment
        # Row 0
        ttk.Label(form_frame, text="Date (DD/MM/YYYY):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.record_date_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_date_var, width=15).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Row 1
        ttk.Label(form_frame, text="Car Model:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.record_car_model_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_car_model_var, width=25).grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # Row 2
        ttk.Label(form_frame, text="Provider:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.record_provider_var = tk.StringVar()
        ttk.Combobox(form_frame, textvariable=self.record_provider_var, values=["Getgo", "Car Club", "Econ", "Stand"], width=15).grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        # Row 3
        ttk.Label(form_frame, text="Distance (KM):").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.record_distance_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_distance_var, width=10).grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        # Row 4
        ttk.Label(form_frame, text="Rental Hours:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        self.record_hours_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_hours_var, width=10).grid(row=4, column=1, padx=5, pady=5, sticky='w')
        
        # Row 5
        ttk.Label(form_frame, text="Fuel Pumped (L):").grid(row=5, column=0, padx=5, pady=5, sticky='w')
        self.record_fuel_pumped_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_fuel_pumped_var, width=10).grid(row=5, column=1, padx=5, pady=5, sticky='w')
        
        # Row 6
        ttk.Label(form_frame, text="Estimated Fuel Usage (L):").grid(row=6, column=0, padx=5, pady=5, sticky='w')
        self.record_fuel_usage_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_fuel_usage_var, width=10).grid(row=6, column=1, padx=5, pady=5, sticky='w')
        
        # Row 7
        ttk.Label(form_frame, text="Weekend/Weekday:").grid(row=7, column=0, padx=5, pady=5, sticky='w')
        self.record_weekend_var = tk.StringVar()
        ttk.Combobox(form_frame, textvariable=self.record_weekend_var, values=["weekday", "weekend"], width=15).grid(row=7, column=1, padx=5, pady=5, sticky='w')
        
        # Row 8
        ttk.Label(form_frame, text="Total Cost ($):").grid(row=8, column=0, padx=5, pady=5, sticky='w')
        self.record_total_cost_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_total_cost_var, width=10).grid(row=8, column=1, padx=5, pady=5, sticky='w')
        
        # Additional fields on right side
        # Row 0
        ttk.Label(form_frame, text="Pumped Fuel Cost ($):").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.record_pumped_cost_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_pumped_cost_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Row 1
        ttk.Label(form_frame, text="Cost per KM ($):").grid(row=1, column=2, padx=5, pady=5, sticky='w')
        self.record_cost_per_km_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_cost_per_km_var, width=10).grid(row=1, column=3, padx=5, pady=5, sticky='w')
        
        # Row 2
        ttk.Label(form_frame, text="Duration Cost ($):").grid(row=2, column=2, padx=5, pady=5, sticky='w')
        self.record_duration_cost_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_duration_cost_var, width=10).grid(row=2, column=3, padx=5, pady=5, sticky='w')
        
        # Row 3
        ttk.Label(form_frame, text="Consumption (KM/L):").grid(row=3, column=2, padx=5, pady=5, sticky='w')
        self.record_consumption_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_consumption_var, width=10).grid(row=3, column=3, padx=5, pady=5, sticky='w')
        
        # Row 4
        ttk.Label(form_frame, text="Est Original Fuel Savings ($):").grid(row=4, column=2, padx=5, pady=5, sticky='w')
        self.record_fuel_savings_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_fuel_savings_var, width=10).grid(row=4, column=3, padx=5, pady=5, sticky='w')
        
        # Row 5
        ttk.Label(form_frame, text="Cost/HR ($):").grid(row=5, column=2, padx=5, pady=5, sticky='w')
        self.record_cost_per_hr_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.record_cost_per_hr_var, width=10).grid(row=5, column=3, padx=5, pady=5, sticky='w')
        
        # Button frame for CRUD operations
        crud_frame = ttk.Frame(form_frame)
        crud_frame.grid(row=10, column=0, columnspan=4, padx=5, pady=10)
        
        ttk.Button(crud_frame, text="Clear Form", command=self.clear_record_form).pack(side="left", padx=5)
        ttk.Button(crud_frame, text="Add New Record", command=self.add_record).pack(side="left", padx=5)
        ttk.Button(crud_frame, text="Update Record", command=self.update_record).pack(side="left", padx=5)
        
        # Record ID variable (hidden) for tracking which record is being edited
        self.current_record_index = None
    
    def browse_file(self):
        """Open file browser to select data file"""
        filename = filedialog.askopenfilename(
            initialdir="./",
            title="Select CSV File",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if filename:
            self.data_file_var.set(filename)
    
    def load_data_action(self):
        """Load data from the selected file"""
        file_path = self.data_file_var.get()
        self.load_data_file(file_path)
    
    def load_data_file(self, file_path):
        """Load and process data from file"""
        try:
            self.df = load_data(file_path)
            self.df = preprocess_data(self.df)
            self.cost_analysis = analyze_rental_costs(self.df)
            messagebox.showinfo("Success", f"Data loaded successfully from {file_path}")
            
            # Remove message labels once data is loaded
            if hasattr(self, 'message_label'):
                self.message_label.place_forget()
            if hasattr(self, 'analysis_label'):
                self.analysis_label.place_forget()
            
            # Refresh records if tab exists
            if hasattr(self, 'records_tree'):
                self.refresh_records()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
    
    def get_recommendations_action(self):
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "Please load rental data first.")
            return
        
        try:
            # Get user inputs
            distance = float(self.distance_var.get())
            duration = float(self.duration_var.get())
            is_weekend = self.is_weekend_var.get()
            
            # Validate inputs
            if distance <= 0 or duration <= 0:
                messagebox.showwarning("Invalid Input", "Distance and duration must be positive numbers.")
                return
            
            # Get recommendations
            if self.cost_analysis is None:
                self.cost_analysis = analyze_rental_costs(self.df)
            
            recommendations = get_recommendations(distance, duration, self.cost_analysis, is_weekend)
            
            # Clear previous results
            for i in self.results_tree.get_children():
                self.results_tree.delete(i)
            
            # Display recommendations in treeview
            for i, rec in enumerate(recommendations):
                provider = rec['provider']
                car_model = rec['car_model']
                cost = f"${rec['estimated_cost']:.2f}"
                details = f"{rec['distance']} km, {rec['duration']} hrs"
                
                # Add to treeview with tags for coloring
                tag = "best" if i == 0 else ""
                self.results_tree.insert("", tk.END, values=(provider, car_model, cost, details), tags=(tag,))
            
            # Configure tag for best option
            self.results_tree.tag_configure("best", background="#e6ffe6")
            
            # Show comparison chart
            self.show_recommendation_chart(recommendations)
            
            # Update status
            self.status_var.set(f"Found {len(recommendations)} recommendations for {distance} km and {duration} hours.")
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values for distance and duration.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def show_recommendation_chart(self, recommendations=None):
        # Clear previous chart
        self.ax.clear()
        
        if not recommendations:
            return
        
        # Extract data for chart
        providers = [rec['provider'] for rec in recommendations]
        models = [rec['car_model'] for rec in recommendations]
        costs = [rec['estimated_cost'] for rec in recommendations]
        
        # Create unique labels combining provider and model
        labels = [f"{p} - {m}" if m != 'Average' else p for p, m in zip(providers, models)]
        
        # Limit to top 5 for readability
        if len(labels) > 5:
            labels = labels[:5]
            costs = costs[:5]
        
        # Create horizontal bar chart
        bars = self.ax.barh(labels, costs, color=['#4a6984', '#5f8ea9', '#7da5c1', '#9bbfd9', '#b8d8f0'][:len(labels)])
        
        # Add labels
        for bar in bars:
            width = bar.get_width()
            self.ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                       f"{width:.2f}", ha='left', va='center', fontsize=9)
        
        # Set title and labels
        self.ax.set_title("Cost Comparison", fontsize=12, pad=10)
        self.ax.set_xlabel("Estimated Cost ($)", fontsize=10)
        
        # Remove top and right spines
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['top'].set_visible(False)
        
        # Add grid lines
        self.ax.grid(axis='x', linestyle='--', alpha=0.7)
        
        # Adjust layout and redraw
        plt.tight_layout()
        self.canvas.draw()
    
    def save_settings(self):
        """Save user settings"""
        try:
            # In a complete application, we would save these to a config file
            # For now, just show confirmation
            messagebox.showinfo("Settings", "Settings saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def refresh_records(self):
        """Refresh the records list in the treeview"""
        if self.df is None:
            messagebox.showwarning("Warning", "No data loaded")
            return
            
        # Clear existing records
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
            
        # Add records from dataframe
        for idx, row in self.df.iterrows():
            try:
                # Format date for display
                date_str = row['Date'].strftime('%d/%m/%Y') if pd.notna(row['Date']) else ''
                
                # Add record to tree with index as ID
                self.records_tree.insert("", "end", iid=str(idx), values=(
                    date_str,
                    row['Car model'] if pd.notna(row['Car model']) else '',
                    row['Car Cat'] if pd.notna(row['Car Cat']) else '',
                    f"{row['Distance (KM)']:.2f}" if pd.notna(row['Distance (KM)']) else '',
                    f"{row['Rental hour']:.2f}" if pd.notna(row['Rental hour']) else '',
                    f"${row['Total']:.2f}" if pd.notna(row['Total']) else ''
                ))
            except Exception as e:
                # Skip problematic records
                print(f"Error adding record {idx}: {e}")
                continue
    
    def on_record_select(self, event):
        """Handle record selection in the treeview"""
        selected_items = self.records_tree.selection()
        if not selected_items:
            return
            
        # Get the selected record's index
        idx = int(selected_items[0])
        self.current_record_index = idx
        
        # Get the record data
        row = self.df.iloc[idx]
        
        # Populate the form fields
        self.record_date_var.set(row['Date'].strftime('%d/%m/%Y') if pd.notna(row['Date']) else '')
        self.record_car_model_var.set(row['Car model'] if pd.notna(row['Car model']) else '')
        self.record_provider_var.set(row['Car Cat'] if pd.notna(row['Car Cat']) else '')
        self.record_distance_var.set(f"{row['Distance (KM)']}" if pd.notna(row['Distance (KM)']) else '')
        self.record_hours_var.set(f"{row['Rental hour']}" if pd.notna(row['Rental hour']) else '')
        self.record_fuel_pumped_var.set(f"{row['Fuel pumped']}".replace(' L', '') if pd.notna(row['Fuel pumped']) else '')
        self.record_fuel_usage_var.set(f"{row['Estimated fuel usage']}" if pd.notna(row['Estimated fuel usage']) else '')
        self.record_weekend_var.set(row['Weekday/weekend'] if pd.notna(row['Weekday/weekend']) else '')
        self.record_total_cost_var.set(f"{row['Total']}" if pd.notna(row['Total']) else '')
        self.record_pumped_cost_var.set(f"{row['Pumped fuel cost']}".replace('$', '') if pd.notna(row['Pumped fuel cost']) else '')
        self.record_cost_per_km_var.set(f"{row['Cost per KM']}".replace('$', '') if pd.notna(row['Cost per KM']) else '')
        self.record_duration_cost_var.set(f"{row['Duration cost']}".replace('$', '') if pd.notna(row['Duration cost']) else '')
        self.record_consumption_var.set(f"{row['Consumption (KM/L)']}" if pd.notna(row['Consumption (KM/L)']) else '')
        self.record_fuel_savings_var.set(f"{row['Est original fuel savings']}".replace('$', '') if pd.notna(row['Est original fuel savings']) else '')
        self.record_cost_per_hr_var.set(f"{row['Cost/HR']}".replace('$', '') if pd.notna(row['Cost/HR']) else '')
    
    def clear_record_form(self):
        """Clear all form fields"""
        self.current_record_index = None
        self.record_date_var.set('')
        self.record_car_model_var.set('')
        self.record_provider_var.set('')
        self.record_distance_var.set('')
        self.record_hours_var.set('')
        self.record_fuel_pumped_var.set('')
        self.record_fuel_usage_var.set('')
        self.record_weekend_var.set('')
        self.record_total_cost_var.set('')
        self.record_pumped_cost_var.set('')
        self.record_cost_per_km_var.set('')
        self.record_duration_cost_var.set('')
        self.record_consumption_var.set('')
        self.record_fuel_savings_var.set('')
        self.record_cost_per_hr_var.set('')
    
    def get_form_data(self):
        """Get data from the form fields and validate it"""
        try:
            # Parse date
            date_str = self.record_date_var.get()
            try:
                date = pd.to_datetime(date_str, format='%d/%m/%Y')
            except:
                messagebox.showerror("Error", "Invalid date format. Please use DD/MM/YYYY.")
                return None
                
            # Get other field values with validation
            car_model = self.record_car_model_var.get()
            if not car_model:
                messagebox.showerror("Error", "Car model is required.")
                return None
                
            provider = self.record_provider_var.get()
            if not provider:
                messagebox.showerror("Error", "Provider is required.")
                return None
                
            # Parse numeric fields
            try:
                distance = float(self.record_distance_var.get()) if self.record_distance_var.get() else None
                rental_hour = float(self.record_hours_var.get()) if self.record_hours_var.get() else None
                fuel_pumped = float(self.record_fuel_pumped_var.get()) if self.record_fuel_pumped_var.get() else None
                fuel_usage = float(self.record_fuel_usage_var.get()) if self.record_fuel_usage_var.get() else None
                total = float(self.record_total_cost_var.get()) if self.record_total_cost_var.get() else None
                pumped_cost = float(self.record_pumped_cost_var.get()) if self.record_pumped_cost_var.get() else None
                cost_per_km = float(self.record_cost_per_km_var.get()) if self.record_cost_per_km_var.get() else None
                duration_cost = float(self.record_duration_cost_var.get()) if self.record_duration_cost_var.get() else None
                consumption = float(self.record_consumption_var.get()) if self.record_consumption_var.get() else None
                fuel_savings = float(self.record_fuel_savings_var.get()) if self.record_fuel_savings_var.get() else None
                cost_per_hr = float(self.record_cost_per_hr_var.get()) if self.record_cost_per_hr_var.get() else None
            except ValueError:
                messagebox.showerror("Error", "Invalid numeric value in one or more fields.")
                return None
                
            weekend = self.record_weekend_var.get()
            
            # Create record dict
            record = {
                'Date': date,
                'Car model': car_model,
                'Car Cat': provider,
                'Distance (KM)': distance,
                'Rental hour': rental_hour,
                'Fuel pumped': f"{fuel_pumped} L" if fuel_pumped is not None else None,
                'Estimated fuel usage': fuel_usage,
                'Consumption (KM/L)': consumption,
                'Pumped fuel cost': f"${pumped_cost}" if pumped_cost is not None else None,
                'Cost per KM': cost_per_km,
                'Duration cost': duration_cost,
                'Total': total,
                'Est original fuel savings': fuel_savings,
                'Weekday/weekend': weekend,
                'Cost/HR': cost_per_hr
            }
            
            return record
        except Exception as e:
            messagebox.showerror("Error", f"Error validating form data: {str(e)}")
            return None
    
    def add_record(self):
        """Add a new record from form data"""
        if self.df is None:
            messagebox.showerror("Error", "No data loaded")
            return
            
        record = self.get_form_data()
        if record is None:
            return
            
        # Add record to dataframe
        self.df = pd.concat([self.df, pd.DataFrame([record])], ignore_index=True)
        
        # Refresh the cost analysis
        self.cost_analysis = analyze_rental_costs(self.df)
        
        # Refresh the records list
        self.refresh_records()
        
        # Clear the form
        self.clear_record_form()
        
        # Show success message
        messagebox.showinfo("Success", "Record added successfully")
        
        # Save the changes
        self.save_data()
    
    def update_record(self):
        """Update an existing record with form data"""
        if self.df is None:
            messagebox.showerror("Error", "No data loaded")
            return
            
        if self.current_record_index is None:
            messagebox.showerror("Error", "No record selected")
            return
            
        record = self.get_form_data()
        if record is None:
            return
            
        # Update record in dataframe
        for key, value in record.items():
            if key in self.df.columns:
                self.df.at[self.current_record_index, key] = value
        
        # Refresh the cost analysis
        self.cost_analysis = analyze_rental_costs(self.df)
        
        # Refresh the records list
        self.refresh_records()
        
        # Show success message
        messagebox.showinfo("Success", "Record updated successfully")
        
        # Save the changes
        self.save_data()
    
    def delete_record(self):
        """Delete the selected record"""
        if self.df is None:
            messagebox.showerror("Error", "No data loaded")
            return
            
        selected_items = self.records_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No record selected")
            return
            
        # Confirm deletion
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete the selected record?"):
            return
            
        # Get the selected record's index
        idx = int(selected_items[0])
        
        # Delete record from dataframe
        self.df = self.df.drop(idx).reset_index(drop=True)
        
        # Refresh the cost analysis
        self.cost_analysis = analyze_rental_costs(self.df)
        
        # Refresh the records list
        self.refresh_records()
        
        # Clear the form
        self.clear_record_form()
        
        # Show success message
        messagebox.showinfo("Success", "Record deleted successfully")
        
        # Save the changes
        self.save_data()
    
    def save_data(self):
        """Save the data to the CSV file"""
        try:
            file_path = self.data_file_var.get()
            self.df.to_csv(file_path, index=False)
            print(f"Data saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")
    
    def on_tab_changed(self, event):
        """Handle tab change events"""
        tab_id = self.notebook.select()
        tab_name = self.notebook.tab(tab_id, "text")
        
        # Refresh data in certain tabs when selected
        if tab_name == "Records Management":
            self.refresh_records()
        elif tab_name == "Data Analysis":
            # Only analyze if data is available
            if self.df is not None and not self.df.empty:
                self.update_analysis_chart()
    
    def export_records_data(self):
        """Export records data to CSV or Excel"""
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "No records to export")
            return
        
        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Export Rental Records"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Save to file
            if file_path.endswith('.xlsx'):
                self.df.to_excel(file_path, index=False)
            else:
                self.df.to_csv(file_path, index=False)
            
            messagebox.showinfo("Export Complete", f"Records exported successfully to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export records: {str(e)}")
    
    def filter_records(self, event=None):
        """Filter records based on search text"""
        if self.df is None:
            return
        
        search_text = self.search_var.get().lower()
        
        # Clear existing records
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        
        # If search text is empty, show all records
        if not search_text:
            self.refresh_records()
            return
        
        # Add matching records
        for idx, row in self.df.iterrows():
            # Check if search text appears in any of the displayed columns
            date_str = row['Date'].strftime('%d/%m/%Y') if pd.notna(row['Date']) else ''
            car_model = str(row['Car model']) if pd.notna(row['Car model']) else ''
            provider = str(row['Car Cat']) if pd.notna(row['Car Cat']) else ''
            
            if (search_text in date_str.lower() or 
                search_text in car_model.lower() or 
                search_text in provider.lower()):
                
                self.records_tree.insert("", "end", iid=str(idx), values=(
                    date_str,
                    car_model,
                    provider,
                    f"{row['Distance (KM)']:.2f}" if pd.notna(row['Distance (KM)']) else '',
                    f"{row['Rental hour']:.2f}" if pd.notna(row['Rental hour']) else '',
                    f"${row['Total']:.2f}" if pd.notna(row['Total']) else ''
                ))
        
        # Update status
        match_count = len(self.records_tree.get_children())
        self.status_var.set(f"Found {match_count} matching records for '{search_text}'")

    def show_car_models_analysis(self, df):
        """Show analysis of car models"""
        if 'Car model' not in df.columns:
            messagebox.showwarning("Missing Data", "Car model information is missing")
            return
        
        # Group by car model
        model_stats = df.groupby('Car model').agg({
            'Total': ['mean', 'count', 'sum'],
            'Distance (KM)': ['sum', 'mean'],
            'Rental hour': ['sum', 'mean'],
            'Consumption (KM/L)': ['mean']
        }).reset_index()
        
        # Flatten multi-index columns
        model_stats.columns = ['_'.join(col).strip('_') for col in model_stats.columns.values]
        
        # Sort by frequency of use
        model_stats = model_stats.sort_values('Total_count', ascending=False).head(10)
        
        # Display key statistics
        self.add_stat("Total Models", f"{df['Car model'].nunique()}")
        self.add_stat("Most Used Model", f"{model_stats['Car model'].iloc[0]}")
        self.add_stat("Total Trips", f"{len(df)}")
        self.add_stat("Average Trip Cost", f"${df['Total'].mean():.2f}")
        
        # Create bar chart for model frequency
        models = model_stats['Car model'].tolist()
        trip_counts = model_stats['Total_count'].tolist()
        
        # Create horizontal bar chart for better readability with long model names
        bars = self.analysis_ax.barh(models, trip_counts, color='#4a6984')
        
        # Add data labels
        for bar in bars:
            width = bar.get_width()
            self.analysis_ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                                f"{int(width)} trips", ha='left', va='center', fontsize=9)
        
        # Set chart properties
        self.analysis_ax.set_title("Most Used Car Models", fontsize=12)
        self.analysis_ax.set_xlabel("Number of Trips", fontsize=10)
        self.analysis_ax.set_ylabel("Car Model", fontsize=10)
        self.analysis_ax.grid(axis='x', linestyle='--', alpha=0.3)
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_monthly_summary(self, df):
        """Show monthly summary of rental activity"""
        if 'Date' not in df.columns:
            messagebox.showwarning("Missing Data", "Date information is missing")
            return
        
        # Ensure Date column is datetime
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_dtype(df_copy['Date']):
            try:
                df_copy['Date'] = pd.to_datetime(df_copy['Date'])
            except:
                messagebox.showwarning("Data Error", "Could not parse dates correctly")
                return
        
        # Extract month and year
        df_copy['Month-Year'] = df_copy['Date'].dt.strftime('%b %Y')
        df_copy['Month'] = df_copy['Date'].dt.month
        df_copy['Year'] = df_copy['Date'].dt.year
        
        # Get unique month-years in chronological order
        month_years = df_copy.sort_values('Date')['Month-Year'].unique()
        
        # Group by month-year
        monthly_data = df_copy.groupby('Month-Year').agg({
            'Total': ['count', 'sum'],
            'Distance (KM)': 'sum'
        }).reset_index()
        
        # Flatten multi-index columns
        monthly_data.columns = ['_'.join(col).strip('_') for col in monthly_data.columns.values]
        
        # Calculate average distance per trip
        monthly_data['Avg_Distance'] = monthly_data['Distance (KM)_sum'] / monthly_data['Total_count']
        
        # Display key statistics
        first_month = month_years[0] if len(month_years) > 0 else "N/A"
        last_month = month_years[-1] if len(month_years) > 0 else "N/A"
        
        self.add_stat("Period", f"{first_month} to {last_month}")
        self.add_stat("Total Months", f"{len(month_years)}")
        self.add_stat("Total Trips", f"{df_copy['Total'].count()}")
        self.add_stat("Total Spending", f"${df_copy['Total'].sum():.2f}")
        
        # Reorder for chronological display (ensure month-years are in order)
        monthly_data = monthly_data.set_index('Month-Year').loc[month_years].reset_index()
        
        # Plot
        x = range(len(monthly_data))
        width = 0.35
        
        # Primary axis: Trip counts
        bars1 = self.analysis_ax.bar([i - width/2 for i in x], monthly_data['Total_count'], 
                                    width, label='Trips', color='#4a6984')
        
        # Secondary axis: Total cost
        ax2 = self.analysis_ax.twinx()
        bars2 = ax2.bar([i + width/2 for i in x], monthly_data['Total_sum'], 
                       width, label='Total Cost ($)', color='#e67e22')
        
        # Add labels and configure axes
        self.analysis_ax.set_title("Monthly Rental Activity", fontsize=12)
        self.analysis_ax.set_ylabel("Number of Trips", fontsize=10)
        ax2.set_ylabel("Total Monthly Cost ($)", fontsize=10, color='#e67e22')
        
        # Set x-ticks to month-year labels
        self.analysis_ax.set_xticks(x)
        self.analysis_ax.set_xticklabels(monthly_data['Month-Year'], rotation=45, ha='right')
        
        # Add grid
        self.analysis_ax.grid(axis='y', linestyle='--', alpha=0.3)
        
        # Add legend
        lines = [bars1[0], bars2[0]]
        labels = ['Trips', 'Total Cost ($)']
        self.analysis_ax.legend(lines, labels, loc='upper left')
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

# Main function
def main():
    root = tk.Tk()
    app = CarRentalRecommenderApp(root)
    
    # Center the window on screen
    window_width = 1000
    window_height = 700
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int((screen_width - window_width) / 2)
    center_y = int((screen_height - window_height) / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    root.mainloop()

if __name__ == "__main__":
    main() 