#!/usr/bin/env python3
"""
Simple GUI to display car rental recommendations and their reasoning, with Ollama integration.
"""

import sys
import os
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure the current directory is in the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from car_rental_recommender_core import (
    get_ollama_enhanced_recommendations,
    create_fallback_recommendations
)

class RecommendationGUI:
    def __init__(self, master):
        self.master = master
        master.title("Car Rental Recommendations (with Reasoning)")
        master.geometry("700x480")

        # Input frame for user parameters
        input_frame = ttk.Frame(master, padding=10)
        input_frame.pack(fill='x')

        ttk.Label(input_frame, text="Distance (km):").grid(row=0, column=0, sticky='w')
        self.distance_var = tk.StringVar(value="50")
        ttk.Entry(input_frame, textvariable=self.distance_var, width=8).grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Duration (hours):").grid(row=0, column=2, sticky='w')
        self.duration_var = tk.StringVar(value="2")
        ttk.Entry(input_frame, textvariable=self.duration_var, width=8).grid(row=0, column=3, padx=5)

        self.weekend_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="Weekend?", variable=self.weekend_var).grid(row=0, column=4, padx=10)

        # Option to use Ollama or fallback
        self.use_ollama_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_frame, text="Use Ollama (AI)", variable=self.use_ollama_var).grid(row=0, column=5, padx=10)

        ttk.Button(input_frame, text="Get Recommendations", command=self.get_recommendations).grid(row=0, column=6, padx=10)

        # Treeview for displaying recommendations
        columns = ("provider", "model", "total_cost", "method", "reasoning")
        self.tree = ttk.Treeview(master, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=120 if col != "reasoning" else 250, anchor='w')
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)

        # Bind double-click to show reasoning popup
        self.tree.bind("<Double-1>", self.show_reasoning_popup)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(master, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill='x', side='bottom')

        # Load sample data for enhanced recommendations
        self.df = self.load_sample_data()

    def load_sample_data(self):
        """
        Load sample data from 22 - Sheet1.csv for enhanced recommendations.
        Returns a DataFrame or an empty DataFrame on failure.
        """
        csv_path = os.path.join(os.path.dirname(__file__), "22 - Sheet1.csv")
        try:
            sample_data = pd.read_csv(csv_path)
            # Only keep relevant columns and a few rows for demo
            sample_data = sample_data[[
                'Car Cat',
                'Car model',
                'Cost per KM',
                'Cost/HR',
                'Consumption (KM/L)',
                'Weekday/weekend'
            ]].head(6)
            return sample_data
        except Exception as e:
            messagebox.showerror("Error", f"Could not load sample data: {e}")
            return pd.DataFrame()

    def get_recommendations(self):
        """
        Get and display recommendations, using Ollama if enabled, otherwise fallback.
        """
        try:
            distance = float(self.distance_var.get())
            duration = float(self.duration_var.get())
            is_weekend = self.weekend_var.get()
        except ValueError:
            self.status_var.set("Please enter valid numbers for distance and duration.")
            return

        self.status_var.set("Getting recommendations...")
        self.tree.delete(*self.tree.get_children())

        use_ollama = self.use_ollama_var.get()

        # Always show fallback recommendations for comparison
        fallback_recs = create_fallback_recommendations(distance, duration, is_weekend)

        # Try to get Ollama recommendations if enabled, fallback if error
        enhanced_recs = []
        ollama_error = None
        if use_ollama:
            try:
                enhanced_recs = get_ollama_enhanced_recommendations(
                    distance, duration, self.df, None, is_weekend, 5, use_ollama=True, use_ml=False
                )
                if not enhanced_recs:
                    ollama_error = "No Ollama recommendations returned."
            except Exception as e:
                ollama_error = f"Ollama error: {e}"
        else:
            # If Ollama not enabled, use fallback as "enhanced" for demo
            enhanced_recs = get_ollama_enhanced_recommendations(
                distance, duration, self.df, None, is_weekend, 5, use_ollama=False, use_ml=False
            )

        # Insert fallback recommendations
        for rec in fallback_recs:
            method = rec.get('method', None)
            if not method or method == "Standard":
                provider = rec.get('provider', '').lower()
                if provider == 'getgo':
                    method = "Getgo Standard"
                elif provider == 'car club':
                    method = "Car Club Standard"
                elif provider == 'zipzap':
                    method = "Zipzap Subscription"
                else:
                    method = "Fallback"
            self.tree.insert("", "end", values=(
                rec.get('provider', ''),
                rec.get('model', ''),
                f"${rec.get('total_cost', 0):.2f}",
                method,
                rec.get('reasoning', 'No reasoning')
            ))

        # Insert enhanced/Ollama recommendations
        if use_ollama and ollama_error:
            # Show error row if Ollama failed
            self.tree.insert("", "end", values=(
                "Ollama", "", "", "Ollama Error", ollama_error
            ))
        else:
            for rec in enhanced_recs:
                method = rec.get('method', None)
                if not method or method == "Standard":
                    provider = rec.get('provider', '').lower()
                    if provider == 'getgo':
                        method = "Getgo (Ollama)"
                    elif provider == 'car club':
                        method = "Car Club (Ollama)"
                    elif provider == 'zipzap':
                        method = "Zipzap Subscription"
                    else:
                        method = "Ollama"
                self.tree.insert("", "end", values=(
                    rec.get('provider', ''),
                    rec.get('model', ''),
                    f"${rec.get('total_cost', 0):.2f}",
                    method,
                    rec.get('reasoning', 'No reasoning')
                ))

        total_displayed = len(fallback_recs) + (len(enhanced_recs) if not ollama_error else 1)
        self.status_var.set(f"Displayed {total_displayed} recommendations.")

    def show_reasoning_popup(self, event):
        """
        Show a popup window with detailed reasoning for the selected recommendation.
        """
        item = self.tree.identify_row(event.y)
        if not item:
            return
        values = self.tree.item(item, "values")
        if len(values) < 5:
            return
        provider, model, total_cost, method, reasoning = values
        popup = tk.Toplevel(self.master)
        popup.title(f"Reasoning for {provider} - {model}")
        popup.geometry("450x250")
        ttk.Label(popup, text=f"Provider: {provider}", font=("Arial", 11, "bold")).pack(anchor='w', padx=10, pady=5)
        ttk.Label(popup, text=f"Model: {model}", font=("Arial", 11)).pack(anchor='w', padx=10)
        ttk.Label(popup, text=f"Total Cost: {total_cost}", font=("Arial", 11)).pack(anchor='w', padx=10)
        ttk.Label(popup, text=f"Method: {method}", font=("Arial", 11)).pack(anchor='w', padx=10)
        ttk.Label(popup, text="Reasoning:", font=("Arial", 11, "underline")).pack(anchor='w', padx=10, pady=(10,0))
        reasoning_text = tk.Text(popup, wrap="word", height=6, width=50)
        reasoning_text.insert("1.0", reasoning)
        reasoning_text.config(state="disabled")
        reasoning_text.pack(padx=10, pady=5, fill='both', expand=True)
        ttk.Button(popup, text="Close", command=popup.destroy).pack(pady=8)

if __name__ == "__main__":
    root = tk.Tk()
    app = RecommendationGUI(root)
    root.mainloop()
