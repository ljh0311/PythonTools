"""Records Panel UI setup (extracted from car_rental_recommender_gui)."""

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


def setup_records_management_tab(app):
    """Set up the records management tab for CRUD operations with enhanced Excel formula integration"""
    # Main frame with improved layout
    main_frame = ttk.Frame(app.records_management_tab)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Split into left and right panes with better proportions
    left_frame = ttk.Frame(main_frame)
    left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=5)

    right_frame = ttk.Frame(main_frame)
    right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=5)

    # Records list on the left with enhanced columns
    records_frame = ttk.LabelFrame(left_frame, text="Rental Records")
    records_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Create treeview for records with comprehensive columns
    columns = (
        "Start",
        "End",
        "Car Model",
        "Provider",
        "Distance",
        "Duration",
        "Collected From",
        "Total Cost",
    )
    app.records_tree = ttk.Treeview(
        records_frame, columns=columns, show="headings", height=15
    )

    # Set column headings and widths
    column_widths = {
        "Start": 80,
        "End": 80,
        "Car Model": 110,
        "Provider": 80,
        "Distance": 65,
        "Duration": 65,
        "Collected From": 100,
        "Total Cost": 80,
    }

    for col in columns:
        app.records_tree.heading(col, text=col)
        app.records_tree.column(
            col, width=column_widths.get(col, 100), anchor="center", stretch=False
        )

    # Add scrollbars
    y_scrollbar = ttk.Scrollbar(
        records_frame, orient="vertical", command=app.records_tree.yview
    )
    x_scrollbar = ttk.Scrollbar(
        records_frame, orient="horizontal", command=app.records_tree.xview
    )
    app.records_tree.configure(
        yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set
    )

    # Improved packing order for better layout and resizing
    app.records_tree.pack(
        side="left", fill="both", expand=True, padx=(0, 0), pady=(0, 0)
    )
    y_scrollbar.pack(side="right", fill="y")
    x_scrollbar.pack(side="bottom", fill="x")

    # Add select event
    app.records_tree.bind("<<TreeviewSelect>>", app.on_record_select)

    # Enhanced buttons for record operations
    button_frame = ttk.Frame(left_frame)
    button_frame.pack(fill="x", expand=False, padx=5, pady=5)

    # Left side buttons
    left_buttons = ttk.Frame(button_frame)
    left_buttons.pack(side="left", fill="x", expand=True)

    ttk.Button(left_buttons, text="🆕 Add New Record", command=app.add_record, style="Accent.TButton").pack(
        side="left", padx=2
    )
    ttk.Button(left_buttons, text="💾 Update Record", command=app.update_record, style="Accent.TButton").pack(
        side="left", padx=2
    )
    ttk.Button(left_buttons, text="🔄 Refresh", command=app.refresh_records).pack(
        side="left", padx=2
    )
    ttk.Button(left_buttons, text="🗑️ Delete", command=app.delete_record).pack(
        side="left", padx=2
    )

    # Right side buttons
    right_buttons = ttk.Frame(button_frame)
    right_buttons.pack(side="right", fill="x", expand=True)

    ttk.Button(
        right_buttons, text="📤 Export", command=app.export_records_data
    ).pack(side="right", padx=2)

    # Enhanced search field
    search_frame = ttk.Frame(button_frame)
    search_frame.pack(side="right", padx=10)

    ttk.Label(search_frame, text="🔍 Search:").pack(side="left", padx=2)
    search_entry = ttk.Entry(search_frame, textvariable=app.search_var, width=20)
    search_entry.pack(side="left", padx=2)
    search_entry.bind("<KeyRelease>", app.filter_records)

    # Vision image import (local Ollama — opt-in)
    vision_import_frame = ttk.LabelFrame(right_frame, text="📷 Import from image")
    vision_import_frame.pack(fill="x", padx=5, pady=5)

    vision_controls = ttk.Frame(vision_import_frame)
    vision_controls.pack(fill="x", padx=5, pady=5)

    app.vision_image_path = None
    app.vision_image_label = ttk.Label(
        vision_controls, text="No image selected", foreground="gray"
    )
    app.vision_image_label.pack(side="left", padx=5)

    ttk.Button(
        vision_controls, text="Choose image", command=app.choose_vision_image
    ).pack(side="left", padx=5)

    vision_model_frame = ttk.Frame(vision_import_frame)
    vision_model_frame.pack(fill="x", padx=5, pady=(0, 5))

    ttk.Label(vision_model_frame, text="Vision model:").pack(side="left", padx=5)
    app.vision_model_var = tk.StringVar(value=DEFAULT_VISION_MODEL)
    app.vision_model_combobox = GUIHelper.create_combobox(
        vision_model_frame,
        app.vision_model_var,
        values=[DEFAULT_VISION_MODEL],
        width=22,
    )
    app.vision_model_combobox.pack(side="left", padx=5)
    ttk.Button(
        vision_model_frame, text="🔄", width=3, command=app.refresh_vision_models
    ).pack(side="left", padx=2)

    vision_actions = ttk.Frame(vision_import_frame)
    vision_actions.pack(fill="x", padx=5, pady=5)

    ttk.Button(
        vision_actions,
        text="Extract & fill form",
        command=app.extract_from_vision_image,
        style="Accent.TButton",
    ).pack(side="left", padx=5)

    ttk.Label(
        vision_import_frame,
        text="Image stays local; sent to localhost Ollama only when you click Extract.",
        font=("TkDefaultFont", 8),
        foreground="gray",
    ).pack(anchor="w", padx=5, pady=(0, 5))

    app.vision_status_text = tk.Text(
        vision_import_frame,
        height=3,
        width=60,
        state="disabled",
        background="#f8f9fa",
        font=("Consolas", 9),
        wrap=tk.WORD,
    )
    app.vision_status_text.pack(fill="x", padx=5, pady=(0, 5))

    app.root.after(400, app.refresh_vision_models)

    # LLM Assistant Frame for natural language input
    llm_assistant_frame = ttk.LabelFrame(right_frame, text="🤖 LLM Assistant - Describe Your Rental")
    llm_assistant_frame.pack(fill="x", padx=5, pady=5)
    
    # Text input area for natural language description
    llm_input_frame = ttk.Frame(llm_assistant_frame)
    llm_input_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    ttk.Label(llm_input_frame, text="💬 Describe your rental in natural language:").pack(anchor="w", padx=5, pady=2)
    
    # Text widget for input with scrollbar
    llm_text_frame = ttk.Frame(llm_input_frame)
    llm_text_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    app.llm_input_text = tk.Text(llm_text_frame, height=4, width=60, wrap=tk.WORD)
    llm_input_scrollbar = ttk.Scrollbar(llm_text_frame, orient="vertical", command=app.llm_input_text.yview)
    app.llm_input_text.configure(yscrollcommand=llm_input_scrollbar.set)
    app.llm_input_text.pack(side="left", fill="both", expand=True)
    llm_input_scrollbar.pack(side="right", fill="y")
    
    # Example text
    example_text = "Example: 'Rented a Getgo car on Saturday, drove 50km in 3 hours, pumped 4L of fuel'"
    ttk.Label(llm_input_frame, text=example_text, font=("TkDefaultFont", 8), foreground="gray").pack(anchor="w", padx=5, pady=2)
    
    # Buttons frame
    llm_buttons_frame = ttk.Frame(llm_assistant_frame)
    llm_buttons_frame.pack(fill="x", padx=5, pady=5)
    
    ttk.Button(
        llm_buttons_frame,
        text="🤖 Rephrase to standard format",
        command=app.rephrase_to_standard_format,
        style="Accent.TButton"
    ).pack(side="left", padx=5)
    
    ttk.Button(
        llm_buttons_frame,
        text="🤖 Process with LLM",
        command=app.process_natural_language_input,
        style="Accent.TButton"
    ).pack(side="left", padx=5)
    
    ttk.Button(
        llm_buttons_frame,
        text="📋 Fill Form from LLM",
        command=app.fill_form_from_llm,
    ).pack(side="left", padx=5)
    
    ttk.Button(
        llm_buttons_frame,
        text="🧹 Clear",
        command=lambda: app.llm_input_text.delete("1.0", tk.END),
    ).pack(side="left", padx=5)
    
    # Display area for LLM response
    llm_response_frame = ttk.LabelFrame(llm_assistant_frame, text="📊 LLM Extracted Data")
    llm_response_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    app.llm_response_text = tk.Text(
        llm_response_frame,
        height=6,
        width=60,
        state="disabled",
        background="#f8f9fa",
        font=("Consolas", 9),
        wrap=tk.WORD
    )
    llm_response_scrollbar = ttk.Scrollbar(
        llm_response_frame,
        orient="vertical",
        command=app.llm_response_text.yview
    )
    app.llm_response_text.configure(yscrollcommand=llm_response_scrollbar.set)
    app.llm_response_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    llm_response_scrollbar.pack(side="right", fill="y")
    
    # Store LLM extracted data
    app.llm_extracted_data = None

    # Enhanced Record Form on the right
    form_frame = ttk.LabelFrame(right_frame, text="📝 Record Details")
    form_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Create scrollable frame for the form with proper configuration
    # Remove scrolling: just use a direct frame in the form_frame
    scrollable_frame = ttk.Frame(form_frame)
    scrollable_frame.pack(fill="both", expand=True)

    # Create two frames for better organization
    left_form_frame = ttk.Frame(scrollable_frame)
    left_form_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)

    right_form_frame = ttk.Frame(scrollable_frame)
    right_form_frame.pack(side="right", fill="both", expand=True, padx=10, pady=5)

    # Left form fields - Basic Information
    basic_info_frame = ttk.LabelFrame(left_form_frame, text="📋 Basic Information")
    basic_info_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Region (Singapore / Malaysia) - determines which providers are shown
    ttk.Label(basic_info_frame, text="🌏 Region:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ttk.Label(basic_info_frame, text="*", foreground="red").grid(row=0, column=0, padx=(55, 0), pady=5, sticky="w")
    app.record_region_var.set("Singapore")
    GUIHelper.create_combobox(
        parent=basic_info_frame,
        textvariable=app.record_region_var,
        values=list(VALID_REGIONS),
        width=15,
        row=0,
        column=1,
        padx=5,
        pady=5,
        sticky="w",
        bind_event=("<<ComboboxSelected>>", app._on_record_region_changed),
    )

    # Rental start / end dates
    date_label_frame = ttk.Frame(basic_info_frame)
    date_label_frame.grid(row=1, column=0, padx=5, pady=5, sticky="w")
    ttk.Label(date_label_frame, text="📅 Rental start (DD/MM/YYYY):").pack(side="left")
    ttk.Label(date_label_frame, text="*", foreground="red").pack(side="left", padx=(2, 0))
    date_entry = ttk.Entry(
        basic_info_frame, textvariable=app.record_date_var, width=15
    )
    date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    date_entry.bind("<KeyRelease>", lambda e: (setattr(app, "_form_dirty", True), app.sync_rental_hours_from_dates()))
    ttk.Button(
        basic_info_frame, text="Today", command=app.set_today_date, width=8
    ).grid(row=1, column=2, padx=2, pady=5, sticky="w")

    end_date_label_frame = ttk.Frame(basic_info_frame)
    end_date_label_frame.grid(row=2, column=0, padx=5, pady=5, sticky="w")
    ttk.Label(end_date_label_frame, text="📅 Rental end (DD/MM/YYYY):").pack(side="left")
    end_date_entry = ttk.Entry(
        basic_info_frame, textvariable=app.record_end_date_var, width=15
    )
    end_date_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
    end_date_entry.bind("<KeyRelease>", lambda e: (setattr(app, "_form_dirty", True), app.sync_rental_hours_from_dates()))
    ttk.Button(
        basic_info_frame, text="= Start", command=app.set_end_date_same_as_start, width=8
    ).grid(row=2, column=2, padx=2, pady=5, sticky="w")

    car_model_label_frame = ttk.Frame(basic_info_frame)
    car_model_label_frame.grid(row=3, column=0, padx=5, pady=5, sticky="w")
    ttk.Label(car_model_label_frame, text="🚗 Car Model:").pack(side="left")
    ttk.Label(car_model_label_frame, text="*", foreground="red").pack(side="left", padx=(2, 0))
    app.record_car_model_combo = ttk.Combobox(
        basic_info_frame, textvariable=app.record_car_model_var, width=23
    )
    app.record_car_model_combo.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky="w")
    app.record_car_model_combo.bind("<KeyRelease>", lambda e: setattr(app, "_form_dirty", True))

    # Provider (Car Cat) - list depends on Region
    provider_label_frame = ttk.Frame(basic_info_frame)
    provider_label_frame.grid(row=4, column=0, padx=5, pady=5, sticky="w")
    ttk.Label(provider_label_frame, text="🏢 Provider:").pack(side="left")
    ttk.Label(provider_label_frame, text="*", foreground="red").pack(side="left", padx=(2, 0))
    app.record_provider_combo = GUIHelper.create_combobox(
        parent=basic_info_frame,
        textvariable=app.record_provider_var,
        values=get_providers_for_region(app.record_region_var.get() or "Singapore"),
        width=15,
        row=4,
        column=1,
        padx=5,
        pady=5,
        sticky="w",
        bind_event=("<<ComboboxSelected>>", app.on_provider_changed),
    )

    ttk.Label(basic_info_frame, text="📅 Day Type:").grid(
        row=5, column=0, padx=5, pady=5, sticky="w"
    )
    daytype_combo = GUIHelper.create_combobox(
        parent=basic_info_frame,
        textvariable=app.record_weekend_var,
        values=["weekday", "weekend"],
        width=15,
        row=5,
        column=1,
        padx=5,
        pady=5,
        sticky="w",
    )

    ttk.Label(basic_info_frame, text="📍 Collected from:").grid(
        row=6, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(
        basic_info_frame, textvariable=app.record_collection_location_var, width=25
    ).grid(row=6, column=1, columnspan=2, padx=5, pady=5, sticky="w")

    ttk.Label(basic_info_frame, text="⭐ Distance rating (0-5):").grid(
        row=7, column=0, padx=5, pady=5, sticky="w"
    )
    GUIHelper.create_combobox(
        parent=basic_info_frame,
        textvariable=app.record_distance_rating_var,
        values=["", "0", "1", "2", "3", "4", "5"],
        width=15,
        row=7,
        column=1,
        padx=5,
        pady=5,
        sticky="w",
    )

    # Right form fields - Rental Details
    rental_details_frame = ttk.LabelFrame(right_form_frame, text="⏱️ Rental Details")
    rental_details_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Distance and Duration with auto-calculation hints
    ttk.Label(rental_details_frame, text="📏 Distance (KM):").grid(
        row=0, column=0, padx=5, pady=5, sticky="w"
    )
    distance_entry = ttk.Entry(
        rental_details_frame, textvariable=app.record_distance_var, width=15
    )
    distance_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(rental_details_frame, text="*Required", foreground="red").grid(
        row=0, column=2, padx=2, pady=5, sticky="w"
    )

    ttk.Label(rental_details_frame, text="⏰ Rental Hours:").grid(
        row=1, column=0, padx=5, pady=5, sticky="w"
    )
    hours_entry = ttk.Entry(
        rental_details_frame, textvariable=app.record_hours_var, width=15
    )
    hours_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(
        rental_details_frame,
        text="Auto for multi-day",
        foreground="gray",
    ).grid(row=1, column=2, padx=2, pady=5, sticky="w")

    # Enhanced Fuel Information with better organization
    fuel_frame = ttk.LabelFrame(left_form_frame, text="⛽ Fuel Information")
    fuel_frame.pack(fill="both", expand=True, padx=5, pady=5)

    ttk.Label(fuel_frame, text="⛽ Fuel Pumped (L):").grid(
        row=0, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(fuel_frame, textvariable=app.record_fuel_pumped_var, width=15).grid(
        row=0, column=1, padx=5, pady=5, sticky="w"
    )

    ttk.Label(fuel_frame, text="📊 Est. Fuel Usage (L):").grid(
        row=1, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(fuel_frame, textvariable=app.record_fuel_usage_var, width=15).grid(
        row=1, column=1, padx=5, pady=5, sticky="w"
    )

    ttk.Label(fuel_frame, text="📈 Consumption (KM/L):").grid(
        row=2, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(fuel_frame, textvariable=app.record_consumption_var, width=15).grid(
        row=2, column=1, padx=5, pady=5, sticky="w"
    )

    # Auto-calculate fuel usage button
    ttk.Button(
        fuel_frame,
        text="Auto-calc Usage",
        command=app.auto_calculate_fuel_usage,
        width=12,
    ).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

    # Enhanced Cost Information with Excel integration
    cost_frame = ttk.LabelFrame(right_form_frame, text="💰 Cost Information")
    cost_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # First column of costs
    ttk.Label(cost_frame, text="💵 Total Cost ($):").grid(
        row=0, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(cost_frame, textvariable=app.record_total_cost_var, width=15).grid(
        row=0, column=1, padx=5, pady=5, sticky="w"
    )

    ttk.Label(cost_frame, text="⛽ Pumped Fuel Cost ($):").grid(
        row=1, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(
        cost_frame,
        textvariable=app.record_pumped_cost_var,
        width=15,
        state="readonly",
        background="#f0f0f0",
        foreground="black",
    ).grid(row=1, column=1, padx=5, pady=5, sticky="w")

    # Second column of costs
    ttk.Label(cost_frame, text="📏 Cost per KM ($):").grid(
        row=0, column=2, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(
        cost_frame,
        textvariable=app.record_cost_per_km_var,
        width=15,
        state="readonly",
        background="#f0f0f0",
        foreground="black",
    ).grid(row=0, column=3, padx=5, pady=5, sticky="w")

    ttk.Label(cost_frame, text="⏰ Duration Cost ($):").grid(
        row=1, column=2, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(
        cost_frame, textvariable=app.record_duration_cost_var, width=15
    ).grid(row=1, column=3, padx=5, pady=5, sticky="w")

    # Additional cost fields
    ttk.Label(cost_frame, text="💰 Cost per Hour ($):").grid(
        row=2, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(
        cost_frame,
        textvariable=app.record_cost_per_hr_var,
        width=15,
        state="readonly",
        background="#f0f0f0",
        foreground="black",
    ).grid(row=2, column=1, padx=5, pady=5, sticky="w")

    ttk.Label(cost_frame, text="💸 Fuel Savings ($):").grid(
        row=2, column=2, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(
        cost_frame,
        textvariable=app.record_fuel_savings_var,
        width=15,
        state="readonly",
        background="#f0f0f0",
        foreground="black",
    ).grid(row=2, column=3, padx=5, pady=5, sticky="w")

    # Improved layout: align buttons horizontally, add spacers for clarity

    # Create a frame to hold the action buttons for better layout
    button_row = ttk.Frame(cost_frame)
    button_row.grid(row=3, column=0, columnspan=4, padx=0, pady=5, sticky="ew")

    # Auto-calc button (left)
    auto_calc_btn = ttk.Button(
        button_row,
        text="Auto-calc Total",
        command=app.auto_calculate_total_cost,
        width=14,
    )
    auto_calc_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

    # Smart calculation button (middle)
    smart_calc_btn = ttk.Button(
        button_row,
        text="Get smart calculation",
        command=app.smart_auto_calc,
        width=16,
    )
    smart_calc_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

    # LLM Assistance button (right, robot emoji)
    llm_btn = ttk.Button(
        button_row,
        text="🤖 Get LLM Assistance",
        command=app.llm_assisted_form_fill,
        width=18,
    )
    llm_btn.pack(side="left", fill="x", expand=True)


    # Traditional Rental breakdown (shown when Provider = Traditional Rental)
    app.traditional_rental_frame = ttk.LabelFrame(
        left_form_frame, text="Traditional Rental (RM)"
    )
    ttk.Label(
        app.traditional_rental_frame,
        text="Rental duration/cost (RM):",
    ).grid(row=0, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(
        app.traditional_rental_frame,
        textvariable=app.record_rental_fee_rm_var,
        width=12,
    ).grid(row=0, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(
        app.traditional_rental_frame,
        text="Malaysia usage add-on (RM):",
    ).grid(row=1, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(
        app.traditional_rental_frame,
        textvariable=app.record_additional_fee_rm_var,
        width=12,
    ).grid(row=1, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(app.traditional_rental_frame, text="Deposit (RM):").grid(
        row=2, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(
        app.traditional_rental_frame,
        textvariable=app.record_deposit_rm_var,
        width=12,
    ).grid(row=2, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(
        app.traditional_rental_frame,
        text="Fuel topped up (RM):",
    ).grid(row=3, column=0, padx=5, pady=5, sticky="w")
    ttk.Entry(
        app.traditional_rental_frame,
        textvariable=app.record_traditional_fuel_rm_var,
        width=12,
    ).grid(row=3, column=1, padx=5, pady=5, sticky="w")
    app.normal_rental_frame = app.traditional_rental_frame

    # EV Information (will be shown/hidden based on provider selection)
    app.ev_frame = ttk.LabelFrame(left_form_frame, text="⚡ EV Information")
    app.ev_frame.pack(fill="both", expand=True, padx=5, pady=5)

    ttk.Label(app.ev_frame, text="⚡ kWh Used (EV):").grid(
        row=0, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(app.ev_frame, textvariable=app.record_kwh_used_var, width=10).grid(
        row=0, column=1, padx=5, pady=5, sticky="w"
    )

    ttk.Label(app.ev_frame, text="💰 Electricity Cost ($):").grid(
        row=1, column=0, padx=5, pady=5, sticky="w"
    )
    ttk.Entry(
        app.ev_frame,
        textvariable=app.record_electricity_cost_var,
        width=15,
        state="readonly",
        background="#f0f0f0",
        foreground="black",
    ).grid(row=1, column=1, padx=5, pady=5, sticky="w")

    # Initially hide the EV frame (will be shown when EV provider is selected)
    app.ev_frame.pack_forget()

    # Enhanced Fuel Economy Comparison Frame
    fuel_economy_frame = ttk.LabelFrame(
        right_form_frame, text="📈 Fuel Economy Comparison"
    )
    fuel_economy_frame.pack(fill="both", expand=True, padx=5, pady=5)

    # Create text widget for fuel economy comparison
    app.fuel_economy_comparison_text = tk.Text(
        fuel_economy_frame,
        height=8,
        width=60,
        state="disabled",
        background="#f8f9fa",
        font=("Consolas", 9),
    )
    fuel_economy_scrollbar = ttk.Scrollbar(
        fuel_economy_frame,
        orient="vertical",
        command=app.fuel_economy_comparison_text.yview,
    )
    app.fuel_economy_comparison_text.configure(
        yscrollcommand=fuel_economy_scrollbar.set
    )

    app.fuel_economy_comparison_text.pack(
        side="left", fill="both", expand=True, padx=5, pady=5
    )
    fuel_economy_scrollbar.pack(side="right", fill="y")

    # Enhanced Button frame for CRUD operations
    crud_frame = ttk.Frame(scrollable_frame)
    crud_frame.pack(fill="x", padx=5, pady=10)

    # Primary action buttons
    primary_buttons = ttk.Frame(crud_frame)
    primary_buttons.pack(fill="x", pady=5)

    add_btn = ttk.Button(
        primary_buttons,
        text="🆕 Add New Record",
        command=app.add_record,
        style="Accent.TButton",
    )
    add_btn.pack(side="left", padx=5, fill="x", expand=True)
    # Bind Enter key to add record when form is focused
    app.root.bind_all("<Return>", lambda e: app.add_record() if app.records_management_tab == app.notebook.select() else None)
    
    update_btn = ttk.Button(
        primary_buttons,
        text="💾 Update Record",
        command=app.update_record,
        style="Accent.TButton",
    )
    update_btn.pack(side="left", padx=5, fill="x", expand=True)

    # Secondary action buttons
    secondary_buttons = ttk.Frame(crud_frame)
    secondary_buttons.pack(fill="x", pady=2)

    ttk.Button(
        secondary_buttons, text="🧹 Clear Form", command=app.clear_record_form
    ).pack(side="left", padx=5, fill="x", expand=True)
    ttk.Button(
        secondary_buttons,
        text="📊 Calculate All",
        command=app.calculate_all_formulas,
    ).pack(side="left", padx=5, fill="x", expand=True)
    ttk.Button(
        secondary_buttons,
        text="📝 Edit Selected",
        command=app.edit_selected_record,
    ).pack(side="left", padx=5, fill="x", expand=True)
    ttk.Button(
        secondary_buttons, text="🆕 Quick Add", command=app.add_new_record_quick
    ).pack(side="left", padx=5, fill="x", expand=True)

    # Add status bar to show form state
    app.records_status_bar = ttk.Label(
        right_frame,
        text="Form ready - All fields visible",
        relief="sunken",
        anchor="w",
    )
    app.records_status_bar.pack(side="bottom", fill="x", padx=5, pady=2)

    # Update status after a short delay to ensure all widgets are visible
    app.root.after(
        200,
        lambda: app.update_records_status(
            "Form loaded - All fields visible and accessible"
        ),
    )

    # Record ID variable (hidden) for tracking which record is being edited
    app.current_record_index = None

    # Enhanced trace callbacks to trigger auto-calculation with better performance
    app.record_provider_var.trace_add(
        "write", lambda *args: app.auto_update_fields()
    )
    app.record_distance_var.trace_add(
        "write", lambda *args: app.auto_update_fields()
    )
    app.record_fuel_pumped_var.trace_add(
        "write", lambda *args: app.auto_update_fields()
    )
    app.record_fuel_usage_var.trace_add(
        "write", lambda *args: app.auto_update_fields()
    )
    app.record_total_cost_var.trace_add(
        "write", lambda *args: app.auto_update_fields()
    )
    app.record_hours_var.trace_add(
        "write", lambda *args: app.auto_update_fields()
    )
    app.record_kwh_used_var.trace_add(
        "write", lambda *args: app.auto_update_fields()
    )
    app.record_duration_cost_var.trace_add(
        "write", lambda *args: app.auto_update_fields()
    )
    app.fuel_price_var.trace_add("write", lambda *args: app.auto_update_fields())

