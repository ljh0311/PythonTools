import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from car_rental_recommender_gui import OllamaHelper

class CarSharingCostPlanner:
    def __init__(self):
        self.ollama_helper = OllamaHelper()
        self.providers = {
            'Getgo': {
                'mileage_rate': 0.39,
                'hourly_rate': 8.0,
                'name': 'Getgo'
            },
            'Car Club': {
                'mileage_rate': 0.33,
                'hourly_rate': 8.0,
                'name': 'Car Club'
            },
            'Zipzap': {
                'mileage_rate': 0.0,
                'hourly_rate': 0.0,
                'monthly_fee': 2000,
                'name': 'Zipzap'
            }
        }

    def calculate_required_mileage(self, target_cost, duration, provider='Getgo'):
        if provider == 'Zipzap':
            return None
        provider_data = self.providers[provider]
        mileage_rate = provider_data['mileage_rate']
        hourly_rate = provider_data['hourly_rate']
        duration_cost = duration * hourly_rate
        if duration_cost >= target_cost:
            return None
        required_mileage = (target_cost - duration_cost) / mileage_rate
        return max(0, required_mileage)

    def calculate_required_duration(self, target_cost, mileage, provider='Getgo'):
        if provider == 'Zipzap':
            return {
                'days': 0,
                'hours': 0,
                'minutes': 0,
                'total_hours': 0,
                'impossible': True,
                'reason': f"Zipzap is a fixed monthly subscription of ${self.providers['Zipzap']['monthly_fee']:.2f}"
            }
        provider_data = self.providers[provider]
        mileage_rate = provider_data['mileage_rate']
        hourly_rate = provider_data['hourly_rate']
        mileage_cost = mileage * mileage_rate
        if mileage_cost >= target_cost:
            return {
                'days': 0,
                'hours': 0,
                'minutes': 0,
                'total_hours': 0,
                'impossible': True,
                'reason': f"Mileage cost (${mileage_cost:.2f}) exceeds target cost (${target_cost:.2f})"
            }
        required_hours = (target_cost - mileage_cost) / hourly_rate
        required_hours = max(0, required_hours)
        total_minutes = int(round(required_hours * 60))
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60
        minute_options = [0, 15, 30, 45]
        minutes = min(minute_options, key=lambda x: abs(x - minutes))
        if minutes == 60:
            minutes = 0
            hours += 1
            if hours == 24:
                hours = 0
                days += 1
        # Use OllamaHelper for LLM-based explanation
        try:
            prompt = (
                f"Given a target cost of ${target_cost:.2f}, mileage {mileage} km, and provider {provider}, "
                "calculate the required rental duration (in hours, days, minutes) to not exceed the budget. "
                "Provider rates: mileage_rate=${:.2f}/km, hourly_rate=${:.2f}/hr. "
                "Return a JSON object with days, hours, minutes, total_hours, impossible (bool), and a brief reason."
            ).format(mileage_rate, hourly_rate)
            llm_result = self.ollama_helper.get_ollama_and_ml_recommendations(
                distance=mileage,
                duration=None,
                df=None,
                cost_analysis=None,
                is_weekend=False,
                top_n=1
            )
            # If LLM returns a valid dict, use it; else, fallback to local calculation
            if isinstance(llm_result, list) and llm_result and isinstance(llm_result[0], dict):
                return llm_result[0]
        except Exception:
            pass
        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'total_hours': required_hours,
            'impossible': False,
            'reason': f"Calculated using rates: ${mileage_rate:.2f}/km, ${hourly_rate:.2f}/hr"
        }

    def generate_booking_scenarios(self, target_cost, duration=None, mileage=None, provider='Getgo'):
        scenarios = []
        if provider == 'Zipzap':
            scenarios.append({
                'bookings_per_week': 'Unlimited',
                'total_hours_per_month': 'Unlimited',
                'km_per_booking': 'Unlimited',
                'hours_per_booking': 'Unlimited',
                'type': 'subscription',
                'note': f'Fixed monthly subscription of ${self.providers["Zipzap"]["monthly_fee"]:.2f}'
            })
            return scenarios
        if duration is not None:
            required_mileage = self.calculate_required_mileage(target_cost, duration, provider)
            if required_mileage is None or required_mileage <= 0:
                return scenarios
            for bookings_per_week in range(1, 21):
                total_bookings_per_month = bookings_per_week * 4
                km_per_booking = required_mileage / total_bookings_per_month
                hours_per_booking_by_km = km_per_booking / 30
                if hours_per_booking_by_km < 1:
                    continue
                minute_options = [0, 0.25, 0.5, 0.75]
                fractional = hours_per_booking_by_km % 1
                rounded_fractional = min(minute_options, key=lambda x: abs(x - fractional))
                rounded_hours = int(hours_per_booking_by_km) + rounded_fractional
                if abs(rounded_hours - hours_per_booking_by_km) < 0.13:
                    total_hours_per_month = rounded_hours * total_bookings_per_month
                    if total_hours_per_month <= duration:
                        scenarios.append({
                            'bookings_per_week': bookings_per_week,
                            'total_hours_per_month': total_hours_per_month,
                            'km_per_booking': km_per_booking,
                            'hours_per_booking': rounded_hours,
                            'type': 'duration_based'
                        })
        if mileage is not None:
            required_duration = self.calculate_required_duration(target_cost, mileage, provider)
            if required_duration is None or required_duration.get('impossible'):
                return scenarios
            total_hours = required_duration['total_hours']
            for bookings_per_week in range(1, 21):
                total_bookings_per_month = bookings_per_week * 4
                hours_per_booking = total_hours / total_bookings_per_month
                decimal_part = round(hours_per_booking % 1, 2)
                if decimal_part in {0.0, 0.25, 0.5, 0.75}:
                    km_per_booking_by_hours = hours_per_booking * 30
                    scenarios.append({
                        'bookings_per_week': bookings_per_week,
                        'total_hours_per_month': total_hours,
                        'km_per_booking': km_per_booking_by_hours,
                        'hours_per_booking': hours_per_booking,
                        'type': 'mileage_based'
                    })
        return scenarios

    def calculate_cost_breakdown(self, mileage, duration, provider='Getgo'):
        if provider == 'Zipzap':
            return {
                'mileage_cost': 0,
                'duration_cost': 0,
                'total_cost': self.providers['Zipzap']['monthly_fee'],
                'mileage_rate': 0,
                'hourly_rate': 0,
                'note': 'Fixed monthly subscription'
            }
        provider_data = self.providers[provider]
        mileage_rate = provider_data['mileage_rate']
        hourly_rate = provider_data['hourly_rate']
        mileage_cost = mileage * mileage_rate
        duration_cost = duration * hourly_rate
        total_cost = mileage_cost + duration_cost
        return {
            'mileage_cost': mileage_cost,
            'duration_cost': duration_cost,
            'total_cost': total_cost,
            'mileage_rate': mileage_rate,
            'hourly_rate': hourly_rate
        }

    def compare_providers(self, target_cost):
        comparisons = {}
        for provider_name, provider_data in self.providers.items():
            if provider_name == 'Zipzap':
                comparisons[provider_name] = {
                    'monthly_cost': provider_data['monthly_fee'],
                    'mileage_limit': 'Unlimited',
                    'duration_limit': 'Unlimited',
                    'cost_per_km': 'N/A',
                    'cost_per_hour': 'N/A',
                    'note': 'Fixed monthly subscription'
                }
            else:
                avg_hours_per_booking = 3
                avg_km_per_booking = 90
                bookings_per_month = 4
                total_hours = avg_hours_per_booking * bookings_per_month
                total_mileage = avg_km_per_booking * bookings_per_month
                breakdown = self.calculate_cost_breakdown(total_mileage, total_hours, provider_name)
                comparisons[provider_name] = {
                    'monthly_cost': breakdown['total_cost'],
                    'mileage_limit': f"{total_mileage:.0f} km",
                    'duration_limit': f"{total_hours:.0f} hours",
                    'cost_per_km': f"${provider_data['mileage_rate']:.2f}",
                    'cost_per_hour': f"${provider_data['hourly_rate']:.2f}",
                    'note': f"Based on {bookings_per_month} bookings/month"
                }
        return comparisons
def main():
    planner = CarSharingCostPlanner()
    print("=" * 60)
    print("CAR SHARING COST PLANNER")
    print("=" * 60)
    print()
    while True:
        print("\nChoose an option:")
        print("1. Calculate travel distance/duration for your budget")
        print("2. Generate booking scenarios for your budget")
        print("3. Compare different providers")
        print("4. Exit")
        choice = input("\nEnter your choice (1-4): ").strip()
        if choice == '1':
            print("\n" + "=" * 50)
            print("CALCULATE TRAVEL CAPACITY FOR YOUR BUDGET")
            print("=" * 50)
            try:
                budget = float(input("Enter your monthly budget ($): "))
                provider = input("Enter provider (Getgo/Car Club/Zipzap): ").strip()
                if provider not in planner.providers:
                    print("Invalid provider. Using Getgo as default.")
                    provider = 'Getgo'
                print(f"\nResults for ${budget:.2f} budget with {provider}:")
                print("-" * 50)
                if provider == 'Zipzap':
                    print(f"Zipzap: Fixed monthly subscription of ${planner.providers['Zipzap']['monthly_fee']:.2f}")
                    print("✓ Unlimited mileage")
                    print("✓ Unlimited duration")
                    print("✓ No per-hour or per-km charges")
                else:
                    scenarios = [
                        {'hours': 50, 'description': 'Light usage (50 hours/month)'},
                        {'hours': 100, 'description': 'Moderate usage (100 hours/month)'},
                        {'hours': 150, 'description': 'Heavy usage (150 hours/month)'}
                    ]
                    for scenario in scenarios:
                        hours = scenario['hours']
                        mileage = planner.calculate_required_mileage(budget, hours, provider)
                        if mileage is not None:
                            print(f"\n{scenario['description']}:")
                            print(f"  • Duration: {hours} hours")
                            print(f"  • Mileage: {mileage:.0f} km")
                            print(f"  • Cost breakdown:")
                            breakdown = planner.calculate_cost_breakdown(mileage, hours, provider)
                            print(f"    - Mileage cost: ${breakdown['mileage_cost']:.2f}")
                            print(f"    - Duration cost: ${breakdown['duration_cost']:.2f}")
                            print(f"    - Total: ${breakdown['total_cost']:.2f}")
                        else:
                            print(f"\n{scenario['description']}: Not possible with this budget")
            except ValueError:
                print("Invalid input. Please enter a valid number.")
        elif choice == '2':
            print("\n" + "=" * 50)
            print("GENERATE BOOKING SCENARIOS")
            print("=" * 50)
            try:
                budget = float(input("Enter your monthly budget ($): "))
                provider = input("Enter provider (Getgo/Car Club/Zipzap): ").strip()
                if provider not in planner.providers:
                    print("Invalid provider. Using Getgo as default.")
                    provider = 'Getgo'
                calc_type = input("Calculate based on (1) Duration or (2) Mileage? Enter 1 or 2: ").strip()
                print(f"\nBooking scenarios for ${budget:.2f} budget with {provider}:")
                print("-" * 70)
                if calc_type == '1':
                    duration = float(input("Enter target duration (hours/month): "))
                    scenarios = planner.generate_booking_scenarios(budget, duration=duration, provider=provider)
                    print(f"{'Bookings/Week':<15} {'Hours/Booking':<15} {'Km/Booking':<15} {'Total Hours/Month':<20}")
                    print("-" * 70)
                    for scenario in scenarios:
                        if scenario['type'] == 'subscription':
                            print(f"{scenario['bookings_per_week']:<15} {scenario['hours_per_booking']:<15} {scenario['km_per_booking']:<15} {scenario['total_hours_per_month']:<20}")
                            print(f"Note: {scenario['note']}")
                        else:
                            print(f"{scenario['bookings_per_week']:<15} {scenario['hours_per_booking']:<15.2f} {scenario['km_per_booking']:<15.2f} {scenario['total_hours_per_month']:<20.2f}")
                elif calc_type == '2':
                    mileage = float(input("Enter target mileage (km/month): "))
                    scenarios = planner.generate_booking_scenarios(budget, mileage=mileage, provider=provider)
                    print(f"{'Bookings/Week':<15} {'Hours/Booking':<15} {'Km/Booking':<15} {'Total Hours/Month':<20}")
                    print("-" * 70)
                    for scenario in scenarios:
                        if scenario['type'] == 'subscription':
                            print(f"{scenario['bookings_per_week']:<15} {scenario['hours_per_booking']:<15} {scenario['km_per_booking']:<15} {scenario['total_hours_per_month']:<20}")
                            print(f"Note: {scenario['note']}")
                        else:
                            print(f"{scenario['bookings_per_week']:<15} {scenario['hours_per_booking']:<15.2f} {scenario['km_per_booking']:<15.2f} {scenario['total_hours_per_month']:<20.2f}")
                else:
                    print("Invalid choice. Please enter 1 or 2.")
            except ValueError:
                print("Invalid input. Please enter valid numbers.")
        elif choice == '3':
            print("\n" + "=" * 50)
            print("PROVIDER COMPARISON")
            print("=" * 50)
            try:
                budget = float(input("Enter your monthly budget ($): "))
                comparisons = planner.compare_providers(budget)
                print(f"\nProvider comparison for ${budget:.2f} budget:")
                print("-" * 80)
                print(f"{'Provider':<12} {'Monthly Cost':<15} {'Mileage Limit':<15} {'Duration Limit':<15} {'Cost/Km':<10} {'Cost/Hour':<10}")
                print("-" * 80)
                for provider, data in comparisons.items():
                    print(f"{provider:<12} ${data['monthly_cost']:<14.2f} {data['mileage_limit']:<15} {data['duration_limit']:<15} {data['cost_per_km']:<10} {data['cost_per_hour']:<10}")
                    if 'note' in data:
                        print(f"  Note: {data['note']}")
            except ValueError:
                print("Invalid input. Please enter a valid number.")
        elif choice == '4':
            print("\nThank you for using the Car Sharing Cost Planner!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
if __name__ == "__main__":
    main()
