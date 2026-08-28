"""Recommendations Panel UI — form-first trip entry, results prominent."""

import tkinter as tk
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from car_rental_recommender_core import VALID_REGIONS, get_providers_for_region
from components.gui_helper import GUIHelper


def setup_recommendation_tab(app):
    container = ttk.Frame(app.recommendation_tab)
    container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # --- Quick trip form (primary path) ---
    quick_frame = ttk.LabelFrame(container, text="Plan your trip", padding=(10, 8))
    quick_frame.pack(fill=tk.X, pady=(0, 8))

    row1 = ttk.Frame(quick_frame)
    row1.pack(fill=tk.X, pady=2)

    ttk.Label(row1, text="Distance (km):").pack(side=tk.LEFT, padx=(0, 4))
    app.rec_distance_var = tk.StringVar(value="40")
    dist_entry = ttk.Entry(row1, textvariable=app.rec_distance_var, width=8)
    dist_entry.pack(side=tk.LEFT, padx=(0, 12))
    dist_entry.bind("<Return>", lambda _e: app.get_quick_recommendations())

    ttk.Label(row1, text="Duration (h):").pack(side=tk.LEFT, padx=(0, 4))
    app.rec_duration_var = tk.StringVar(value="1")
    dur_entry = ttk.Entry(row1, textvariable=app.rec_duration_var, width=8)
    dur_entry.pack(side=tk.LEFT, padx=(0, 12))
    dur_entry.bind("<Return>", lambda _e: app.get_quick_recommendations())

    app.is_weekend_var = tk.BooleanVar()
    GUIHelper.create_checkbutton(row1, "Weekend", app.is_weekend_var)

    get_btn = ttk.Button(
        row1,
        text="Get Recommendations",
        command=app.get_quick_recommendations,
        style="Accent.TButton",
    )
    get_btn.pack(side=tk.RIGHT, padx=(8, 0))

    row2 = ttk.Frame(quick_frame)
    row2.pack(fill=tk.X, pady=4)

    ttk.Label(row2, text="Region:").pack(side=tk.LEFT, padx=(0, 4))
    app.current_region_var = tk.StringVar(value="Singapore")
    GUIHelper.create_combobox(row2, app.current_region_var, list(VALID_REGIONS), width=12)
    app.current_region_var.trace_add("write", lambda *a: app._on_region_filter_changed())

    ttk.Label(row2, text="Provider:").pack(side=tk.LEFT, padx=(12, 4))
    app.car_cat_var = tk.StringVar(value="All")
    app.car_cat_combo = GUIHelper.create_combobox(
        row2, app.car_cat_var, ["All"] + get_providers_for_region("Singapore"), width=14
    )

    ttk.Label(
        quick_frame,
        text="Uses your CSV history + pricing + ML (Ollama optional in Advanced).",
        foreground="#555555",
        font=("Segoe UI", 9),
    ).pack(anchor=tk.W, pady=(4, 0))

    app.recommendation_region_label = ttk.Label(
        quick_frame, text="Showing recommendations for: Singapore", font=("Segoe UI", 9)
    )
    app.recommendation_region_label.pack(anchor=tk.W)

    # --- Results + chart ---
    results_frame = ttk.LabelFrame(container, text="Results", padding=(8, 5))
    results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

    tree_wrap = ttk.Frame(results_frame)
    tree_wrap.pack(fill=tk.BOTH, expand=True)

    app.results_tree = ttk.Treeview(
        tree_wrap,
        columns=("provider", "car_model", "cost", "method", "confidence", "reasoning", "full_reasoning"),
        show="headings",
        height=8,
    )
    for col, text in [
        ("provider", "Provider"),
        ("car_model", "Car Model"),
        ("cost", "Est. Cost ($)"),
        ("method", "Method"),
        ("confidence", "Confidence"),
        ("reasoning", "Reasoning"),
        ("full_reasoning", ""),
    ]:
        app.results_tree.heading(col, text=text)
    for col, width, anchor in [
        ("provider", 90, None),
        ("car_model", 120, None),
        ("cost", 90, tk.E),
        ("method", 110, None),
        ("confidence", 80, tk.CENTER),
        ("reasoning", 260, None),
        ("full_reasoning", 0, None),
    ]:
        kw = {"width": width, "stretch": col != "full_reasoning"}
        if anchor is not None:
            kw["anchor"] = anchor
        app.results_tree.column(col, **kw)
    results_scroll = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=app.results_tree.yview)
    app.results_tree.configure(yscrollcommand=results_scroll.set)
    app.results_tree.bind("<Double-1>", app.show_recommendation_details)
    app.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    app.chart_frame = ttk.LabelFrame(results_frame, text="Cost comparison", padding=(8, 4))
    app.chart_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
    app.fig, app.ax = plt.subplots(figsize=(6, 2.8), dpi=100)
    app.canvas = FigureCanvasTkAgg(app.fig, master=app.chart_frame)
    app.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # --- Advanced: trip options + ML/Ollama ---
    adv_collapsible, adv_body = GUIHelper.create_collapsible(
        container, "Advanced options", collapsed=True
    )
    adv_collapsible.pack(fill=tk.X, pady=2)

    trip_opts = ttk.Frame(adv_body)
    trip_opts.pack(fill=tk.X, pady=2)
    ttk.Label(trip_opts, text="Passengers:").pack(side=tk.LEFT, padx=(0, 4))
    app.passenger_count_var = tk.StringVar(value="2")
    ttk.Spinbox(
        trip_opts, from_=1, to=10, textvariable=app.passenger_count_var, width=5, state="readonly"
    ).pack(side=tk.LEFT, padx=(0, 12))
    ttk.Label(trip_opts, text="Space:").pack(side=tk.LEFT, padx=(0, 4))
    app.space_requirements_var = tk.StringVar(value="little")
    ttk.Combobox(
        trip_opts,
        textvariable=app.space_requirements_var,
        values=["little", "medium", "alot"],
        width=10,
        state="readonly",
    ).pack(side=tk.LEFT)

    ai_row = ttk.Frame(adv_body)
    ai_row.pack(fill=tk.X, pady=4)
    app.use_ml_var = tk.BooleanVar(value=True)
    GUIHelper.create_checkbutton(ai_row, "Use Machine Learning", app.use_ml_var)
    app.use_ollama_var = tk.BooleanVar(value=False)
    GUIHelper.create_checkbutton(ai_row, "Use Ollama LLM", app.use_ollama_var)

    ollama_row = ttk.Frame(adv_body)
    ollama_row.pack(fill=tk.X, pady=2)
    ttk.Label(ollama_row, text="Ollama model:").pack(side=tk.LEFT, padx=(0, 4))
    app.ollama_model_var = tk.StringVar(value="llama3.1:3b")
    app.ollama_model_combobox = GUIHelper.create_combobox(
        ollama_row,
        app.ollama_model_var,
        ["llama3.1:3b", "llama2", "llama2:7b", "mistral"],
        width=16,
    )
    ttk.Button(ollama_row, text="Refresh", command=app.refresh_ollama_models, width=8).pack(
        side=tk.LEFT, padx=4
    )
    app.ollama_status_label = ttk.Label(ollama_row, text="●", foreground="gray")
    app.ollama_status_label.pack(side=tk.LEFT, padx=4)
    app.ollama_status_tooltip = "Ollama status: Unknown"
    app.available_ollama_models = ["llama3.1:3b", "llama2", "llama2:7b", "mistral"]
    app.ollama_available = False

    # --- Chat assistant (optional) ---
    chat_collapsible, chat_body = GUIHelper.create_collapsible(
        container, "Chat assistant (optional)", collapsed=True
    )
    chat_collapsible.pack(fill=tk.BOTH, expand=False, pady=2)

    chat_display_frame = ttk.Frame(chat_body)
    chat_display_frame.pack(fill=tk.BOTH, expand=True)
    app.chat_display = tk.Text(
        chat_display_frame,
        wrap=tk.WORD,
        state=tk.DISABLED,
        font=("Segoe UI", 10),
        height=6,
        bg="white",
    )
    chat_scroll = ttk.Scrollbar(chat_display_frame, orient=tk.VERTICAL, command=app.chat_display.yview)
    app.chat_display.configure(yscrollcommand=chat_scroll.set)
    app.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    chat_input = ttk.Frame(chat_body)
    chat_input.pack(fill=tk.X, pady=(4, 0))
    app.message_var = tk.StringVar()
    app.message_entry = ttk.Entry(chat_input, textvariable=app.message_var)
    app.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
    app.message_entry.bind("<Return>", lambda _e: app.send_message())
    ttk.Button(chat_input, text="Send", command=app.send_message).pack(side=tk.RIGHT)

    # --- Error log (collapsed) ---
    err_collapsible, err_body = GUIHelper.create_collapsible(container, "Error log", collapsed=True)
    err_collapsible.pack(fill=tk.X, pady=2)
    err_wrap = ttk.Frame(err_body)
    err_wrap.pack(fill=tk.X)
    app.error_display = tk.Text(
        err_wrap, wrap=tk.WORD, state=tk.DISABLED, height=3, bg="#fff5f5", fg="#d73a49"
    )
    app.error_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Button(err_wrap, text="Clear", command=app.clear_error_display).pack(side=tk.RIGHT, padx=4)

    # --- Data source (compact) ---
    file_row = ttk.Frame(container)
    file_row.pack(fill=tk.X, pady=(4, 0))
    ttk.Label(file_row, text="Data:").pack(side=tk.LEFT)
    app.data_file_var = tk.StringVar()
    app.file_path_var = tk.StringVar()
    ttk.Entry(file_row, textvariable=app.data_file_var, state="readonly", width=28).pack(
        side=tk.LEFT, padx=4
    )
    ttk.Button(file_row, text="Browse…", command=app.browse_file).pack(side=tk.LEFT)

    app.chat_state = {
        "waiting_for_timing": False,
        "waiting_for_distance": False,
        "waiting_for_duration": False,
        "waiting_for_passengers": False,
        "waiting_for_space": False,
        "rental_date": None,
        "rental_time": None,
        "rental_timing": None,
        "distance": None,
        "duration": None,
        "passenger_count": 2,
        "space_requirements": "little",
        "conversation_started": False,
        "conversation_history": [],
        "last_recommendations": None,
        "user_preferences": {},
        "trip_context": {},
    }
    app.start_chat()
