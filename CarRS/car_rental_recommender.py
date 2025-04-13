import pandas as pd
import numpy as np
import os
import time
import datetime
from tabulate import tabulate  # Added for better table formatting

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
    if df is None or df.empty:
        return df
        
    # Create a copy to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Remove empty rows
    df = df.dropna(subset=['Car model'], how='all')
    
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
    numeric_cols = ['Distance (KM)', 'Fuel pumped', 'Estimated fuel usage', 
                   'Consumption (KM/L)', 'Fuel cost', 'Pumped fuel cost',
                   'Mileage cost ($0.39)', 'Cost per KM', 'Duration cost', 
                   'Total', 'Est original fuel savings', 'Rental hour', 'Cost/HR']
    
    for col in numeric_cols:
        if col in df.columns:
            try:
                df.loc[:, col] = pd.to_numeric(
                    df[col].astype(str).str.replace('$', '').str.replace('L', '').str.strip(), 
                    errors='coerce'
                )
            except Exception as e:
                print(f"Warning: Error converting column {col} - {str(e)}")
    
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
        'estimated_cost': round(total_cost, 2)
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

# Main function with improved UI
def main():
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    print("\n" + "="*60)
    print("       CAR RENTAL RECOMMENDATION SYSTEM")
    print("="*60)
    
    # Load and preprocess data
    file_path = "22 - Sheet1.csv"
    try:
        print(f"\nLoading data from {file_path}...")
        df = load_data(file_path)
        df = preprocess_data(df)
        
        # Analyze rental costs
        print("Analyzing rental costs...")
        cost_analysis = analyze_rental_costs(df)
        
        print(f"✓ Data loaded successfully: {len(df)} records found\n")
        
        while True:
            print("\n" + "="*60)
            print("MAIN MENU")
            print("="*60)
            print("1. Get Rental Recommendations")
            print("2. Manage Rental Records")
            print("3. View Rental Statistics")
            print("4. Exit")
            print("-"*60)
            
            choice = input("\nSelect an option (1-4): ")
            
            if choice == '1':
                get_recommendations_menu(df, cost_analysis)
            elif choice == '2':
                df = manage_records_menu(df)
                # Re-analyze costs after record changes
                cost_analysis = analyze_rental_costs(df)
            elif choice == '3':
                show_statistics(df)
            elif choice == '4':
                print("\nThank you for using the Car Rental Recommendation System!")
                time.sleep(1)  # Short pause before exit
                break
            else:
                print("\n❌ Invalid choice. Please try again.")
                time.sleep(1)
    
    except Exception as e:
        print(f"\n❌ Error loading or processing data: {e}")
        print("Please check that the file exists and is in the correct format.")

def get_recommendations_menu(df, cost_analysis):
    """Handle the recommendations menu with improved UI"""
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    print("\n" + "="*60)
    print("       RENTAL RECOMMENDATIONS")
    print("="*60)
    print("Enter your trip details to get personalized recommendations.")
    print("-"*60)
    
    try:
        # Get user input for trip details
        distance = float(input("\nPlanned distance (km): "))
        if distance <= 0:
            print("❌ Distance must be greater than zero.")
            input("\nPress Enter to return to menu...")
            return
            
        duration = float(input("Planned duration (hours): "))
        if duration <= 0:
            print("❌ Duration must be greater than zero.")
            input("\nPress Enter to return to menu...")
            return
            
        is_weekend = input("Is this a weekend trip? (y/n): ").lower().startswith('y')
        
        print("\nCalculating recommendations...")
        time.sleep(0.5)  # Short delay for user experience
        
        # Get recommendations
        recommendations = get_recommendations(distance, duration, cost_analysis, is_weekend, top_n=10)
        
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
        
        # Display recommendations in a nicely formatted table
        print("\n" + "="*80)
        print(f"TOP RECOMMENDATIONS FOR {distance}km, {duration} HOURS ({'WEEKEND' if is_weekend else 'WEEKDAY'})")
        print("="*80)
        
        # Prepare data for tabulate
        table_data = []
        for i, rec in enumerate(recommendations[:5], 1):
            table_data.append([
                i,
                rec['provider'],
                rec['car_model'],
                f"${rec['estimated_cost']:.2f}",
                f"${rec['hourly_cost']:.2f}",
                f"${rec['mileage_cost']:.2f}",
                f"${rec['fuel_cost']:.2f}"
            ])
        
        # Print table
        headers = ["Rank", "Provider", "Car Model", "Total Cost", "Hourly Cost", "Mileage Cost", "Fuel Cost"]
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
        
        # Additional cost breakdown for the best option
        if recommendations:
            best = recommendations[0]
            print("\n" + "-"*80)
            print(f"BEST OPTION: {best['provider']} - {best['car_model']}")
            print(f"Total Estimated Cost: ${best['estimated_cost']:.2f}")
            print("-"*80)
            print(f"Cost Breakdown:")
            print(f"  • Hourly charges: ${best['hourly_cost']:.2f} ({duration} hours)")
            print(f"  • Mileage charges: ${best['mileage_cost']:.2f} ({distance} km)")
            print(f"  • Estimated fuel cost: ${best['fuel_cost']:.2f}")
            print("-"*80)
        
    except ValueError:
        print("\n❌ Please enter valid numeric values for distance and duration.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    
    input("\nPress Enter to return to the main menu...")

def manage_records_menu(df):
    """Handle the records management menu with improved UI"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
        
        print("\n" + "="*60)
        print("       RECORDS MANAGEMENT")
        print("="*60)
        print("1. View All Records")
        print("2. Add New Record")
        print("3. Modify Existing Record")
        print("4. Delete Record")
        print("5. Search Records")
        print("6. Return to Main Menu")
        print("-"*60)
        
        choice = input("\nSelect an option (1-6): ")
        
        if choice == '1':
            view_all_records(df)
        elif choice == '2':
            df = add_new_record(df)
        elif choice == '3':
            df = modify_record(df)
        elif choice == '4':
            df = delete_record(df)
        elif choice == '5':
            search_records(df)
        elif choice == '6':
            return df
        else:
            print("\n❌ Invalid choice. Please try again.")
            time.sleep(1)

def search_records(df):
    """Search for records matching a query"""
    if df.empty:
        print("\nNo records to search.")
        input("\nPress Enter to continue...")
        return
    
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    print("\n" + "="*60)
    print("       SEARCH RECORDS")
    print("="*60)
    
    search_term = input("\nEnter search term (car model, provider, etc.): ").lower()
    
    if not search_term:
        print("No search term provided.")
        input("\nPress Enter to continue...")
        return
    
    # Search in multiple columns
    mask = df['Car model'].str.lower().str.contains(search_term, na=False) | \
           df['Car Cat'].str.lower().str.contains(search_term, na=False)
    
    # Try to search in date if it's a valid date format
    try:
        date_search = pd.to_datetime(search_term, errors='coerce')
        if not pd.isna(date_search):
            # Convert to string format for comparison
            search_date_str = date_search.strftime('%Y-%m-%d')
            # Create mask for date search
            date_mask = df['Date'].dt.strftime('%Y-%m-%d') == search_date_str
            # Combine with previous mask
            mask = mask | date_mask
    except:
        pass  # Skip date search if it fails
    
    results = df[mask]
    
    if results.empty:
        print(f"\nNo records found matching '{search_term}'.")
        input("\nPress Enter to continue...")
        return
    
    print(f"\nFound {len(results)} records matching '{search_term}':")
    
    # Display results in a table
    display_records_table(results)
    
    input("\nPress Enter to continue...")

def view_all_records(df):
    """Display all records in a formatted table"""
    if df.empty:
        print("\nNo records found.")
        input("\nPress Enter to continue...")
        return
    
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    print("\n" + "="*80)
    print("       ALL RENTAL RECORDS")
    print("="*80)
    
    # Display records in pages
    page_size = 10
    total_pages = (len(df) + page_size - 1) // page_size
    current_page = 1
    
    while True:
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(df))
        
        page_df = df.iloc[start_idx:end_idx].copy()
        
        display_records_table(page_df)
        
        print(f"\nPage {current_page} of {total_pages} | Showing records {start_idx}-{end_idx-1} of {len(df)}")
        print("\nNavigation options:")
        print("  n - Next page")
        print("  p - Previous page")
        print("  g - Go to page")
        print("  r - Return to menu")
        
        nav = input("\nEnter option: ").lower()
        
        if nav == 'n' and current_page < total_pages:
            current_page += 1
        elif nav == 'p' and current_page > 1:
            current_page -= 1
        elif nav == 'g':
            try:
                page_num = int(input(f"Enter page number (1-{total_pages}): "))
                if 1 <= page_num <= total_pages:
                    current_page = page_num
                else:
                    print(f"Page number must be between 1 and {total_pages}")
                    time.sleep(1)
            except ValueError:
                print("Invalid page number")
                time.sleep(1)
        elif nav == 'r':
            break
        
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
        print("\n" + "="*80)
        print("       ALL RENTAL RECORDS")
        print("="*80)

def display_records_table(df_subset):
    """Format and display a subset of records in a table"""
    # Prepare data for tabulate
    table_data = []
    
    for idx, row in df_subset.iterrows():
        date_str = row['Date'].strftime('%d/%m/%Y') if pd.notna(row['Date']) else 'N/A'
        car_model = str(row['Car model'])[:20] if pd.notna(row['Car model']) else 'N/A'
        provider = str(row['Car Cat']) if pd.notna(row['Car Cat']) else 'N/A'
        distance = f"{row['Distance (KM)']:.1f}" if pd.notna(row['Distance (KM)']) else 'N/A'
        rental_hour = f"{row['Rental hour']:.1f}" if pd.notna(row['Rental hour']) else 'N/A'
        total = f"${row['Total']:.2f}" if pd.notna(row['Total']) else 'N/A'
        
        table_data.append([
            idx,
            date_str,
            car_model,
            provider,
            distance,
            rental_hour,
            total
        ])
    
    # Print table
    headers = ["Index", "Date", "Car Model", "Provider", "Distance", "Hours", "Total Cost"]
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))

def show_statistics(df):
    """Show key statistics about rental data"""
    if df.empty:
        print("\nNo records to analyze.")
        input("\nPress Enter to continue...")
        return
    
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    print("\n" + "="*60)
    print("       RENTAL STATISTICS")
    print("="*60)
    
    # Basic statistics
    total_trips = len(df)
    total_distance = df['Distance (KM)'].sum()
    total_hours = df['Rental hour'].sum()
    total_cost = df['Total'].sum()
    
    print(f"\nOverall Statistics:")
    print(f"  • Total number of trips: {total_trips}")
    print(f"  • Total distance traveled: {total_distance:.1f} km")
    print(f"  • Total rental duration: {total_hours:.1f} hours")
    print(f"  • Total spending: ${total_cost:.2f}")
    
    if total_trips > 0:
        print(f"\nAverage per Trip:")
        print(f"  • Average distance: {total_distance/total_trips:.1f} km")
        print(f"  • Average duration: {total_hours/total_trips:.1f} hours")
        print(f"  • Average cost: ${total_cost/total_trips:.2f}")
    
    # Provider statistics
    if 'Car Cat' in df.columns:
        print("\nBy Provider:")
        provider_stats = df.groupby('Car Cat').agg({
            'Total': ['count', 'sum', 'mean'],
            'Distance (KM)': 'sum',
            'Rental hour': 'sum'
        })
        
        for provider, stats in provider_stats.iterrows():
            trip_count = stats[('Total', 'count')]
            total_provider_cost = stats[('Total', 'sum')]
            avg_cost = stats[('Total', 'mean')]
            
            print(f"\n  {provider}:")
            print(f"    - Trips: {trip_count}")
            print(f"    - Total cost: ${total_provider_cost:.2f}")
            print(f"    - Average cost: ${avg_cost:.2f}")
    
    # Most used car models (top 5)
    if 'Car model' in df.columns and len(df) > 0:
        print("\nMost Used Car Models:")
        model_counts = df['Car model'].value_counts().head(5)
        
        for model, count in model_counts.items():
            print(f"  • {model}: {count} trips")
    
    input("\nPress Enter to return to the main menu...")

def add_new_record(df):
    """Add a new rental record with improved UI"""
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
    
    print("\n" + "="*60)
    print("       ADD NEW RENTAL RECORD")
    print("="*60)
    print("Enter the details for the new rental record.")
    print("Fields marked with * are required.")
    print("-"*60)
    
    try:
        # Get basic record information with better input handling
        date_str = input("* Date (DD/MM/YYYY): ")
        car_model = input("* Car Model: ")
        
        # Provider selection with numbering
        print("\nSelect Provider:")
        providers = ["Getgo", "Car Club", "Econ", "Stand"]
        for i, p in enumerate(providers, 1):
            print(f"{i}. {p}")
        
        provider_choice = input("* Enter number (1-4): ")
        try:
            provider = providers[int(provider_choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice. Using 'Other' as provider.")
            provider = "Other"
        
        # Continue with other fields
        distance = input("* Distance (KM): ")
        hours = input("* Rental Hours: ")
        
        # Weekend selection with numbering
        print("\nWeekday or Weekend:")
        print("1. Weekday")
        print("2. Weekend")
        weekend_choice = input("Enter number (1-2): ")
        weekend = "weekend" if weekend_choice == "2" else "weekday"
        
        total_cost = input("* Total Cost ($): ")
        
        # Optional fields with clearer labels
        print("\nOptional Fields (leave blank if unknown):")
        fuel_pumped = input("Fuel Pumped (L): ")
        fuel_usage = input("Estimated Fuel Usage (L): ")
        pumped_cost = input("Pumped Fuel Cost ($): ")
        cost_per_km = input("Cost per KM ($): ")
        duration_cost = input("Duration Cost ($): ")
        consumption = input("Consumption (KM/L): ")
        fuel_savings = input("Estimated Fuel Savings ($): ")
        cost_per_hr = input("Cost per Hour ($): ")
        
        # Validate required fields
        if not all([date_str, car_model, provider, distance, hours, total_cost]):
            print("\n❌ All required fields must be filled.")
            input("\nPress Enter to continue...")
            return df
        
        # Parse date
        try:
            date = pd.to_datetime(date_str, format='%d/%m/%Y')
        except:
            print("\n❌ Invalid date format. Using today's date.")
            date = pd.Timestamp.now()
        
        # Parse numeric fields with better error handling
        try:
            distance = float(distance)
            hours = float(hours)
            total_cost = float(total_cost)
            
            # Optional numeric fields
            fuel_pumped = float(fuel_pumped) if fuel_pumped else None
            fuel_usage = float(fuel_usage) if fuel_usage else None
            pumped_cost = float(pumped_cost) if pumped_cost else None
            cost_per_km = float(cost_per_km) if cost_per_km else None
            duration_cost = float(duration_cost) if duration_cost else None
            consumption = float(consumption) if consumption else None
            fuel_savings = float(fuel_savings) if fuel_savings else None
            cost_per_hr = float(cost_per_hr) if cost_per_hr else None
        except ValueError:
            print("\n❌ Invalid numeric value. Please enter numbers only.")
            input("\nPress Enter to continue...")
            return df
        
        # Create new record
        new_record = {
            'Date': date,
            'Car model': car_model,
            'Car Cat': provider,
            'Distance (KM)': distance,
            'Rental hour': hours,
            'Fuel pumped': f"{fuel_pumped} L" if fuel_pumped is not None else None,
            'Estimated fuel usage': fuel_usage,
            'Consumption (KM/L)': consumption,
            'Fuel cost': None,  # This could be calculated
            'Pumped fuel cost': f"${pumped_cost}" if pumped_cost is not None else None,
            'Mileage cost ($0.39)': None,  # This could be calculated
            'Cost per KM': cost_per_km,
            'Duration cost': duration_cost,
            'Total': total_cost,
            'Est original fuel savings': fuel_savings,
            'Weekday/weekend': weekend,
            'Cost/HR': cost_per_hr
        }
        
        # Preview the record before adding
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
        
        print("\n" + "="*60)
        print("       RECORD PREVIEW")
        print("="*60)
        
        print(f"\nDate: {date.strftime('%d/%m/%Y')}")
        print(f"Car Model: {car_model}")
        print(f"Provider: {provider}")
        print(f"Distance: {distance} km")
        print(f"Duration: {hours} hours")
        print(f"Weekend/Weekday: {weekend}")
        print(f"Total Cost: ${total_cost}")
        
        confirm = input("\nAdd this record? (y/n): ").lower()
        
        if confirm == 'y':
            # Add to dataframe
            df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
            
            # Save the updated dataframe
            df.to_csv("22 - Sheet1.csv", index=False)
            
            print("\n✓ Record added successfully!")
        else:
            print("\nRecord addition cancelled.")
        
    except Exception as e:
        print(f"\n❌ Error adding record: {e}")
    
    input("\nPress Enter to continue...")
    return df

def modify_record(df):
    """Modify an existing rental record with improved UI"""
    if df.empty:
        print("\nNo records to modify.")
        return df
    
    # Show all records first
    view_all_records(df)
    
    try:
        # Get record index to modify
        idx = int(input("\nEnter the index of the record to modify: "))
        
        # Validate index
        if idx < 0 or idx >= len(df):
            print(f"Invalid index. Please enter a value between 0 and {len(df)-1}.")
            return df
        
        # Get current values for the record
        record = df.iloc[idx]
        
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen
        
        print("\n" + "="*60)
        print("       MODIFY RENTAL RECORD")
        print("="*60)
        print(f"Current values for record {idx}:")
        print(f"Date: {record['Date'].strftime('%d/%m/%Y')}")
        # Get updated values with current values as defaults
        date_str = input(f"Date ({record['Date'].strftime('%d/%m/%Y')} if pd.notna(record['Date']) else 'N/A'): ")
        car_model = input(f"Car Model ({record['Car model']} if pd.notna(record['Car model']) else 'N/A'): ")
        provider = input(f"Provider ({record['Car Cat']} if pd.notna(record['Car Cat']) else 'N/A'): ")
        distance = input(f"Distance (KM) ({record['Distance (KM)']:.2f} if pd.notna(record['Distance (KM)']) else 'N/A'): ")
        hours = input(f"Rental Hours ({record['Rental hour']:.2f} if pd.notna(record['Rental hour']) else 'N/A'): ")
        fuel_pumped = input(f"Fuel Pumped (L) ({str(record['Fuel pumped']).replace(' L', '')} if pd.notna(record['Fuel pumped']) else 'N/A'): ")
        fuel_usage = input(f"Estimated Fuel Usage (L) ({record['Estimated fuel usage']} if pd.notna(record['Estimated fuel usage']) else 'N/A'): ")
        weekend = input(f"Weekend or Weekday ({record['Weekday/weekend']} if pd.notna(record['Weekday/weekend']) else 'N/A'): ")
        total_cost = input(f"Total Cost ($) ({record['Total']:.2f} if pd.notna(record['Total']) else 'N/A'): ")
        
        # Process the inputs - use original values if fields are left blank
        if date_str:
            try:
                df.at[idx, 'Date'] = pd.to_datetime(date_str, format='%d/%m/%Y')
            except:
                print("Invalid date format. Keeping original value.")
        
        if car_model:
            df.at[idx, 'Car model'] = car_model
        
        if provider:
            df.at[idx, 'Car Cat'] = provider
        
        if distance:
            try:
                df.at[idx, 'Distance (KM)'] = float(distance)
            except:
                print("Invalid distance value. Keeping original value.")
        
        if hours:
            try:
                df.at[idx, 'Rental hour'] = float(hours)
            except:
                print("Invalid hours value. Keeping original value.")
        
        if fuel_pumped:
            try:
                df.at[idx, 'Fuel pumped'] = f"{float(fuel_pumped)} L"
            except:
                print("Invalid fuel pumped value. Keeping original value.")
        
        if fuel_usage:
            try:
                df.at[idx, 'Estimated fuel usage'] = float(fuel_usage)
            except:
                print("Invalid fuel usage value. Keeping original value.")
        
        if weekend:
            df.at[idx, 'Weekday/weekend'] = weekend
        
        if total_cost:
            try:
                df.at[idx, 'Total'] = float(total_cost)
            except:
                print("Invalid total cost value. Keeping original value.")
        
        # Save the updated dataframe
        df.to_csv("22 - Sheet1.csv", index=False)
        
        print("\nRecord updated successfully!")
        
    except ValueError:
        print("\nError: Please enter a valid index number.")
    except Exception as e:
        print(f"\nError modifying record: {e}")
    
    return df

def delete_record(df):
    """Delete a rental record"""
    if df.empty:
        print("\nNo records to delete.")
        return df
    
    # Show all records first
    view_all_records(df)
    
    try:
        # Get record index to delete
        idx = int(input("\nEnter the index of the record to delete: "))
        
        # Validate index
        if idx < 0 or idx >= len(df):
            print(f"Invalid index. Please enter a value between 0 and {len(df)-1}.")
            return df
        
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete record {idx}? (y/n): ").lower()
        if confirm != 'y':
            print("Deletion cancelled.")
            return df
        
        # Delete the record
        df = df.drop(idx).reset_index(drop=True)
        
        # Save the updated dataframe
        df.to_csv("22 - Sheet1.csv", index=False)
        
        print("\nRecord deleted successfully!")
        
    except ValueError:
        print("\nError: Please enter a valid index number.")
    except Exception as e:
        print(f"\nError deleting record: {e}")
    
    return df

if __name__ == "__main__":
    main() 