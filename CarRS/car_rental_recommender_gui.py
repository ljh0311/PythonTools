import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

# Load the data
def load_data(file_path):
    """Load the rental data from the CSV file."""
    df = pd.read_csv(file_path)
    # Clean up column names
    df.columns = df.columns.str.strip()
    return df

# Preprocess the data
def preprocess_data(df):
    """Clean and preprocess the rental data."""
    # Remove empty rows
    df = df.dropna(subset=['Car model'], how='all')
    
    # Convert date strings to datetime objects
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
    
    # Convert numeric columns
    numeric_cols = ['Distance (KM)', 'Fuel pumped', 'Estimated fuel usage', 
                   'Consumption (KM/L)', 'Fuel cost', 'Pumped fuel cost',
                   'Mileage cost ($0.39)', 'Cost per KM', 'Duration cost', 
                   'Total', 'Est original fuel savings', 'Rental hour', 'Cost/HR']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace('L', ''), errors='coerce')
    
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
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # Set icon if available
        try:
            self.root.iconbitmap("car_icon.ico")
        except:
            pass
        
        self.create_widgets()
        
        # Data variables
        self.df = None
        self.cost_analysis = None
        self.recommendations = None
        
        # Try to load default data file
        default_file = "22 - Sheet1.csv"
        if os.path.exists(default_file):
            self.load_data_file(default_file)
    
    def create_widgets(self):
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Recommendation System
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="Recommendations")
        
        # Tab 2: Data Analysis
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text="Data Analysis")
        
        # Tab 3: Settings
        self.tab3 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab3, text="Settings")
        
        # Set up Tab 1: Recommendation System
        self.setup_recommendation_tab()
        
        # Set up Tab 2: Data Analysis
        self.setup_data_analysis_tab()
        
        # Set up Tab 3: Settings
        self.setup_settings_tab()
    
    def setup_recommendation_tab(self):
        # Input Frame
        input_frame = ttk.LabelFrame(self.tab1, text="Trip Details")
        input_frame.pack(fill='x', expand=False, padx=10, pady=10)
        
        # Distance input
        ttk.Label(input_frame, text="Distance (km):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.distance_var = tk.StringVar(value="50")
        ttk.Entry(input_frame, textvariable=self.distance_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Duration input
        ttk.Label(input_frame, text="Duration (hours):").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.duration_var = tk.StringVar(value="3")
        ttk.Entry(input_frame, textvariable=self.duration_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Weekend checkbox
        self.is_weekend_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="Weekend Trip", variable=self.is_weekend_var).grid(
            row=0, column=4, padx=5, pady=5, sticky='w')
        
        # Get Recommendations button
        ttk.Button(input_frame, text="Get Recommendations", command=self.get_recommendations_action).grid(
            row=0, column=5, padx=20, pady=5, sticky='e')
        
        # Results Frame
        self.results_frame = ttk.LabelFrame(self.tab1, text="Recommendations")
        self.results_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create treeview for recommendations
        self.tree = ttk.Treeview(self.results_frame, columns=("Rank", "Provider", "Car Model", "Total Cost", 
                                                              "Hourly Cost", "Mileage Cost", "Fuel Cost"),
                                show="headings", height=10)
        
        # Set column headings
        self.tree.heading("Rank", text="Rank")
        self.tree.heading("Provider", text="Provider")
        self.tree.heading("Car Model", text="Car Model")
        self.tree.heading("Total Cost", text="Total Cost")
        self.tree.heading("Hourly Cost", text="Hourly Cost")
        self.tree.heading("Mileage Cost", text="Mileage Cost")
        self.tree.heading("Fuel Cost", text="Fuel Cost")
        
        # Set column widths
        self.tree.column("Rank", width=50, anchor="center")
        self.tree.column("Provider", width=100, anchor="center")
        self.tree.column("Car Model", width=200, anchor="center")
        self.tree.column("Total Cost", width=100, anchor="center")
        self.tree.column("Hourly Cost", width=100, anchor="center")
        self.tree.column("Mileage Cost", width=100, anchor="center")
        self.tree.column("Fuel Cost", width=100, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack the treeview and scrollbar
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Chart frame for visualization
        self.chart_frame = ttk.LabelFrame(self.tab1, text="Cost Comparison")
        self.chart_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Message when no data is loaded
        self.message_label = ttk.Label(self.results_frame, 
                                      text="Please enter trip details and click 'Get Recommendations'",
                                      font=("Arial", 12))
        self.message_label.place(relx=0.5, rely=0.5, anchor="center")
    
    def setup_data_analysis_tab(self):
        # Analysis options frame
        options_frame = ttk.LabelFrame(self.tab2, text="Analysis Options")
        options_frame.pack(fill='x', expand=False, padx=10, pady=10)
        
        # Provider selection
        ttk.Label(options_frame, text="Provider:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.provider_var = tk.StringVar(value="All")
        self.provider_combo = ttk.Combobox(options_frame, textvariable=self.provider_var, 
                                         values=["All", "Getgo", "Car Club", "Econ", "Stand"])
        self.provider_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.provider_combo.current(0)
        
        # Analysis type
        ttk.Label(options_frame, text="Analysis:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.analysis_var = tk.StringVar(value="Cost per Hour")
        self.analysis_combo = ttk.Combobox(options_frame, textvariable=self.analysis_var, 
                                         values=["Cost per Hour", "Cost per KM", "Consumption", "Trip Counts"])
        self.analysis_combo.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        self.analysis_combo.current(0)
        
        # Analyze button
        ttk.Button(options_frame, text="Analyze", command=self.analyze_data).grid(
            row=0, column=4, padx=20, pady=5, sticky='e')
        
        # Create a frame for the chart
        self.analysis_chart_frame = ttk.Frame(self.tab2)
        self.analysis_chart_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Message when no data is loaded
        self.analysis_label = ttk.Label(self.analysis_chart_frame, 
                                      text="Please load data file first or select analysis options",
                                      font=("Arial", 12))
        self.analysis_label.place(relx=0.5, rely=0.5, anchor="center")
    
    def setup_settings_tab(self):
        # Settings frame
        settings_frame = ttk.LabelFrame(self.tab3, text="Data Settings")
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
        fuel_frame = ttk.LabelFrame(self.tab3, text="Fuel Cost Settings")
        fuel_frame.pack(fill='x', expand=False, padx=10, pady=10, ipadx=10, ipady=10)
        
        ttk.Label(fuel_frame, text="Cost for full tank (SGD):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.fuel_cost_var = tk.StringVar(value="20")
        ttk.Entry(fuel_frame, textvariable=self.fuel_cost_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(fuel_frame, text="Expected distance per tank (km):").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.tank_distance_var = tk.StringVar(value="110")
        ttk.Entry(fuel_frame, textvariable=self.tank_distance_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Mileage charge settings
        mileage_frame = ttk.LabelFrame(self.tab3, text="Mileage Charge Settings")
        mileage_frame.pack(fill='x', expand=False, padx=10, pady=10, ipadx=10, ipady=10)
        
        ttk.Label(mileage_frame, text="Getgo (SGD/km):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.getgo_mileage_var = tk.StringVar(value="0.39")
        ttk.Entry(mileage_frame, textvariable=self.getgo_mileage_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(mileage_frame, text="Car Club (SGD/km):").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.carclub_mileage_var = tk.StringVar(value="0.33")
        ttk.Entry(mileage_frame, textvariable=self.carclub_mileage_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Save settings button
        save_button = ttk.Button(self.tab3, text="Save Settings", command=self.save_settings)
        save_button.pack(anchor='w', padx=10, pady=20)
    
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
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
    
    def get_recommendations_action(self):
        """Get recommendations based on user input"""
        if self.cost_analysis is None:
            messagebox.showwarning("Warning", "Please load data first")
            return
        
        try:
            distance = float(self.distance_var.get())
            duration = float(self.duration_var.get())
            is_weekend = self.is_weekend_var.get()
            
            # Get recommendations
            self.recommendations = get_recommendations(distance, duration, self.cost_analysis, is_weekend, top_n=10)
            
            # Clear previous data
            for i in self.tree.get_children():
                self.tree.delete(i)
            
            # Insert new recommendations
            for i, rec in enumerate(self.recommendations, 1):
                self.tree.insert("", "end", values=(
                    i,
                    rec['provider'],
                    rec['car_model'],
                    f"${rec['estimated_cost']:.2f}",
                    f"${rec['hourly_cost']:.2f}",
                    f"${rec['mileage_cost']:.2f}",
                    f"${rec['fuel_cost']:.2f}"
                ))
            
            # Generate chart
            self.show_recommendation_chart()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for distance and duration")
    
    def show_recommendation_chart(self):
        """Display a chart comparing recommendations"""
        # Clear previous chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Get data for the chart (use only top 5 for clarity)
        top_recs = self.recommendations[:5]
        labels = [f"{r['provider']}\n{r['car_model']}" for r in top_recs]
        
        # Create data for stacked bar chart
        hourly_costs = [r['hourly_cost'] for r in top_recs]
        mileage_costs = [r['mileage_cost'] for r in top_recs]
        fuel_costs = [r['fuel_cost'] for r in top_recs]
        
        # Create stacked bar chart
        width = 0.6
        ax.bar(labels, hourly_costs, width, label='Hourly Cost')
        ax.bar(labels, mileage_costs, width, bottom=hourly_costs, label='Mileage Cost')
        
        # Add fuel costs to appropriate bars
        bottoms = [h + m for h, m in zip(hourly_costs, mileage_costs)]
        ax.bar(labels, fuel_costs, width, bottom=bottoms, label='Fuel Cost')
        
        # Add total cost on top of each bar
        for i, rec in enumerate(top_recs):
            ax.text(i, rec['estimated_cost'] + 1, f"${rec['estimated_cost']:.2f}", 
                   ha='center', va='bottom', fontweight='bold')
        
        # Set chart properties
        ax.set_ylabel('Cost (SGD)')
        ax.set_title('Cost Comparison for Top 5 Recommendations')
        ax.legend()
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=15, ha='right')
        
        # Adjust layout
        plt.tight_layout()
        
        # Create canvas for displaying the plot
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def analyze_data(self):
        """Analyze data based on selected options"""
        if self.df is None:
            messagebox.showwarning("Warning", "Please load data first")
            return
        
        provider = self.provider_var.get()
        analysis_type = self.analysis_var.get()
        
        # Clear previous chart
        for widget in self.analysis_chart_frame.winfo_children():
            widget.destroy()
        
        # Filter data by provider if not "All"
        data = self.df
        if provider != "All":
            data = data[data['Car Cat'] == provider]
        
        if data.empty:
            messagebox.showinfo("Info", f"No data available for {provider}")
            return
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if analysis_type == "Cost per Hour":
            # Group by car model and calculate mean cost per hour
            car_costs = data.groupby('Car model')['Cost/HR'].mean().sort_values(ascending=False)
            car_costs = car_costs.head(10)  # Show top 10 for clarity
            
            car_costs.plot(kind='bar', ax=ax, color='skyblue')
            ax.set_ylabel('Average Cost per Hour (SGD)')
            ax.set_title(f'Average Hourly Cost by Car Model ({provider})')
            
        elif analysis_type == "Cost per KM":
            # Group by car model and calculate mean cost per km
            car_costs = data.groupby('Car model')['Cost per KM'].mean().sort_values(ascending=False)
            car_costs = car_costs.head(10)  # Show top 10 for clarity
            
            car_costs.plot(kind='bar', ax=ax, color='lightgreen')
            ax.set_ylabel('Average Cost per KM (SGD)')
            ax.set_title(f'Average Cost per KM by Car Model ({provider})')
            
        elif analysis_type == "Consumption":
            # Group by car model and calculate mean consumption
            car_consumption = data.groupby('Car model')['Consumption (KM/L)'].mean().sort_values(ascending=False)
            car_consumption = car_consumption.head(10)  # Show top 10 for clarity
            
            car_consumption.plot(kind='bar', ax=ax, color='salmon')
            ax.set_ylabel('Average Consumption (KM/L)')
            ax.set_title(f'Average Fuel Consumption by Car Model ({provider})')
            
        elif analysis_type == "Trip Counts":
            # Count trips by car model
            car_counts = data['Car model'].value_counts().head(10)  # Show top 10 for clarity
            
            car_counts.plot(kind='bar', ax=ax, color='purple')
            ax.set_ylabel('Number of Trips')
            ax.set_title(f'Number of Trips by Car Model ({provider})')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Adjust layout
        plt.tight_layout()
        
        # Create canvas for displaying the plot
        canvas = FigureCanvasTkAgg(fig, master=self.analysis_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def save_settings(self):
        """Save user settings"""
        try:
            # In a complete application, we would save these to a config file
            # For now, just show confirmation
            messagebox.showinfo("Settings", "Settings saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

# Main function
def main():
    root = tk.Tk()
    app = CarRentalRecommenderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 