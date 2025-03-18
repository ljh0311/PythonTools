import pandas as pd
import numpy as np
from datetime import datetime

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

# Main function to run the recommendation system
def main():
    print("Car Rental Recommendation System")
    print("--------------------------------")
    
    # Load and preprocess data
    file_path = "22 - Sheet1.csv"
    try:
        df = load_data(file_path)
        df = preprocess_data(df)
        
        # Analyze rental costs
        cost_analysis = analyze_rental_costs(df)
        
        while True:
            try:
                # Get user input for trip details
                distance = float(input("\nEnter the planned distance (km): "))
                duration = float(input("Enter the planned duration (hours): "))
                is_weekend = input("Is this a weekend trip? (y/n): ").lower() == 'y'
                
                # Get recommendations
                recommendations = get_recommendations(distance, duration, cost_analysis, is_weekend)
                
                # Display recommendations
                print("\nTop 5 Recommended Rental Options:")
                print("--------------------------------")
                for i, rec in enumerate(recommendations, 1):
                    print(f"{i}. {rec['provider']} - {rec['car_model']}")
                    print(f"   Estimated Cost: ${rec['estimated_cost']:.2f}")
                    print(f"   Distance: {rec['distance']} km, Duration: {rec['duration']} hours")
                    print()
                
                # Ask if user wants another recommendation
                another = input("Would you like another recommendation? (y/n): ").lower()
                if another != 'y':
                    break
                    
            except ValueError:
                print("Please enter valid numeric values for distance and duration.")
            except Exception as e:
                print(f"An error occurred: {e}")
    
    except Exception as e:
        print(f"Error loading or processing data: {e}")

if __name__ == "__main__":
    main() 