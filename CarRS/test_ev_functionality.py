#!/usr/bin/env python3
"""
A simple GUI to demonstrate EV functionality for car rental recommender.
"""

import tkinter as tk
from tkinter import ttk

def simple_ev_gui():
    root = tk.Tk()
    root.title("Simple EV Functionality GUI")
    root.geometry("350x220")

    # Variables
    provider_var = tk.StringVar(value="Getgo")
    cost_per_kwh_var = tk.StringVar(value="0.45")

    # Frame
    frame = ttk.Frame(root, padding=15)
    frame.pack(fill='both', expand=True)

    # Provider selection
    ttk.Label(frame, text="Provider:").grid(row=0, column=0, sticky='w', pady=5)
    provider_combo = ttk.Combobox(
        frame, textvariable=provider_var,
        values=["Getgo", "Car Club", "Getgo(EV)"], width=15, state="readonly"
    )
    provider_combo.grid(row=0, column=1, pady=5)

    # Cost per kWh (hidden unless EV)
    cost_per_kwh_label = ttk.Label(frame, text="Cost per kWh (SGD):")
    cost_per_kwh_entry = ttk.Entry(frame, textvariable=cost_per_kwh_var, width=10)
    cost_per_kwh_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
    cost_per_kwh_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
    cost_per_kwh_label.grid_remove()
    cost_per_kwh_entry.grid_remove()

    def on_provider_change(event=None):
        if provider_var.get() == "Getgo(EV)":
            cost_per_kwh_label.grid()
            cost_per_kwh_entry.grid()
        else:
            cost_per_kwh_label.grid_remove()
            cost_per_kwh_entry.grid_remove()

    provider_combo.bind('<<ComboboxSelected>>', on_provider_change)

    # Simple calculation and result display
    result_var = tk.StringVar(value="")

    def calculate():
        provider = provider_var.get()
        if provider == "Getgo(EV)":
            try:
                cost_per_kwh = float(cost_per_kwh_var.get())
            except ValueError:
                result_var.set("Please enter a valid cost per kWh.")
                return
            distance = 100.0
            kwh_used = 16.0
            ev_cost = cost_per_kwh * kwh_used
            ev_eff = distance / kwh_used
            result_var.set(f"EV: {ev_eff:.2f} km/kWh, Total Cost: ${ev_cost:.2f}")
        else:
            distance = 100.0
            fuel_usage = 8.0
            fuel_price = 2.51
            ice_cost = fuel_price * fuel_usage
            ice_eff = distance / fuel_usage
            result_var.set(f"ICE: {ice_eff:.2f} km/L, Total Cost: ${ice_cost:.2f}")

    ttk.Button(frame, text="Calculate", command=calculate).grid(row=2, column=0, columnspan=2, pady=15)

    ttk.Label(frame, textvariable=result_var, foreground="blue", wraplength=300, justify="center").grid(
        row=3, column=0, columnspan=2, pady=10
    )

    ttk.Label(
        frame,
        text="Select provider. If 'Getgo(EV)', enter cost per kWh and click Calculate.",
        justify="center", wraplength=300
    ).grid(row=4, column=0, columnspan=2, pady=5)

    root.mainloop()

if __name__ == "__main__":
    simple_ev_gui()