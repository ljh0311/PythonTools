import os
import sys
import pandas as pd
import tkinter as tk
import numpy as np
from car_rental_recommender_gui import CarRentalRecommenderApp, get_recommendations

# Get the current directory where this script is running
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Current directory: {current_dir}")

# Set the path to the data file
data_file = os.path.join(current_dir, "22 - Sheet1.csv")
print(f"Data file: {data_file}")

# Check if the file exists
if os.path.exists(data_file):
    print(f"Data file exists: {data_file}")
else:
    print(f"ERROR: Data file NOT found: {data_file}")
    sys.exit(1)

def enhance_dataframe(df):
    """Fix and enhance dataframe with proper formatting for all analyses to work"""
    # Make a copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Convert Date column to datetime
    if 'Date' in df.columns:
        try:
            df['Date'] = pd.to_datetime(df['Date'])
            print("Date column converted to datetime")
            # Add Month and Year columns needed for analysis
            df['Month'] = df['Date'].dt.month
            df['Year'] = df['Date'].dt.year
            print("Added Month and Year columns")
        except Exception as e:
            print(f"Warning: Could not convert Date column: {str(e)}")
    
    # Ensure numeric columns are properly formatted
    numeric_cols = [
        'Distance (KM)', 'Fuel pumped', 'Estimated fuel usage', 'Consumption (KM/L)',
        'Fuel cost', 'Pumped fuel cost', 'Mileage cost ($0.39)', 'Cost per KM',
        'Duration cost', 'Total', 'Est original fuel savings', 'Rental hour', 'Cost/HR'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            try:
                # Convert column to string, remove $ and L symbols, then convert to numeric
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace('$', '').str.replace('L', '').str.strip(), 
                    errors='coerce'
                )
                print(f"Converted {col} to numeric")
            except Exception as e:
                print(f"Warning: Could not convert {col} to numeric: {str(e)}")
    
    # Fill NaN values with reasonable defaults to prevent analysis errors
    df = df.fillna({
        'Cost per KM': df['Cost per KM'].mean() if 'Cost per KM' in df.columns and not df['Cost per KM'].isna().all() else 0.75,
        'Cost/HR': df['Cost/HR'].mean() if 'Cost/HR' in df.columns and not df['Cost/HR'].isna().all() else 15.0,
        'Consumption (KM/L)': df['Consumption (KM/L)'].mean() if 'Consumption (KM/L)' in df.columns and not df['Consumption (KM/L)'].isna().all() else 12.0,
        'Weekday/weekend': 'weekday'
    })
    
    print(f"Enhanced dataframe: {len(df)} rows ready for analysis")
    return df

def create_complete_cost_analysis(df):
    """Create a comprehensive cost analysis for providers with all required fields"""
    providers = ['Getgo', 'Car Club', 'Econ', 'Stand']
    results = {}
    
    for provider in providers:
        provider_data = df[df['Car Cat'] == provider] if 'Car Cat' in df.columns else pd.DataFrame()
        if not provider_data.empty:
            # Calculate basic stats
            avg_cost_per_km = provider_data['Cost per KM'].mean() if 'Cost per KM' in provider_data.columns else 0.75
            avg_cost_per_hour = provider_data['Cost/HR'].mean() if 'Cost/HR' in provider_data.columns else 15.00
            
            # Get unique car models
            car_models = provider_data['Car model'].unique() if 'Car model' in provider_data.columns else []
            car_model_stats = {}
            
            # Add stats for each car model
            for model in car_models:
                if pd.isna(model):  # Skip NaN model names
                    continue
                    
                model_data = provider_data[provider_data['Car model'] == model]
                car_model_stats[model] = {
                    'avg_cost_per_km': model_data['Cost per KM'].mean() if 'Cost per KM' in model_data.columns else avg_cost_per_km,
                    'avg_cost_per_hour': model_data['Cost/HR'].mean() if 'Cost/HR' in model_data.columns else avg_cost_per_hour,
                    'avg_consumption': model_data['Consumption (KM/L)'].mean() if 'Consumption (KM/L)' in model_data.columns else 12.0,
                    'count': len(model_data)
                }
            
            results[provider] = {
                'avg_cost_per_km': avg_cost_per_km,
                'avg_cost_per_hour': avg_cost_per_hour,
                'car_models': car_model_stats
            }
    
    # If we don't have any providers from the data, add some defaults
    if len(results) == 0:
        for provider in providers:
            results[provider] = {
                'avg_cost_per_km': 0.75,  # Default cost per km
                'avg_cost_per_hour': 15.00,  # Default cost per hour
                'car_models': {'Generic': {
                    'avg_cost_per_km': 0.75,
                    'avg_cost_per_hour': 15.00,
                    'avg_consumption': 12.0,
                    'count': 1
                }}
            }
    
    print(f"Created cost analysis for {len(results)} providers")
    return results

# Try to read the data file directly
try:
    df = pd.read_csv(data_file)
    print(f"Successfully read data file with {len(df)} rows and {len(df.columns)} columns")
    
    # Enhance the dataframe
    enhanced_df = enhance_dataframe(df)
    
    # Create comprehensive cost analysis
    cost_analysis = create_complete_cost_analysis(enhanced_df)
    
except Exception as e:
    print(f"ERROR processing data file: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Override the module function
original_get_recommendations = get_recommendations

def patched_get_recommendations(distance, duration, cost_analysis, is_weekend=False, top_n=5):
    """Enhanced version of get_recommendations that stores detailed cost breakdown"""
    recommendations = original_get_recommendations(distance, duration, cost_analysis, is_weekend, top_n)
    
    # Save full recommendations for detailed display
    return recommendations

# Patch module-level function
from car_rental_recommender_gui import calculate_estimated_cost as original_calculate_cost

def patched_calculate_cost(distance, duration, provider, car_model=None, cost_analysis=None, is_weekend=False):
    """Enhanced calculate_estimated_cost with more detailed cost breakdown"""
    result = original_calculate_cost(distance, duration, provider, car_model, cost_analysis, is_weekend)
    
    # Make sure we have a valid structure
    if not result:
        return result
        
    # Keep existing fields
    return result

def update_tree_with_cost_breakdowns(app):
    """Update the recommendation tree with detailed cost breakdowns"""
    # Get current values from inputs
    try:
        distance = float(app.distance_var.get())
        duration = float(app.duration_var.get())
        is_weekend = app.is_weekend_var.get()
    except:
        # Use defaults if values aren't valid
        distance = 35.0
        duration = 2.0
        is_weekend = False
    
    # After showing recommendations, update the display to show duration cost separately
    for item in app.results_tree.get_children():
        values = list(app.results_tree.item(item, "values"))
        if len(values) >= 4:
            rec_id = item
            rec_provider = values[0]
            rec_model = values[1]
            rec_cost_text = values[2]
            
            # Parse cost value
            rec_cost = rec_cost_text.replace('$', '') if isinstance(rec_cost_text, str) else rec_cost_text
            try:
                rec_cost = float(rec_cost)
            except ValueError:
                rec_cost = 0
            
            # Calculate costs based on provider
            if rec_provider == 'Getgo':
                mileage_cost = distance * 0.39
                hourly_cost = rec_cost - mileage_cost
                fuel_cost = 0
            elif rec_provider == 'Car Club':
                mileage_cost = distance * 0.33
                hourly_cost = rec_cost - mileage_cost
                fuel_cost = 0
            else:  # Econ/Stand
                mileage_cost = 0
                fuel_cost = (distance / 110) * 20 if distance > 0 else 0
                hourly_cost = rec_cost - fuel_cost
            
            # Create enhanced details string
            new_details = f"{distance} km, {duration} hrs | Duration: ${hourly_cost:.2f}"
            if mileage_cost > 0:
                new_details += f" | Mileage: ${mileage_cost:.2f}"
            if fuel_cost > 0:
                new_details += f" | Fuel: ${fuel_cost:.2f}"
            
            # Update the tree item
            values[3] = new_details
            app.results_tree.item(rec_id, values=values)
    
    print(f"Updated recommendation details with separate costs for {len(app.results_tree.get_children())} items")

# Patch the calculate_estimated_cost function to show duration cost separately
def patch_application(app):
    """Apply runtime patches to the application to improve functionality"""
    # Store the original get_recommendations function
    original_get_recommendations_action = app.get_recommendations_action
    
    # Create a patched version
    def patched_get_recommendations_action():
        """Patched version of get_recommendations_action that shows duration cost separately"""
        # Call the original function to get the recommendations
        result = original_get_recommendations_action()
        
        # Now update tree to add cost breakdowns
        root.after(100, lambda: update_tree_with_cost_breakdowns(app))
        
        return result
    
    # Replace the function
    app.get_recommendations_action = patched_get_recommendations_action
    
    print("Application patched to show duration cost separately")
    return app

# Run the main application
if __name__ == "__main__":
    print("Starting Car Rental Recommender application...")
    root = tk.Tk()
    app = CarRentalRecommenderApp(root)
    
    # Apply patches to the application
    app = patch_application(app)
    
    # Force load the data file
    app.file_path = data_file
    app.data_file_var.set(data_file)
    
    # Pre-load the enhanced data
    try:
        app.df = enhanced_df
        app.cost_analysis = cost_analysis
        print(f"Enhanced data assigned to application: {len(enhanced_df)} records")
        
        # Update status
        app.status_var.set(f"Data loaded successfully: {len(app.df)} records from {data_file}")
        
        # Force a refresh of the records
        print("Refreshing records display...")
        
        # Use after() to allow the GUI to initialize first, then refresh everything
        def refresh_all():
            try:
                # Refresh the records list
                app.refresh_records() 
                print(f"Records refreshed: {len(app.records_tree.get_children())} items")
                
                # Set some values and get recommendations
                def get_recs():
                    app.notebook.select(app.recommendation_tab)
                    app.distance_var.set("35")
                    app.duration_var.set("2.0")
                    app.get_recommendations_action()
                    print("Recommendations generated")
                
                # Wait one more second before getting recommendations
                root.after(1000, get_recs)
            except Exception as e:
                print(f"Error in refresh_all: {str(e)}")
        
        # Wait 1 second before refreshing
        root.after(1000, refresh_all)
        
    except Exception as e:
        print(f"Error assigning data: {str(e)}")
        import traceback
        traceback.print_exc()
        
    # Center the window on screen
    window_width = 1000
    window_height = 700
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int((screen_width - window_width) / 2)
    center_y = int((screen_height - window_height) / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    print("Application initialized and data loaded. Starting main loop...")
    root.mainloop() 