"""
Visualization controls component for the Clinic Data Visualizer.

This module contains the visualization type selection controls, patient selection,
and search functionality that allow users to select chart types and configure
visualization parameters.
"""

import tkinter as tk
from tkinter import ttk
from app.utils.logger import get_logger
import tkinter.simpledialog
import tkinter.messagebox
import pandas as pd


class VizControls:
    """
    Visualization controls component for chart type and patient selection.
    
    This component provides visualization type selection (radio buttons),
    patient selection controls, and search functionality with the same 
    appearance as the original application.
    """

    def __init__(self, parent, colors, on_viz_change=None):
        """
        Initialize the visualization controls.
        
        Args:
            parent: Parent widget
            colors: Color scheme dictionary
            on_viz_change: Callback function when visualization changes
        """
        self.parent = parent
        self.colors = colors
        self.on_viz_change = on_viz_change
        self.logger = get_logger(__name__)

        # Initialize variables
        self._initialize_variables()
        
        # Create the visualization controls UI
        self._create_viz_controls()

    def _initialize_variables(self):
        """Initialize visualization control variables"""
        # Visualization type variable
        self.viz_type = tk.StringVar(value="clinic_summary_dashboard")
        
        # Patient selection variables
        self.patient_id_var = tk.StringVar()
        self.patient_date_var = tk.StringVar()
        self.search_var = tk.StringVar()
        
        # Search variable for visualization filtering
        self.viz_search_var = tk.StringVar()
        
        # Store visualization radiobuttons for filtering
        self.viz_radio_buttons = []
        
        # Store previous selection for revert functionality
        self.previous_viz_type = None
        
        # Track if date filtering is active
        self.date_filter_active = False

    def _create_viz_controls(self):
        """Create the visualization controls UI"""
        # Create main container
        self.controls_frame = ttk.Frame(self.parent, style="Sidebar.TFrame")
        self.controls_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create visualization type controls
        self._setup_visualization_controls(self.controls_frame)
        
        # Create patient selection controls (initially hidden)
        self._setup_patient_selection(self.controls_frame)

    def _setup_visualization_controls(self, parent):
        """Set up the Visualization Controls section of the UI with search and categorized radio buttons"""

        # Create main visualization frame with blue styling
        viz_frame = ttk.LabelFrame(
            parent, text="Visualization Type", padding="12", style="Blue.TLabelframe"
        )
        viz_frame.pack(fill=tk.X, pady=(15, 0), padx=0)

        # SECTION 1: Search functionality for filtering visualization options
        search_frame = ttk.Frame(viz_frame, style="Sidebar.TFrame")
        search_frame.pack(fill=tk.X, pady=(0, 10))

        # Search label
        search_label = ttk.Label(
            search_frame,
            text="Search:",
            style="TLabel",
            background=self.colors["sidebar"],
        )
        search_label.pack(side=tk.LEFT, padx=(0, 5))

        # Search entry field - binds to filtering function when text changes
        self.viz_search_var.trace("w", self._filter_visualizations)
        search_entry = ttk.Entry(
            search_frame, textvariable=self.viz_search_var, state="disabled"
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # SECTION 2: Container for all visualization options
        self.viz_options_frame = ttk.Frame(viz_frame, style="Sidebar.TFrame")
        self.viz_options_frame.pack(fill=tk.X, pady=(0, 10))

        # SECTION 3: Define all available visualization categories and their options
        # Each category contains a list of (display_name, internal_value) tuples
        viz_categories = [
            (
                "Dashboard Analysis",
                [
                    ("Clinic Summary Dashboard", "clinic_summary_dashboard"),
                    ("KPI Dashboard", "kpi_dashboard"),
                    ("Enhanced Service Types", "enhanced_service_types"),
                ],
            ),
            (
                "Distribution Analysis",
                [
                    ("Service Area Distribution", "service_area_distribution"),
                    ("Service Type Distribution", "service_type_distribution"),
                    ("Action Distribution", "action_distribution"),
                    ("Patient Call Frequency", "patient_call_frequency"),
                    ("Location Distribution", "location_distribution"),
                ],
            ),
            (
                "Time Series Analysis",
                [
                    ("Hourly Activity", "hourly_activity"),
                    ("Hourly Unique Patients", "hourly_unique_patients"),
                    ("Hourly Kiosk Queue Arrivals", "hourly_unique_kiosk_queue"),
                    ("RTMS Patient Trends", "rtms_patients_trends"),
                    ("Call Volume by Hour", "call_volume_by_hour"),
                ],
            ),
            (
                "Flow Analysis",
                [
                    ("Patient Journey", "patient_journey"),
                    ("Service Transitions", "service_transitions"),
                    ("Patient Flow Analysis", "patient_flow_analysis"),
                ],
            ),
            (
                "Data Comparison",
                [
                    ("Data Comparison Tool", "data_comparison"),
                ],
            ),
            (
                "Specialized Analysis",
                [
                    ("RTMS Analysis Dashboard", "rtms_analysis_dashboard"),
                    ("Call Analysis Dashboard", "call_analysis_dashboard"),
                    ("Location Analysis Dashboard", "location_analysis_dashboard"),
                ],
            ),
        ]

        # SECTION 4: Build the UI for each category and its options
        for i, (category_name, category_options) in enumerate(viz_categories):

            # Create container frame for this entire category
            category_container = ttk.Frame(
                self.viz_options_frame, style="Sidebar.TFrame"
            )
            category_container.pack(fill=tk.X, pady=(5, 0))

            # Create and display the category title (bold header)
            category_label = ttk.Label(
                category_container,
                text=category_name,
                font=("Segoe UI", 10, "bold"),
                style="SectionTitle.TLabel",
                background=self.colors["sidebar"],
            )
            category_label.pack(anchor=tk.W, padx=0, pady=(0, 5))

            # Create frame to hold all radio buttons for this category
            category_frame = ttk.Frame(category_container, style="Sidebar.TFrame")
            category_frame.pack(fill=tk.X, anchor=tk.W, padx=(10, 0))

            # Create individual radio button for each option in this category
            for display_text, internal_value in category_options:

                # Frame to hold this single radio button
                rb_frame = ttk.Frame(category_frame, style="Sidebar.TFrame")
                rb_frame.pack(fill=tk.X, pady=2)

                # Create the radio button widget
                rb = ttk.Radiobutton(
                    rb_frame,
                    text=display_text,
                    value=internal_value,
                    variable=self.viz_type,
                    style="TRadiobutton",
                    padding=(5, 2),
                    state="disabled",  # Initialize as disabled until data is loaded
                )
                rb.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X)

                # Connect radio button to selection handler
                rb.config(command=self._on_viz_type_selected)

                # Store radio button metadata for search filtering functionality
                self.viz_radio_buttons.append(
                    {
                        "widget": rb,
                        "text": display_text.lower(),
                        "value": internal_value.lower(),
                        "category": category_name,
                        "category_frame": category_frame,
                    }
                )

            # Add visual separator between categories (except after the last one)
            if i < len(viz_categories) - 1:
                ttk.Separator(self.viz_options_frame, orient="horizontal").pack(
                    fill=tk.X, pady=5
                )

    def _setup_patient_selection(self, parent):
        """Set up the Patient Selection section of the UI"""

        # --- Main patient frame ---
        self.patient_frame = ttk.LabelFrame(
            parent, text="Patient Journey", padding="12", style="Blue.TLabelframe"
        )

        # --- Date selection group ---
        date_frame = ttk.Frame(self.patient_frame, style="Sidebar.TFrame")
        date_frame.pack(fill=tk.X, pady=(0, 10))

        date_label = ttk.Label(
            date_frame,
            text="Select Date:",
            style="TLabel",
            background=self.colors["sidebar"],
            width=10,
        )
        date_label.pack(side=tk.LEFT, padx=(0, 5))

        self.patient_date_combo = ttk.Combobox(
            date_frame, textvariable=self.patient_date_var, state="readonly"
        )
        self.patient_date_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.patient_date_combo.bind(
            "<<ComboboxSelected>>", self._update_patients_for_date
        )

        # --- Patient ID selection group ---
        patient_label = ttk.Label(
            self.patient_frame, text="Patient ID", style="SectionTitle.TLabel"
        )
        patient_label.pack(anchor=tk.W, pady=(0, 5))

        # --- Search/filter group ---
        search_frame = ttk.Frame(self.patient_frame, style="Sidebar.TFrame")
        search_frame.pack(fill=tk.X, pady=(0, 8))

        search_label = ttk.Label(
            search_frame,
            text="Search:",
            style="TLabel",
            background=self.colors["sidebar"],
        )
        search_label.pack(side=tk.LEFT, padx=(0, 5))

        self.search_var.trace("w", self._filter_patient_list)

        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- Patient dropdown ---
        self.patient_combo = ttk.Combobox(
            self.patient_frame, textvariable=self.patient_id_var, state="readonly"
        )
        self.patient_combo.pack(anchor=tk.W, pady=(0, 10), fill=tk.X)
        self.patient_combo.bind(
            "<<ComboboxSelected>>",
            self._on_patient_selected,
        )

        # --- View button ---
        select_patient_btn = ttk.Button(
            self.patient_frame,
            text="View Patient Journey",
            command=self._on_view_patient_journey,
            style="Accent.TButton",
        )
        select_patient_btn.pack(fill=tk.X, pady=(0, 10))

        # --- Informational note group ---
        info_frame = ttk.Frame(
            self.patient_frame, style="Sidebar.TFrame", padding=(5, 5)
        )
        info_frame.pack(fill=tk.X)

        info_icon = ttk.Label(
            info_frame,
            text="ℹ",
            font=("Segoe UI", 12, "bold"),
            background=self.colors["sidebar"],
            foreground=self.colors["primary"],
        )
        info_icon.pack(side=tk.LEFT, padx=(0, 5))

        info_text = ttk.Label(
            info_frame,
            text="Note: Queue numbers may be reused by different patients on different days.",
            font=("Segoe UI", 9),
            foreground=self.colors["text_secondary"],
            background=self.colors["sidebar"],
            wraplength=260,
        )
        info_text.pack(side=tk.LEFT, fill=tk.X)

        # Initially hide patient selection until needed
        self.patient_frame.pack_forget()

    def _on_viz_type_selected(self):
        """Handle visualization type selection"""
        viz_type = self.viz_type.get()
        self.logger.debug(f"Visualization type selected: {viz_type}")

        # Find the radiobutton info for this visualization type
        selected_rb_info = None
        for rb_info in self.viz_radio_buttons:
            if rb_info["value"] == viz_type:
                selected_rb_info = rb_info
                break

        # Check if the selected visualization is available (not disabled)
        if selected_rb_info and selected_rb_info["widget"].cget("state") == "disabled":
            # Selected visualization is not available, show warning
            self.logger.warning(f"Visualization '{viz_type}' is not available")
            
            # Try to revert to a previous valid selection if possible
            if self.previous_viz_type:
                self.viz_type.set(self.previous_viz_type)
            return
        
        # Store current selection for possible revert
        self.previous_viz_type = viz_type

        # Show/hide patient selection frame based on visualization type
        if viz_type in ["patient_journey", "patient_journey_des"]:
            self.patient_frame.pack(fill=tk.X, pady=(0, 15), padx=0)
        else:
            self.patient_frame.pack_forget()

        # Notify parent component of the change
        if self.on_viz_change:
            self.on_viz_change('viz_type_selected', viz_type)

    def _on_patient_selected(self, event=None):
        """Handle patient selection"""
        patient_id = self.patient_id_var.get()
        if hasattr(self, 'logger'):
            self.logger.debug(f"Patient selected: {patient_id}")
        
        # Notify parent component of the change
        if hasattr(self, 'on_viz_change') and self.on_viz_change:
            self.on_viz_change('patient_selected', patient_id)

    def _on_view_patient_journey(self):
        patient_id = self.patient_id_var.get()
        if not patient_id:
            tkinter.messagebox.showinfo("No Selection", "Please select a patient first.")
            return

        # The patient_id is already a full journey ID
        # Notify parent component to handle the patient journey visualization
        if hasattr(self, 'on_viz_change') and self.on_viz_change:
            self.on_viz_change('view_patient_journey', patient_id)
        else:
            print(f"Selected patient journey: {patient_id}")
            # Fallback: just log the selection

    def _ask_user_to_pick_full_id(self, full_ids):
        return tkinter.simpledialog.askstring(
            "Select Full Patient ID",
            "Multiple records found. Please enter the full Patient ID:\n" + "\n".join(full_ids)
        )

    def _filter_visualizations(self, *args):
        """Filter visualization options based on search query"""
        search_term = self.viz_search_var.get().lower()
        
        # If no search term, show all visualizations
        if not search_term:
            for rb_info in self.viz_radio_buttons:
                rb_info["widget"].pack(side=tk.LEFT, anchor=tk.W, fill=tk.X)
                rb_info["category_frame"].pack(fill=tk.X, anchor=tk.W, padx=(10, 0))
            return

        # Hide/show visualizations based on search term
        visible_categories = set()
        
        for rb_info in self.viz_radio_buttons:
            # Check if search term matches text or value
            if (search_term in rb_info["text"] or 
                search_term in rb_info["value"]):
                rb_info["widget"].pack(side=tk.LEFT, anchor=tk.W, fill=tk.X)
                visible_categories.add(rb_info["category"])
            else:
                rb_info["widget"].pack_forget()

        # Hide category frames that have no visible options
        for rb_info in self.viz_radio_buttons:
            if rb_info["category"] in visible_categories:
                rb_info["category_frame"].pack(fill=tk.X, anchor=tk.W, padx=(10, 0))
            else:
                rb_info["category_frame"].pack_forget()

    def _filter_patient_list(self, *args):
        """Filter the patient list based on search query"""
        search_term = self.search_var.get().lower()
        
        # Get current values from combobox
        current_values = list(self.patient_combo["values"]) if self.patient_combo["values"] else []
        
        if not search_term:
            # Show all patients if no search term
            if hasattr(self, '_all_patients'):
                self.patient_combo["values"] = self._all_patients
        else:
            # Filter patients based on search term
            if hasattr(self, '_all_patients'):
                filtered_patients = [p for p in self._all_patients if search_term in str(p).lower()]
                self.patient_combo["values"] = filtered_patients
                
                # Clear selection if current patient is not in filtered list
                if (self.patient_id_var.get() and 
                    self.patient_id_var.get() not in filtered_patients):
                    self.patient_id_var.set("")

    def _update_patients_for_date(self, event=None):
        """Update patient list for the selected date."""
        selected_date = self.patient_date_var.get()
        

        
        # Add debug logging
        if hasattr(self, 'logger'):
            self.logger.debug(f"Date filtering triggered for date: {selected_date}")
        
        # Try to get all journey IDs from stored ORIGINAL list first, then from data loader
        all_journey_ids = []
        
        # Option 1: Use stored original patient list if available (never overwritten during filtering)
        if hasattr(self, '_original_all_patients') and self._original_all_patients:
            all_journey_ids = self._original_all_patients
        # Option 2: Get from data loader if parent is available
        elif hasattr(self, 'parent') and hasattr(self.parent, 'data_loader'):
            data = self.parent.data_loader.get_data()
            if data is not None and 'Patient ID' in data.columns:
                # Get all unique Patient IDs (journey IDs) - always from data loader for consistency
                all_journey_ids = sorted(data['Patient ID'].unique())
                
                # Store this as the original list (never overwritten)
                self._original_all_patients = all_journey_ids
                # Also store in _all_patients for backward compatibility
                self._all_patients = all_journey_ids
        
        if all_journey_ids:
            if hasattr(self, 'logger'):
                self.logger.debug(f"Total journey IDs available: {len(all_journey_ids)}")
            
            if selected_date:
                # Filter journey IDs that contain the selected date
                # Journey ID format: <queue_number>_<date>_<time>_<journey_num>
                # Extract date from journey ID and compare with selected date
                filtered_journey_ids = []
                
                for journey_id in all_journey_ids:
                    try:
                        # Parse journey ID to extract date
                        parts = journey_id.split('_')
                        if len(parts) >= 2:
                            # The date is the second part (index 1)
                            journey_date_str = parts[1]
                            
                            # Convert journey date to DD/MM/YYYY format for comparison
                            if journey_date_str != "unknown":
                                # Parse YYYYMMDD format
                                journey_date = pd.to_datetime(journey_date_str, format='%Y%m%d')
                                journey_date_formatted = journey_date.strftime('%d/%m/%Y')
                                
                                if journey_date_formatted == selected_date:
                                    filtered_journey_ids.append(journey_id)
                    except Exception as e:
                        # Skip invalid journey IDs
                        if hasattr(self, 'logger'):
                            self.logger.debug(f"Error parsing journey ID {journey_id}: {e}")
                        continue
                
                self.patient_combo['values'] = filtered_journey_ids
                # DON'T overwrite _all_patients or _original_all_patients - keep them intact for future filtering
                self.date_filter_active = True
                
                if hasattr(self, 'logger'):
                    self.logger.info(f"Updated patient list for date {selected_date}: {len(filtered_journey_ids)} journeys")
                else:
                    print(f"Updated patient list for date {selected_date}: {len(filtered_journey_ids)} journeys")
                
                # Clear selection if current patient is not in filtered list
                if (self.patient_id_var.get() and 
                    self.patient_id_var.get() not in filtered_journey_ids):
                    self.patient_id_var.set("")
            else:
                # No date selected, show all journey IDs
                self.patient_combo['values'] = all_journey_ids
                # DON'T overwrite the original list
                self.date_filter_active = False
                if hasattr(self, 'logger'):
                    self.logger.info(f"Showing all journeys: {len(all_journey_ids)} total")
                else:
                    print(f"Showing all journeys: {len(all_journey_ids)} total")
        else:
            if hasattr(self, 'logger'):
                self.logger.warning("No journey IDs available for filtering")
            else:
                print("No journey IDs available for filtering")

    def get_current_selection(self):
        """Get current selection values"""
        return {
            'viz_type': self.viz_type.get(),
            'patient_id': self.patient_id_var.get(),
            'patient_date': self.patient_date_var.get(),
            'search_term': self.search_var.get(),
            'viz_search_term': self.viz_search_var.get(),
        }

    def set_enabled(self, enabled):
        """Enable or disable all controls"""
        state = "normal" if enabled else "disabled"
        
        # Enable/disable visualization radio buttons
        for rb_info in self.viz_radio_buttons:
            rb_info["widget"].configure(state=state)
        
        # Enable/disable patient controls
        if hasattr(self, 'patient_date_combo'):
            self.patient_date_combo.configure(state="readonly" if enabled else "disabled")
        if hasattr(self, 'patient_combo'):
            self.patient_combo.configure(state="readonly" if enabled else "disabled")

    def update_patient_dates(self, dates):
        """Update available patient dates"""
        if hasattr(self, 'patient_date_combo'):
            self.patient_date_combo["values"] = dates
            if dates and not self.patient_date_var.get():
                self.patient_date_var.set(dates[0])
                # Trigger patient filtering for the newly set date
                self._update_patients_for_date()

    def update_patients(self, patients):
        """Update available patients"""
        if hasattr(self, 'patient_combo'):
            # Store both the current list and original list for filtering
            self._all_patients = patients
            # Store original list (never overwritten during filtering)
            if not hasattr(self, '_original_all_patients') or not self._original_all_patients:
                self._original_all_patients = patients
            
            # Check if there's a date filter active
            selected_date = self.patient_date_var.get()
            filter_active = getattr(self, 'date_filter_active', False)
            
            if selected_date and filter_active:
                # Apply date filtering to the new patient list
                self._update_patients_for_date()
            else:
                # No date filter, show all patients
                self.patient_combo["values"] = patients
                if patients and not self.patient_id_var.get():
                    self.patient_id_var.set(patients[0])

    def show_patient_controls(self, show=True):
        """Show or hide patient selection controls"""
        if show:
            self.patient_frame.pack(fill=tk.X, pady=(0, 15), padx=0)
        else:
            self.patient_frame.pack_forget()

    def set_viz_type(self, viz_type):
        """Set the current visualization type"""
        self.viz_type.set(viz_type)
        self._on_viz_type_selected()

    def get_viz_type(self):
        """Get the current visualization type"""
        return self.viz_type.get()
        
    def reset_selection(self):
        """Reset all selection variables to default state"""
        self.patient_id_var.set("")
        self.patient_date_var.set("")
        self.search_var.set("")
        self.viz_search_var.set("")
        
        # Clear combobox values
        if hasattr(self, 'patient_combo'):
            self.patient_combo["values"] = []
        if hasattr(self, 'patient_date_combo'):
            self.patient_date_combo["values"] = [] 