"""Settings Panel UI setup (extracted from car_rental_recommender_gui)."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd

from car_rental_recommender_core import (
    VALID_REGIONS,
    get_providers_for_region,
    normalize_traditional_rental_provider,
    is_traditional_rental,
)
from components.gui_helper import GUIHelper


def setup_settings_tab(app):
    def add_labeled_entry(
        parent,
        label_text,
        var,
        row,
        col,
        width=10,
        entry_kwargs=None,
        label_kwargs=None,
        **grid_kwargs,
    ):
        """Helper to add a label and entry to a grid row/col."""
        if label_kwargs is None:
            label_kwargs = {}
        if entry_kwargs is None:
            entry_kwargs = {}
        ttk.Label(parent, text=label_text, **label_kwargs).grid(
            row=row, column=col, padx=5, pady=5, sticky="w", **grid_kwargs
        )
        entry = ttk.Entry(parent, textvariable=var, width=width, **entry_kwargs)
        entry.grid(
            row=row, column=col + 1, padx=5, pady=5, sticky="w", **grid_kwargs
        )
        return entry

    def add_button(parent, text, command, row, col, style=None, **grid_kwargs):
        kwargs = {"text": text, "command": command}
        if style:
            kwargs["style"] = style
        btn = ttk.Button(parent, **kwargs)
        btn.grid(row=row, column=col, padx=5, pady=5, sticky="w", **grid_kwargs)
        return btn

    # Combined Data Settings and Upload frame
    data_frame = ttk.LabelFrame(app.settings_tab, text="Data Settings & Upload")
    data_frame.pack(fill="x", expand=False, padx=10, pady=10, ipadx=10, ipady=10)

    # Data file row
    ttk.Label(data_frame, text="Data File:").grid(
        row=0, column=0, padx=5, pady=5, sticky="w"
    )
    app.data_file_var = tk.StringVar(value="22 - Sheet1.csv")
    ttk.Entry(data_frame, textvariable=app.data_file_var, width=40).grid(
        row=0, column=1, padx=5, pady=5, sticky="w"
    )
    add_button(data_frame, "Browse", app.browse_file, row=0, col=2)
    add_button(data_frame, "Load Data", app.load_data_action, row=0, col=3)
    add_button(data_frame, "Data quality report", app.show_data_quality_report, row=0, col=4)

    # Divider
    ttk.Separator(data_frame, orient="horizontal").grid(
        row=1, column=0, columnspan=4, sticky="ew", pady=(5, 5)
    )

    # Upload file selection
    ttk.Label(data_frame, text="📄 Select File:").grid(
        row=2, column=0, padx=5, pady=5, sticky="w"
    )
    app.upload_file_var = tk.StringVar()
    ttk.Entry(
        data_frame, textvariable=app.upload_file_var, width=40, state="readonly"
    ).grid(row=2, column=1, padx=5, pady=5, sticky="w")
    add_button(data_frame, "Browse", app.browse_upload_file, row=2, col=2)

    # Upload mode selection
    ttk.Label(data_frame, text="📋 Upload Mode:").grid(
        row=3, column=0, padx=5, pady=5, sticky="w"
    )
    app.upload_mode_var = tk.StringVar(value="replace")
    upload_mode_combo = ttk.Combobox(
        data_frame,
        textvariable=app.upload_mode_var,
        values=["Replace Current Data", "Add to Current Data"],
        width=25,
        state="readonly",
    )
    upload_mode_combo.grid(row=3, column=1, padx=5, pady=5, sticky="w")
    add_button(
        data_frame,
        "📤 Upload File",
        app.upload_file_action,
        row=3,
        col=2,
        style="Accent.TButton",
    )
    add_button(
        data_frame,
        "👁️ Preview",
        app.preview_upload_file,
        row=4,
        col=2,
    )

    # Upload status
    app.upload_status_var = tk.StringVar(value="No file selected")
    ttk.Label(
        data_frame, textvariable=app.upload_status_var, foreground="gray"
    ).grid(row=5, column=0, columnspan=3, padx=5, pady=2, sticky="w")

    # Fuel cost settings
    fuel_frame = ttk.LabelFrame(app.settings_tab, text="Fuel Cost Settings")
    fuel_frame.pack(fill="x", expand=False, padx=10, pady=10, ipadx=10, ipady=10)

    # Fuel price per liter, cost for full tank, expected distance per tank
    add_labeled_entry(
        fuel_frame, "Fuel Price (SGD/L):", app.fuel_price_var, row=0, col=0
    )
    add_labeled_entry(
        fuel_frame, "Cost for full tank (SGD):", app.fuel_cost_var, row=0, col=2
    )
    add_labeled_entry(
        fuel_frame,
        "Expected distance per tank (km):",
        app.tank_distance_var,
        row=0,
        col=4,
    )

    # Mileage charge settings
    mileage_frame = ttk.LabelFrame(
        app.settings_tab, text="Mileage Charge Settings"
    )
    mileage_frame.pack(fill="x", expand=False, padx=10, pady=10, ipadx=10, ipady=10)

    add_labeled_entry(
        mileage_frame, "Getgo (SGD/km):", app.getgo_mileage_var, row=0, col=0
    )
    add_labeled_entry(
        mileage_frame, "Car Club (SGD/km):", app.carclub_mileage_var, row=0, col=2
    )

    # Cost per kWh for EVs (will be shown/hidden based on provider selection)
    app.cost_per_kwh_label = ttk.Label(fuel_frame, text="Cost per kWh (SGD):")
    app.cost_per_kwh_entry = ttk.Entry(
        fuel_frame, textvariable=app.cost_per_kwh_var, width=10
    )
    app.cost_per_kwh_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
    app.cost_per_kwh_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    # Initially hide the cost per kWh field (will be shown when EV provider is selected)
    app.cost_per_kwh_label.grid_remove()
    app.cost_per_kwh_entry.grid_remove()

    # Esso Singapore fuel discount (23%) - applies only when region is Singapore
    app.esso_discount_cb = ttk.Checkbutton(
        fuel_frame,
        text="Apply Esso Singapore fuel discount (23%)",
        variable=app.apply_esso_sg_discount_var,
        command=app._on_esso_discount_toggled,
    )
    app.esso_discount_cb.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")

    # GetGo fleet catalog (web sync)
    fleet_frame = ttk.LabelFrame(app.settings_tab, text="GetGo Fleet Catalog")
    fleet_frame.pack(fill="both", expand=True, padx=10, pady=10, ipadx=10, ipady=10)

    fleet_toolbar = ttk.Frame(fleet_frame)
    fleet_toolbar.pack(fill=tk.X, padx=5, pady=4)
    ttk.Button(
        fleet_toolbar, text="Refresh from GetGo", command=app.refresh_getgo_fleet_now
    ).pack(side=tk.LEFT, padx=(0, 8))
    app.getgo_fleet_auto_var = tk.BooleanVar(
        value=app.settings.get("getgo_fleet_auto_refresh", True)
    )
    ttk.Checkbutton(
        fleet_toolbar,
        text="Auto-update monthly",
        variable=app.getgo_fleet_auto_var,
        command=app.save_getgo_fleet_prefs,
    ).pack(side=tk.LEFT, padx=4)
    app.getgo_fleet_status_var = tk.StringVar(value="Fleet catalog not loaded yet.")
    ttk.Label(
        fleet_frame, textvariable=app.getgo_fleet_status_var, foreground="#444444"
    ).pack(anchor=tk.W, padx=8, pady=(0, 4))
    ttk.Label(
        fleet_frame,
        text="Source: home.getgo.sg/meet-the-fleet (public). Uses Firecrawl CLI if installed, else cached list.",
        foreground="#666666",
        font=("Segoe UI", 9),
        wraplength=720,
    ).pack(anchor=tk.W, padx=8, pady=(0, 6))

    fleet_tree_wrap = ttk.Frame(fleet_frame)
    fleet_tree_wrap.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    fleet_scroll = ttk.Scrollbar(fleet_tree_wrap)
    fleet_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    app.getgo_fleet_tree = ttk.Treeview(
        fleet_tree_wrap,
        columns=("name", "tier", "type", "seats"),
        show="headings",
        height=8,
        yscrollcommand=fleet_scroll.set,
    )
    for col, label, width in [
        ("name", "Model", 220),
        ("tier", "Tier", 100),
        ("type", "Type", 100),
        ("seats", "Seats", 80),
    ]:
        app.getgo_fleet_tree.heading(col, text=label)
        app.getgo_fleet_tree.column(col, width=width)
    app.getgo_fleet_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    fleet_scroll.config(command=app.getgo_fleet_tree.yview)

    # Car Model Tank Capacities section
    tank_capacity_frame = ttk.LabelFrame(
        app.settings_tab, text="Car Model Tank Capacities"
    )
    tank_capacity_frame.pack(fill="both", expand=True, padx=10, pady=10, ipadx=10, ipady=10)
    tree_frame = ttk.Frame(tank_capacity_frame)
    tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Create Treeview with scrollbar
    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")

    app.tank_capacity_tree = ttk.Treeview(
        tree_frame,
        columns=("car_model", "capacity"),
        show="headings",
        yscrollcommand=tree_scroll.set,
        height=8,
    )
    app.tank_capacity_tree.heading("car_model", text="Car Model")
    app.tank_capacity_tree.heading("capacity", text="Tank Capacity (L)")
    app.tank_capacity_tree.column("car_model", width=300)
    app.tank_capacity_tree.column("capacity", width=150)
    app.tank_capacity_tree.pack(side="left", fill="both", expand=True)
    tree_scroll.config(command=app.tank_capacity_tree.yview)

    # Bind selection event
    app.tank_capacity_tree.bind(
        "<<TreeviewSelect>>", app.on_tank_capacity_select
    )

    # Input fields frame
    input_frame = ttk.Frame(tank_capacity_frame)
    input_frame.pack(fill="x", padx=5, pady=5)

    ttk.Label(input_frame, text="Car Model:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    app.tank_capacity_model_var = tk.StringVar()
    app.tank_capacity_model_combo = ttk.Combobox(
        input_frame, textvariable=app.tank_capacity_model_var, width=30
    )
    app.tank_capacity_model_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    ttk.Label(input_frame, text="Tank Capacity (L):").grid(
        row=0, column=2, padx=5, pady=5, sticky="w"
    )
    app.tank_capacity_value_var = tk.StringVar()
    app.tank_capacity_value_entry = ttk.Entry(
        input_frame, textvariable=app.tank_capacity_value_var, width=15
    )
    app.tank_capacity_value_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    # Buttons frame
    button_frame = ttk.Frame(tank_capacity_frame)
    button_frame.pack(fill="x", padx=5, pady=5)

    ttk.Button(button_frame, text="Add", command=app.add_tank_capacity_entry).pack(
        side="left", padx=5
    )
    ttk.Button(button_frame, text="Edit", command=app.edit_tank_capacity_entry).pack(
        side="left", padx=5
    )
    ttk.Button(button_frame, text="Delete", command=app.delete_tank_capacity_entry).pack(
        side="left", padx=5
    )
    ttk.Button(
        button_frame, text="Load from CSV", command=app.load_car_models_from_csv
    ).pack(side="left", padx=5)
    ttk.Button(
        button_frame, text="Set Defaults", command=app.set_default_tank_capacities
    ).pack(side="left", padx=5)

    # Refresh the treeview with existing data
    app.refresh_tank_capacity_tree()

    # Save settings button
    save_button = ttk.Button(
        app.settings_tab, text="Save Settings", command=app.save_settings
    )
    save_button.pack(anchor="w", padx=10, pady=20)

