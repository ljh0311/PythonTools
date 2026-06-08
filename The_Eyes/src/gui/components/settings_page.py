import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from config.user_config_manager import (
    get_merged_config, save_user_config, load_user_config, 
    set_config_value, reset_config_to_defaults, export_config_template,
    import_config_from_file
)

logger = logging.getLogger(__name__)

class SettingsPage(ttk.Frame):
    def __init__(self, parent, on_config_change=None):
        super().__init__(parent)
        self.parent = parent
        self.entries = {}
        self.on_config_change = on_config_change  # Callback for config changes
        self._build_ui()

    def _build_ui(self):
        """Build the settings UI with tabbed interface"""
        try:
            # Create main container with proper weight configuration
            self.columnconfigure(0, weight=1)
            self.rowconfigure(0, weight=1)
            self.rowconfigure(1, weight=0)  # Button frame should not expand
            
            # Set minimum window size for settings dialog
            self.master.minsize(800, 600)
            
            # Create notebook for tabs
            self.notebook = ttk.Notebook(self)
            self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(10, 0))

            # Create tabs for different config sections (consolidated)
            self._create_app_tab()
            self._create_data_tab()
            self._create_data_quality_tab()
            self._create_data_processing_tab()
            self._create_columns_tab()
            self._create_consultation_tab()
            self._create_visualization_tab()
            self._create_journey_tab()
            self._create_export_tab()

            # Create button frame at bottom
            button_frame = ttk.Frame(self)
            button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=(10, 10))

            # Buttons
            ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_settings).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="Export Config", command=self.export_config).pack(side=tk.RIGHT, padx=(5, 0))
            ttk.Button(button_frame, text="Import Config", command=self.import_config).pack(side=tk.RIGHT, padx=(5, 0))
            
        except Exception as e:
            logger.error(f"Error building settings UI: {e}")
            # Show error message
            error_label = ttk.Label(self, text=f"Error loading settings: {str(e)}", foreground="red")
            error_label.pack(pady=20)

    def _get_nested_value(self, config_data, section, key):
        """Get a nested value from config data"""
        try:
            section_data = config_data.get(section, {})
            if isinstance(section_data, dict):
                return section_data.get(key, "")
            else:
                # If section is not a dict, try to get the key directly
                return config_data.get(key, "")
        except Exception as e:
            logger.error(f"Error getting nested value for {section}.{key}: {e}")
            return ""

    def _create_scrollable_frame(self, parent):
        """Create a scrollable frame for tab content that always fits the window"""
        # Create a frame to hold both canvas and scrollbar, and grid it to fill parent
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        # Create canvas and scrollbar
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Create the scrollable frame inside the canvas
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Make canvas expand with container
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make the canvas width match the container width
            canvas_width = container.winfo_width()
            canvas.itemconfig(scrollable_frame_id, width=canvas_width)

        scrollable_frame.bind("<Configure>", _on_frame_configure)
        container.bind("<Configure>", lambda e: canvas.itemconfig(scrollable_frame_id, width=container.winfo_width()))

        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mouse wheel scrolling
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass

        canvas.bind("<MouseWheel>", _on_mousewheel)

        return scrollable_frame

    def _add_field(self, parent, section, key, label, field_type, options=None):
        """Add a field to the settings form, using dropdowns for fixed choices"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=10, pady=2)

        # Label
        ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)

        # Get current value using the nested getter
        config_data = get_merged_config()
        value = self._get_nested_value(config_data, section, key)

        # Dropdown fields
        if field_type == "dropdown" and options:
            var = tk.StringVar(value=str(value))
            widget = ttk.Combobox(frame, textvariable=var, values=options, state="readonly", width=30)
            widget.pack(side=tk.LEFT, padx=(5, 0))
        elif field_type == "boolean":
            var = tk.BooleanVar(value=bool(value))
            widget = ttk.Checkbutton(frame, variable=var)
            widget.pack(side=tk.LEFT, padx=(5, 0))
        elif field_type == "number":
            var = tk.StringVar(value=str(value))
            widget = ttk.Entry(frame, textvariable=var, width=20)
            widget.pack(side=tk.LEFT, padx=(5, 0))
        elif field_type == "list":
            var = tk.StringVar(value=str(value))
            widget = ttk.Entry(frame, textvariable=var, width=40)
            widget.pack(side=tk.LEFT, padx=(5, 0))
        else:  # text
            var = tk.StringVar(value=str(value))
            widget = ttk.Entry(frame, textvariable=var, width=30)
            widget.pack(side=tk.LEFT, padx=(5, 0))

        # Store reference
        self.entries[(section, key)] = (var, field_type)

    def _add_readonly_field(self, parent, section, key, label, default_value):
        """Add a read-only field to the settings form."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=10, pady=2)

        # Label
        ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)

        # Read-only entry with gray background
        var = tk.StringVar(value=default_value)
        widget = ttk.Entry(frame, textvariable=var, width=30, state="readonly")
        widget.pack(side=tk.LEFT, padx=(5, 0))
        
        # Add a small info label
        info_label = ttk.Label(frame, text="(System Generated)", font=("Segoe UI", 8), foreground="gray")
        info_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Store reference with readonly field type
        self.entries[(section, key)] = (var, "readonly")

    def _create_app_tab(self):
        """Create the Application settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Application")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # App settings
        self._add_section_header(scrollable_frame, "Application Settings")
        self._add_field(scrollable_frame, "app", "app_name", "Application Name", "text")
        self._add_field(scrollable_frame, "app", "debug_mode", "Debug Mode", "boolean")
        self._add_field(scrollable_frame, "app", "environment", "Environment", "dropdown", ["development", "production", "test"])

        # Window settings
        self._add_section_header(scrollable_frame, "Window Settings")
        self._add_field(scrollable_frame, "app", "window_title", "Window Title", "text")
        # window_size and window_min_size are now set automatically and not user-editable

    def _create_data_tab(self):
        """Create the Data settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Data")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # Data loading settings
        self._add_section_header(scrollable_frame, "Data Loading")
        self._add_field(scrollable_frame, "data", "encoding", "File Encoding", "dropdown", ["utf-8", "latin-1", "cp1252", "ascii"])
        self._add_field(scrollable_frame, "data", "chunk_size", "Chunk Size", "number")
        self._add_field(scrollable_frame, "data", "validate_on_load", "Validate on Load", "boolean")
        self._add_field(scrollable_frame, "data", "auto_clean_data", "Auto Clean Data", "boolean")

        # Data quality settings
        self._add_section_header(scrollable_frame, "Data Quality")
        self._add_field(scrollable_frame, "data_quality", "min_completeness_threshold", "Min Completeness", "number")
        self._add_field(scrollable_frame, "data_quality", "max_duplicate_ratio", "Max Duplicate Ratio", "number")
        self._add_field(scrollable_frame, "data_quality", "min_uniqueness_threshold", "Min Uniqueness", "number")

    def _create_data_quality_tab(self):
        """Create the Data Quality settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Data Quality")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # Completeness thresholds
        self._add_section_header(scrollable_frame, "Completeness Thresholds")
        self._add_field(scrollable_frame, "data_quality", "min_completeness_threshold", "Min Completeness (%)", "number")
        self._add_field(scrollable_frame, "data_quality", "critical_column_threshold", "Critical Column Threshold (%)", "number")

        # Consistency thresholds
        self._add_section_header(scrollable_frame, "Consistency Thresholds")
        self._add_field(scrollable_frame, "data_quality", "max_duplicate_ratio", "Max Duplicate Ratio (%)", "number")
        self._add_field(scrollable_frame, "data_quality", "max_inconsistent_ratio", "Max Inconsistent Ratio (%)", "number")

        # Uniqueness thresholds
        self._add_section_header(scrollable_frame, "Uniqueness Thresholds")
        self._add_field(scrollable_frame, "data_quality", "min_uniqueness_threshold", "Min Uniqueness (%)", "number")

        # Timeliness thresholds
        self._add_section_header(scrollable_frame, "Timeliness Thresholds")
        self._add_field(scrollable_frame, "data_quality", "max_date_range_days", "Max Date Range (days)", "number")
        self._add_field(scrollable_frame, "data_quality", "min_date_range_days", "Min Date Range (days)", "number")

        # Critical and optional columns
        self._add_section_header(scrollable_frame, "Column Configuration")
        self._add_field(scrollable_frame, "data_quality", "critical_columns", "Critical Columns", "list")
        self._add_field(scrollable_frame, "data_quality", "optional_columns", "Optional Columns", "list")

    def _create_data_processing_tab(self):
        """Create the Data Processing settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Data Processing")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # Memory optimization
        self._add_section_header(scrollable_frame, "Memory Optimization")
        self._add_field(scrollable_frame, "processing", "enable_memory_optimization", "Enable Memory Optimization", "boolean")
        self._add_field(scrollable_frame, "processing", "enable_caching", "Enable Caching", "boolean")
        self._add_field(scrollable_frame, "processing", "cache_large_files", "Cache Large Files", "boolean")
        self._add_field(scrollable_frame, "processing", "large_file_threshold_mb", "Large File Threshold (MB)", "number")

        # Chunked processing
        self._add_section_header(scrollable_frame, "Chunked Processing")
        self._add_field(scrollable_frame, "processing", "chunk_size", "Chunk Size", "number")
        self._add_field(scrollable_frame, "processing", "enable_chunked_loading", "Enable Chunked Loading", "boolean")

        # Data type optimization
        self._add_section_header(scrollable_frame, "Data Type Optimization")
        self._add_field(scrollable_frame, "processing", "enable_dtype_optimization", "Enable Data Type Optimization", "boolean")
        self._add_field(scrollable_frame, "processing", "categorical_threshold", "Categorical Threshold (%)", "number")

        # Error handling
        self._add_section_header(scrollable_frame, "Error Handling")
        self._add_field(scrollable_frame, "processing", "max_errors_before_fail", "Max Errors Before Fail", "number")
        self._add_field(scrollable_frame, "processing", "continue_on_error", "Continue On Error", "boolean")

        # Performance settings
        self._add_section_header(scrollable_frame, "Performance Settings")
        self._add_field(scrollable_frame, "processing", "enable_parallel_processing", "Enable Parallel Processing", "boolean")
        self._add_field(scrollable_frame, "processing", "max_workers", "Max Workers", "number")

    def _create_columns_tab(self):
        """Create the Columns settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Columns")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # Core columns
        self._add_section_header(scrollable_frame, "Core Columns")
        self._add_field(scrollable_frame, "columns", "patient_id", "Patient ID Column", "text")
        self._add_field(scrollable_frame, "columns", "queue_number", "Queue Number Column", "text")
        self._add_field(scrollable_frame, "columns", "service_date", "Service Date Column", "text")
        self._add_field(scrollable_frame, "columns", "service_timestamp", "Service Timestamp Column", "text")
        self._add_field(scrollable_frame, "columns", "service_type", "Service Type Column", "text")
        self._add_field(scrollable_frame, "columns", "service_area", "Service Area Column", "text")
        self._add_field(scrollable_frame, "columns", "action", "Action Column", "text")
        self._add_field(scrollable_frame, "columns", "location", "Location Column", "text")
        self._add_field(scrollable_frame, "columns", "sequence", "Sequence Column", "text")

        # Calculated columns (read-only, not user configurable)
        self._add_section_header(scrollable_frame, "Calculated Columns (System Generated)")
        self._add_readonly_field(scrollable_frame, "columns", "hour", "Hour Column", "Hour")
        self._add_readonly_field(scrollable_frame, "columns", "hour_float", "Hour Float Column", "Hour_Float")
        self._add_readonly_field(scrollable_frame, "columns", "day_of_week", "Day of Week Column", "Day of Week")
        self._add_readonly_field(scrollable_frame, "columns", "service_duration", "Service Duration Column", "Service Duration")
        self._add_readonly_field(scrollable_frame, "columns", "enhanced_service_type", "Enhanced Service Type Column", "Enhanced Service Type")
        self._add_readonly_field(scrollable_frame, "columns", "simple_patient_id", "Simple Patient ID Column", "Simple Patient ID")

        # Date/time formats
        self._add_section_header(scrollable_frame, "Date/Time Formats")
        self._add_field(scrollable_frame, "columns", "date_format", "Date Format", "text")
        self._add_field(scrollable_frame, "columns", "time_format", "Time Format", "text")
        self._add_field(scrollable_frame, "columns", "datetime_format", "DateTime Format", "text")

    def _create_consultation_tab(self):
        """Create the Consultation settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Consultation")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # Consultation splitting
        self._add_section_header(scrollable_frame, "Consultation Splitting")
        self._add_field(scrollable_frame, "consultation", "enable_consultation_splitting", "Enable Consultation Splitting", "boolean")
        self._add_field(scrollable_frame, "consultation", "fv_rv_ratio", "FV/RV Ratio", "number")
        self._add_field(scrollable_frame, "consultation", "splitting_random_seed", "Splitting Random Seed", "number")
        self._add_field(scrollable_frame, "consultation", "min_sample_size_for_splitting", "Min Sample Size for Splitting", "number")

        # Service names
        self._add_section_header(scrollable_frame, "Service Names")
        self._add_field(scrollable_frame, "consultation", "fv_service_name", "FV Service Name", "text")
        self._add_field(scrollable_frame, "consultation", "rv_service_name", "RV Service Name", "text")
        self._add_field(scrollable_frame, "consultation", "original_consultation_name", "Original Consultation Name", "text")

    def _create_visualization_tab(self):
        """Create the Visualization settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Visualization")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # Chart settings
        self._add_section_header(scrollable_frame, "Chart Settings")
        self._add_field(scrollable_frame, "visualization", "style", "Chart Style", "dropdown", ["seaborn-v0_8", "ggplot", "classic", "bmh", "dark_background"])
        self._add_field(scrollable_frame, "visualization", "figure_size", "Figure Size", "list")
        self._add_field(scrollable_frame, "visualization", "dpi", "DPI", "number")
        self._add_field(scrollable_frame, "visualization", "color_palette", "Color Palette", "dropdown", ["Set2", "Set1", "Set3", "Pastel1", "Pastel2", "Dark2", "Accent"])

        # Font settings
        self._add_section_header(scrollable_frame, "Font Settings")
        self._add_field(scrollable_frame, "visualization", "font_family", "Font Family", "dropdown", ["DejaVu Sans", "Arial", "Calibri", "Times New Roman", "Verdana"])
        self._add_field(scrollable_frame, "visualization", "font_size", "Font Size", "number")
        self._add_field(scrollable_frame, "visualization", "title_font_size", "Title Font Size", "number")

        # Performance settings
        self._add_section_header(scrollable_frame, "Performance")
        # Performance settings with data sampling explanation
        self._add_field(scrollable_frame, "visualization", "enable_sampling", "Enable Sampling", "boolean")
        self._add_field(scrollable_frame, "visualization", "sampling_ratio", "Sampling Ratio", "number")
        self._add_field(scrollable_frame, "visualization", "max_sample_size", "Max Sample Size", "number")
        
        # Add explanation container for sampling settings
        sampling_info_frame = ttk.LabelFrame(scrollable_frame, text="📊 Data Sampling Information", padding=(10, 5))
        sampling_info_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # Create a canvas with scrollbar for scrollable content
        canvas = tk.Canvas(sampling_info_frame, height=150)
        scrollbar = ttk.Scrollbar(sampling_info_frame, orient="vertical", command=canvas.yview)
        scrollable_content = ttk.Frame(canvas)
        
        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        info_text = """Data sampling improves performance for large datasets by intelligently reducing data size while preserving statistical accuracy and patterns.

• Enable Sampling: Automatically samples datasets >1,500 records for faster visualization
• Sampling Ratio: Percentage of data to keep (0.1-1.0, default: 0.3 for large datasets)
• Max Sample Size: Maximum records to use (default: 20,000 for optimal performance)

The sampler uses smart strategies:
• Stratified sampling preserves data distribution patterns
• Temporal sampling maintains time-based trends
• 90%+ performance improvement with statistically valid results

Large clinic datasets (>25k records) are automatically optimized for visualization speed."""
        
        info_label = ttk.Label(scrollable_content, text=info_text, wraplength=500, justify=tk.LEFT)
        info_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel scrolling with proper error handling
        def _on_mousewheel(event):
            try:
                # Check if canvas still exists and is valid
                if canvas and canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                # Canvas has been destroyed, ignore the event
                pass
            except Exception as e:
                # Log any other errors but don't crash
                print(f"Mousewheel error: {e}")
        
        # Bind mousewheel to this specific canvas only, not globally
        canvas.bind("<MouseWheel>", _on_mousewheel)



    def _create_journey_tab(self):
        """Create the Journey settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Journey")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # Journey settings
        self._add_section_header(scrollable_frame, "Journey Configuration")
        self._add_field(scrollable_frame, "journey", "enabled", "Enable Journey Identification", "boolean")
        self._add_field(scrollable_frame, "journey", "max_gap_minutes", "Max Gap (minutes)", "number")
        self._add_field(scrollable_frame, "journey", "same_day_only", "Same Day Only", "boolean")
        self._add_field(scrollable_frame, "journey", "include_service_type", "Include Service Type", "boolean")

        # Action types
        self._add_section_header(scrollable_frame, "Action Types")
        self._add_field(scrollable_frame, "journey", "registration_actions", "Registration Actions", "list")
        self._add_field(scrollable_frame, "journey", "completion_actions", "Completion Actions", "list")
        self._add_field(scrollable_frame, "journey", "transfer_actions", "Transfer Actions", "list")
        self._add_field(scrollable_frame, "journey", "wait_actions", "Wait Actions", "list")
        self._add_field(scrollable_frame, "journey", "service_actions", "Service Actions", "list")

        # Journey help section
        self._add_section_header(scrollable_frame, "Journey Configuration Help")
        self._add_journey_help_section(scrollable_frame)

    def _create_export_tab(self):
        """Create the Export settings tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Export")

        # Create scrollable content
        scrollable_frame = self._create_scrollable_frame(frame)

        # Export settings
        self._add_section_header(scrollable_frame, "Export Settings")
        self._add_field(scrollable_frame, "export", "default_format", "Default Format", "dropdown", ["png", "pdf", "svg", "jpeg", "eps"])
        self._add_field(scrollable_frame, "export", "default_dpi", "Default DPI", "number")
        self._add_field(scrollable_frame, "export", "include_timestamp", "Include Timestamp", "boolean")
        self._add_field(scrollable_frame, "export", "timestamp_format", "Timestamp Format", "text")
        self._add_field(scrollable_frame, "export", "filename_prefix", "Filename Prefix", "text")

        # Quality settings
        self._add_section_header(scrollable_frame, "Quality Settings")
        self._add_field(scrollable_frame, "export", "high_quality_dpi", "High Quality DPI", "number")
        self._add_field(scrollable_frame, "export", "web_quality_dpi", "Web Quality DPI", "number")
        self._add_field(scrollable_frame, "export", "print_quality_dpi", "Print Quality DPI", "number")



    def _add_section_header(self, parent, text):
        """Add a section header"""
        header = ttk.Label(parent, text=text, font=("Segoe UI", 12, "bold"))
        header.pack(anchor=tk.W, pady=(15, 5), padx=10)

    def save_settings(self):
        """Save all settings to JSON"""
        try:
            # Collect all values from entries
            new_config = {}
            for (section, key), (var, field_type) in self.entries.items():
                # Skip readonly fields (calculated columns)
                if field_type == "readonly":
                    continue
                    
                if section not in new_config:
                    new_config[section] = {}
                
                value = var.get()
                
                # Convert value based on field type
                if field_type == "boolean":
                    new_config[section][key] = bool(value)
                elif field_type == "number":
                    try:
                        # Handle percentage fields (remove % if present)
                        if "%" in str(value):
                            value = str(value).replace("%", "").strip()
                        new_config[section][key] = float(value) if "." in value else int(value)
                    except ValueError:
                        new_config[section][key] = 0
                elif field_type == "list":
                    # Try to parse as list (simple comma-separated for now)
                    try:
                        if value.startswith("[") and value.endswith("]"):
                            # Remove brackets and split
                            list_str = value[1:-1]
                            new_config[section][key] = [item.strip().strip('"\'') for item in list_str.split(",")]
                        else:
                            new_config[section][key] = value
                    except:
                        new_config[section][key] = value
                else:
                    new_config[section][key] = value

            # Save to JSON
            if save_user_config(new_config):
                messagebox.showinfo("Success", "Settings saved successfully!")
                
                # Notify parent of configuration changes
                if self.on_config_change:
                    try:
                        self.on_config_change(new_config)
                    except Exception as e:
                        logger.error(f"Error in config change callback: {e}")
            else:
                messagebox.showerror("Error", "Failed to save settings!")
                
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Error saving settings: {str(e)}")

    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            if reset_config_to_defaults():
                messagebox.showinfo("Success", "Settings reset to defaults!")
                # Reload the page
                # Clear and rebuild UI
                for widget in self.winfo_children():
                    widget.destroy()
                self._build_ui()
            else:
                messagebox.showerror("Error", "Failed to reset settings!")

    def export_config(self):
        """Export current config as template"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Configuration"
        )
        if file_path:
            if export_config_template():
                messagebox.showinfo("Success", f"Configuration exported to {file_path}")
            else:
                messagebox.showerror("Error", "Failed to export configuration!")

    def import_config(self):
        """Import config from file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Configuration"
        )
        if file_path:
            if import_config_from_file(file_path):
                messagebox.showinfo("Success", "Configuration imported successfully!")
                # Reload the page
                # Clear and rebuild UI
                for widget in self.winfo_children():
                    widget.destroy()
                self._build_ui()
            else:
                messagebox.showerror("Error", "Failed to import configuration!")

    def select_tab(self, tab_name):
        """Select a tab by its name (case-insensitive)."""
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text").lower() == tab_name.lower():
                self.notebook.select(i)
                break

    def cleanup(self):
        """Clean up resources when the settings page is destroyed."""
        try:
            # Unbind mouse wheel events from help canvas if it exists
            if hasattr(self, '_help_canvas') and self._help_canvas:
                try:
                    self._help_canvas.unbind("<MouseWheel>")
                except:
                    pass
        except Exception as e:
            logger.error(f"Error cleaning up settings page: {e}")

    def destroy(self):
        """Override destroy to ensure proper cleanup."""
        self.cleanup()
        super().destroy()

    def _add_journey_help_section(self, parent):
        """Add journey configuration help section"""
        help_frame = ttk.Frame(parent)
        help_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create a canvas with scrollbar for scrollable content
        canvas = tk.Canvas(help_frame, height=200)
        scrollbar = ttk.Scrollbar(help_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        help_text = """Patient Journey Configuration Help

What is Patient Journey Identification?
Patient journey identification groups related patient activities into distinct "journeys" or visits. This helps analyze patient flow and service patterns.

Configuration Options:

1. Maximum Time Gap (minutes)
   - Defines the maximum time between activities to consider them part of the same journey
   - Shorter gaps = more separate journeys
   - Longer gaps = fewer, longer journeys

2. Same Day Only
   - When enabled: Only group activities within the same calendar day
   - When disabled: Allow journeys to span multiple days

3. Include Service Type
   - When enabled: Start a new journey when service type changes
   - When disabled: Group by time gaps only

4. Enable/Disable
   - When disabled: Use simple Patient IDs (Queue Numbers)
   - When enabled: Use complex journey-based Patient IDs

Recommended Settings:
• For most clinics: Use default settings (30 min, same day, include service type)
• For long procedures: Increase time gap to 45-60 minutes
• For simple analysis: Disable service type grouping

Note: Changes may require reloading your data to take effect."""
        
        help_label = ttk.Label(
            scrollable_frame,
            text=help_text,
            font=("Segoe UI", 9),
            wraplength=500,
            justify=tk.LEFT
        )
        help_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel scrolling
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                # Canvas was destroyed, ignore the event
                pass
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Store canvas reference for cleanup
        self._help_canvas = canvas