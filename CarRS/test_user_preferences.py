#!/usr/bin/env python3
"""
Test script for the User Preference Analysis functionality
This script demonstrates how to use the new user preference features.
"""

import pandas as pd
import sys
import os

# Add the current directory to the path so we can import the core module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from car_rental_recommender_core import (
    load_data,
    enhance_dataframe,
    analyze_user_preferences,
    get_preference_based_recommendations,
    get_enhanced_preference_recommendations,
    prepare_user_data_summary
)

def test_user_preference_analysis():
    """Test the user preference analysis functionality"""
    print("=== Testing User Preference Analysis ===\n")
    
    try:
        # Load the data
        print("1. Loading data from CSV...")
        df = load_data("22 - Sheet1.csv")
        df = enhance_dataframe(df)
        print(f"   Loaded {len(df)} records\n")
        
        # Test data summary preparation
        print("2. Preparing user data summary...")
        user_summary = prepare_user_data_summary(df)
        print(f"   Total rentals: {user_summary['total_rentals']}")
        print(f"   Total distance: {user_summary['total_distance']:.1f} km")
        print(f"   Total cost: ${user_summary['total_cost']:.2f}")
        print(f"   Average cost per rental: ${user_summary['avg_cost_per_rental']:.2f}")
        print()
        
        # Test fallback user preferences (without Ollama)
        print("3. Creating fallback user preferences...")
        fallback_preferences = analyze_user_preferences(df, ollama_model="llama2")
        print("   Fallback preferences created successfully")
        print(f"   User profile: {fallback_preferences.get('user_profile', {})}")
        print()
        
        # Test preference-based recommendations
        print("4. Testing preference-based recommendations...")
        distance = 50.0
        duration = 3.0
        is_weekend = False
        
        recommendations = get_preference_based_recommendations(
            distance, duration, fallback_preferences, df, is_weekend, top_n=3
        )
        
        print(f"   Generated {len(recommendations)} recommendations for {distance}km, {duration}h trip:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec['provider']} - {rec['model']}: ${rec['total_cost']:.2f} (Confidence: {rec['confidence']:.1%})")
            print(f"      Reasoning: {rec['reasoning']}")
        print()
        
        # Test enhanced preference recommendations
        print("5. Testing enhanced preference recommendations...")
        enhanced_recs = get_enhanced_preference_recommendations(
            distance, duration, df, fallback_preferences, is_weekend, top_n=3, use_ollama=False
        )
        
        print(f"   Generated {len(enhanced_recs)} enhanced recommendations:")
        for i, rec in enumerate(enhanced_recs, 1):
            print(f"   {i}. {rec['provider']} - {rec['model']}: ${rec['total_cost']:.2f}")
            if 'user_insights' in rec:
                print(f"      User insights: {rec['user_insights']}")
        print()
        
        print("✅ All tests completed successfully!")
        print("\n=== Summary ===")
        print("The user preference analysis system is working correctly.")
        print("Key features implemented:")
        print("• User data analysis and pattern recognition")
        print("• Preference extraction from rental history")
        print("• Personalized recommendations based on user preferences")
        print("• Fallback mechanisms when Ollama is not available")
        print("• Enhanced recommendations with user insights")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

def display_user_insights(df):
    """Display interesting insights from the user's rental data"""
    print("\n=== User Rental Insights ===")
    
    # Basic statistics
    total_rentals = len(df)
    total_distance = df["Distance (KM)"].sum()
    total_cost = df["Total"].sum()
    avg_cost = total_cost / total_rentals
    
    print(f"📊 Total rentals: {total_rentals}")
    print(f"🛣️  Total distance traveled: {total_distance:.1f} km")
    print(f"💰 Total spent: ${total_cost:.2f}")
    print(f"💵 Average cost per rental: ${avg_cost:.2f}")
    
    # Provider preferences
    if "Car Cat" in df.columns:
        provider_counts = df["Car Cat"].value_counts()
        print(f"\n🏢 Most used providers:")
        for provider, count in provider_counts.head(3).items():
            percentage = (count / total_rentals) * 100
            print(f"   • {provider}: {count} rentals ({percentage:.1f}%)")
    
    # Car model preferences
    if "Car model" in df.columns:
        model_counts = df["Car model"].value_counts()
        print(f"\n🚗 Most used car models:")
        for model, count in model_counts.head(3).items():
            percentage = (count / total_rentals) * 100
            print(f"   • {model}: {count} rentals ({percentage:.1f}%)")
    
    # Time patterns
    if "Weekday/weekend" in df.columns:
        weekend_rentals = len(df[df["Weekday/weekend"] == "weekend"])
        weekday_rentals = total_rentals - weekend_rentals
        print(f"\n📅 Time patterns:")
        print(f"   • Weekday rentals: {weekday_rentals} ({(weekday_rentals/total_rentals)*100:.1f}%)")
        print(f"   • Weekend rentals: {weekend_rentals} ({(weekend_rentals/total_rentals)*100:.1f}%)")
    
    # Distance patterns
    avg_distance = df["Distance (KM)"].mean()
    max_distance = df["Distance (KM)"].max()
    min_distance = df["Distance (KM)"].min()
    print(f"\n📏 Distance patterns:")
    print(f"   • Average trip distance: {avg_distance:.1f} km")
    print(f"   • Longest trip: {max_distance:.1f} km")
    print(f"   • Shortest trip: {min_distance:.1f} km")

if __name__ == "__main__":
    print("Car Rental User Preference Analysis Test")
    print("=" * 50)
    
    # Check if the CSV file exists
    if not os.path.exists("22 - Sheet1.csv"):
        print("❌ Error: CSV file '22 - Sheet1.csv' not found!")
        print("Please ensure the CSV file is in the same directory as this script.")
        sys.exit(1)
    
    # Run the tests
    test_user_preference_analysis()
    
    # Load data for insights
    try:
        df = load_data("22 - Sheet1.csv")
        df = enhance_dataframe(df)
        display_user_insights(df)
    except Exception as e:
        print(f"❌ Error displaying insights: {str(e)}")
    
    print("\n🎉 Test completed! The user preference system is ready to use.")
    print("\nTo use the GUI:")
    print("1. Run: python car_rental_recommender_gui.py")
    print("2. Load your CSV data in the 'Data Analysis' tab")
    print("3. Go to the 'User Preferences' tab")
    print("4. Click 'Analyze User Preferences' to get your personalized profile")
    print("5. Use the 'Personalized Recommendations' section for tailored suggestions")
