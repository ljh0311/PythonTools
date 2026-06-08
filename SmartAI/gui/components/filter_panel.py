"""
Filter panel component for the Clinic Data Visualizer.

This module contains the filter controls that allow users to filter data
by date range, time range, service type, and action.
"""

import tkinter as tk
from tkinter import ttk
from app.utils.logger import get_logger
import pandas as pd


class FilterPanel:
    """
    Filter panel component for data filtering controls.
    
    This component provides date range, time range, service type, and action
    filtering capabilities with the same appearance as the original application.
    """

    def __init__(self, parent, colors, on_filter_change=None):
        """
        Initialize the filter panel.
        
        Args:
            parent: Parent widget
            colors: Color scheme dictionary
            on_filter_change: Callback function when filters change
        """
        self.parent = parent
        self.colors = colors
        self.on_filter_change = on_filter_change
        self.logger = get_logger(__name__)

        # Initialize filter variables
        self._initialize_variables()
        
        # Create the filter panel UI
        self._create_filter_panel()

    def _initialize_variables(self):
        """Initialize filter variables"""
        # Filter variables
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.start_time_var = tk.StringVar(value="08:00")
        self.end_time_var = tk.StringVar(value="18:00")
        self.service_type_var = tk.StringVar(value="All")
        self.action_var = tk.StringVar(value="All")

    def _create_filter_panel(self):
        """Create the filter panel UI"""
        # Main filter frame
        self.filter_frame = ttk.LabelFrame(
            self.parent, text="Analysis Filters", padding="12", style="Blue.TLabelframe"
        )
        self.filter_frame.pack(fill=tk.X, pady=(0, 15), padx=0)

        # By default, all filter controls are disabled until a file is loaded in @/core
        self._filters_enabled = False  # Track enabled/disabled state

        # Date Range Filter
        self._create_date_filter()
        
        # Add separator
        ttk.Separator(self.filter_frame, orient="horizontal").pack(fill=tk.X, pady=8)
        
        # Time Range Filter
        self._create_time_filter()
        
        # Add separator
        ttk.Separator(self.filter_frame, orient="horizontal").pack(fill=tk.X, pady=8)
        
        # Service Type and Action Filters
        self._create_service_action_filters()
        
        # Apply Filters button
        self._create_apply_button()

        # Disable all filter controls initially (greyed out)
        self._set_filters_state("disabled")

        # Provide a method to enable filters when data is loaded
        def enable_filters():
            self._set_filters_state("readonly")
            self._filters_enabled = True

        def disable_filters():
            self._set_filters_state("disabled")
            self._filters_enabled = False

        self.enable_filters = enable_filters
        self.disable_filters = disable_filters

    def _create_date_filter(self):
        """Create date range filter controls"""
        # Date filter configuration
        date_config = {
            'title': 'Date Range',
            'fields': [
                {
                    'label': 'From:',
                    'var': self.start_date_var,
                    'combo': 'start_date_combo',
                    'callback': self._on_start_date_changed,
                    'width': 15
                },
                {
                    'label': 'To:',
                    'var': self.end_date_var,
                    'combo': 'end_date_combo',
                    'callback': self._on_filter_changed,
                    'width': 15
                }
            ]
        }
        
        # Create title label
        date_label = ttk.Label(
            self.filter_frame, 
            text=date_config['title'], 
            style="SectionTitle.TLabel"
        )
        date_label.pack(anchor=tk.W, pady=(0, 8))

        # Create date fields dynamically
        for i, field in enumerate(date_config['fields']):
            # Create frame for each field
            field_frame = ttk.Frame(self.filter_frame, style="Sidebar.TFrame")
            field_frame.pack(fill=tk.X, pady=(0, 8 if i == 0 else 10))

            # Create label
            field_label = ttk.Label(
                field_frame,
                text=field['label'],
                style="TLabel",
                background=self.colors["sidebar"],
            )
            field_label.pack(side=tk.LEFT, padx=(0, 5))

            # Create combobox
            combo = ttk.Combobox(
                field_frame,
                textvariable=field['var'],
                state="readonly",
                width=field['width'],
            )
            combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
            combo.bind("<<ComboboxSelected>>", field['callback'])
            
            # Store reference to combobox
            setattr(self, field['combo'], combo)

    def _create_time_filter(self):
        """Create time range filter controls"""
        # Time Range Filter with improved layout
        time_label = ttk.Label(
            self.filter_frame, text="Time Range", style="SectionTitle.TLabel"
        )
        time_label.pack(anchor=tk.W, pady=(0, 8))

        # Create time frames with consistent styling
        time_frame = ttk.Frame(self.filter_frame, style="Sidebar.TFrame")
        time_frame.pack(fill=tk.X, pady=(0, 10))

        # Start Time
        start_time_label = ttk.Label(
            time_frame,
            text="From:",
            width=5,
            style="TLabel",
            background=self.colors["sidebar"],
        )
        start_time_label.pack(side=tk.LEFT, padx=(0, 5))

        # Generate time options (8:00 to 18:00 in 15-minute intervals)
        hours = [f"{h:02d}" for h in range(8, 19)]
        minutes = [f"{m:02d}" for m in range(0, 60, 15)]
        time_options = [
            f"{h}:{m}" for h in hours for m in minutes if not (h == "18" and m != "00")
        ]

        self.start_time_combo = ttk.Combobox(
            time_frame,
            textvariable=self.start_time_var,
            values=time_options,
            state="readonly",
            width=7,
        )
        self.start_time_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.start_time_combo.bind("<<ComboboxSelected>>", self._on_start_time_changed)

        # End Time
        end_time_label = ttk.Label(
            time_frame,
            text="To:",
            width=3,
            style="TLabel",
            background=self.colors["sidebar"],
        )
        end_time_label.pack(side=tk.LEFT, padx=(0, 5))

        self.end_time_combo = ttk.Combobox(
            time_frame,
            textvariable=self.end_time_var,
            values=time_options,
            state="readonly",
            width=7,
        )
        self.end_time_combo.pack(side=tk.LEFT)
        self.end_time_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

    def _create_service_action_filters(self):
        """Create service type and action filter controls"""
        # Service Type Filter
        service_frame = ttk.Frame(self.filter_frame, style="Sidebar.TFrame")
        service_frame.pack(fill=tk.X, pady=(0, 8))

        service_label = ttk.Label(
            service_frame,
            text="Service Type:",
            style="TLabel",
            background=self.colors["sidebar"],
            width=12,
        )
        service_label.pack(side=tk.LEFT, padx=(0, 5))

        self.service_type_combo = ttk.Combobox(
            service_frame, textvariable=self.service_type_var, state="readonly"
        )
        self.service_type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.service_type_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Action Filter
        action_frame = ttk.Frame(self.filter_frame, style="Sidebar.TFrame")
        action_frame.pack(fill=tk.X, pady=(0, 12))

        action_label = ttk.Label(
            action_frame,
            text="Action:",
            style="TLabel",
            background=self.colors["sidebar"],
            width=12,
        )
        action_label.pack(side=tk.LEFT, padx=(0, 5))

        self.action_combo = ttk.Combobox(
            action_frame, textvariable=self.action_var, state="readonly"
        )
        self.action_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.action_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

    def _create_apply_button(self):
        """Create the apply filters button"""
        apply_btn = ttk.Button(
            self.filter_frame,
            text="Generate Insights",
            command=self._on_apply_filters,
            style="Accent.TButton",
        )
        apply_btn.pack(fill=tk.X, pady=(5, 0))

    def _on_start_date_changed(self, event=None):
        """Handle start date change"""
        self.logger.debug("Start date changed")
        if self.on_filter_change:
            self.on_filter_change('start_date_changed')

    def _on_start_time_changed(self, event=None):
        """Handle start time change"""
        self.logger.debug("Start time changed")
        if self.on_filter_change:
            self.on_filter_change('start_time_changed')

    def _on_filter_changed(self, event=None):
        """Handle general filter change"""
        self.logger.debug("Filter changed")
        if self.on_filter_change:
            # Delay the callback to allow UI to update
            self.parent.after(100, lambda: self.on_filter_change('filter_changed'))

    def _on_apply_filters(self):
        """Handle apply filters button click"""
        self.logger.debug("Apply filters clicked")
        if self.on_filter_change:
            self.on_filter_change('apply_filters')

    def update_date_options(self, dates):
        """
        Update available date options.
        
        Args:
            dates: List of available dates
        """
        if dates:
            # Sort dates chronologically
            date_objs = pd.to_datetime(dates, errors='coerce', dayfirst=True)
            sorted_pairs = sorted(zip(date_objs, dates))
            sorted_dates = [d for dt, d in sorted_pairs if pd.notna(dt)]
            self.sorted_dates = sorted_dates  # Store for later use
            self.start_date_combo['values'] = sorted_dates
            self.end_date_combo['values'] = sorted_dates
            # Set default values if not already set
            if not self.start_date_var.get() and sorted_dates:
                self.start_date_var.set(sorted_dates[0])
            if not self.end_date_var.get() and sorted_dates:
                self.end_date_var.set(sorted_dates[-1])
            # Add trace to update 'To' dropdown when 'From' changes
            if not hasattr(self, '_start_date_trace_added'):
                self.start_date_var.trace_add('write', self._on_start_date_var_changed)
                self._start_date_trace_added = True

    def _on_start_date_var_changed(self, *args):
        """Update 'To' dropdown to only show dates >= selected 'From' date."""
        from_date = self.start_date_var.get()
        if hasattr(self, 'sorted_dates') and self.sorted_dates and from_date:
            from_dt = pd.to_datetime(from_date, errors='coerce', dayfirst=True)
            filtered = [d for d in self.sorted_dates if pd.to_datetime(d, errors='coerce', dayfirst=True) >= from_dt]
            self.end_date_combo['values'] = filtered
            # If current 'To' date is before new 'From', reset to last available
            to_date = self.end_date_var.get()
            if to_date not in filtered and filtered:
                self.end_date_var.set(filtered[-1])

    def update_service_types(self, service_types):
        """
        Update available service type options.
        
        Args:
            service_types: List of available service types
        """
        if service_types:
            options = ["All"] + list(service_types)
            self.service_type_combo['values'] = options
            if not self.service_type_var.get():
                self.service_type_var.set("All")

    def update_actions(self, actions):
        """
        Update available action options.
        
        Args:
            actions: List of available actions
        """
        if actions:
            options = ["All"] + list(actions)
            self.action_combo['values'] = options
            if not self.action_var.get():
                self.action_var.set("All")

    def get_current_filters(self):
        """
        Get current filter values.
        
        Returns:
            dict: Dictionary containing current filter values
        """
        return {
            'start_date': self.start_date_var.get(),
            'end_date': self.end_date_var.get(),
            'start_time': self.start_time_var.get(),
            'end_time': self.end_time_var.get(),
            'service_type': self.service_type_var.get(),
            'action': self.action_var.get(),
        }

    def set_enabled(self, enabled):
        """
        Enable or disable all filter controls.
        
        Args:
            enabled: Boolean indicating whether controls should be enabled
        """
        state = "normal" if enabled else "disabled"
        
        # Update all comboboxes
        for combo in [self.start_date_combo, self.end_date_combo, 
                     self.start_time_combo, self.end_time_combo,
                     self.service_type_combo, self.action_combo]:
            combo.config(state="readonly" if enabled else "disabled")

    def reset_filters(self):
        """Reset all filters to default values"""
        self.start_time_var.set("08:00")
        self.end_time_var.set("18:00")
        self.service_type_var.set("All")
        self.action_var.set("All")
        
        # Clear date selections
        self.start_date_var.set("")
        self.end_date_var.set("") 