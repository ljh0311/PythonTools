"""
Data loading dialog for the Clinic Data Visualizer application.

This module provides the data loading dialog with progress tracking and quality checks,
with the same appearance and behavior as the original.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime


class DataLoadingDialog:
    """A dialog for loading and preprocessing clinic data with advanced options"""

    def __init__(self, parent, processor):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Load Clinic Data")
        self.dialog.geometry("700x600")  # Increased size for log panel
        self.dialog.minsize(600, 500)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Store references
        self.parent = parent
        self.processor = processor
        self.file_path = None
        self.success = False
        
        # Create main container with padding
        main_frame = ttk.Frame(self.dialog, padding="10", style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File Selection Section
        file_frame = ttk.LabelFrame(main_frame, text="Data File Selection", padding="10", style="Card.TLabelframe")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File path display
        self.file_path_var = tk.StringVar()
        file_path_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=50, style="TEntry")
        file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Browse button
        browse_btn = ttk.Button(file_frame, text="Browse", command=self._browse_file, style="Primary.TButton")
        browse_btn.pack(side=tk.LEFT)
        
        # Preprocessing Options Section
        options_frame = ttk.LabelFrame(main_frame, text="Preprocessing Options", padding="10", style="Card.TLabelframe")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Data Quality Checks
        self.check_quality_var = tk.BooleanVar(value=True)
        quality_check = ttk.Checkbutton(
            options_frame, 
            text="Perform data quality checks",
            variable=self.check_quality_var,
            style="TCheckbutton"
        )
        quality_check.pack(anchor=tk.W, pady=2)
        
        # Add tooltip for quality checks
        self._create_tooltip(quality_check, 
            "Check for missing values, inconsistencies, and data format issues")
            
        # Add memory optimization option
        self.optimize_memory_var = tk.BooleanVar(value=True)
        memory_check = ttk.Checkbutton(
            options_frame,
            text="Optimize memory usage",
            variable=self.optimize_memory_var,
            style="TCheckbutton"
        )
        memory_check.pack(anchor=tk.W, pady=2)
        
        # Add tooltip for memory optimization
        self._create_tooltip(memory_check,
            "Convert data types to more memory-efficient formats when possible")
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Loading Progress", padding="10", style="Card.TLabelframe")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            mode='determinate', 
            variable=self.progress_var,
            style="TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # Status message
        self.status_var = tk.StringVar(value="Ready to load data")
        status_label = ttk.Label(
            progress_frame, 
            textvariable=self.status_var,
            wraplength=550,
            style="TLabel"
        )
        status_label.pack(fill=tk.X)
        
        # Add Log Panel
        log_frame = ttk.LabelFrame(main_frame, text="Loading Log", padding="10", style="Card.TLabelframe")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Add scrolled text widget for log
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=10,
            font=("Consolas", 9),
            background="#F8F8F8"  # This will be updated by theme system
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)  # Make read-only
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Load button
        self.load_btn = ttk.Button(
            button_frame,
            text="Load Data",
            command=self._load_data,
            style="Accent.TButton"
        )
        self.load_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            style="Accent.TButton"
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        # Center the dialog on parent window
        self.dialog.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Create tooltip window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(
                self.tooltip, 
                text=text, 
                background="#ffffe0", 
                relief="solid", 
                borderwidth=1,
                wraplength=300
            )
            label.pack()
            
        def leave(event):
            if hasattr(self, "tooltip"):
                self.tooltip.destroy()
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        
    def _log_message(self, message, level="INFO"):
        """Add a message to the log panel"""
        self.log_text.config(state=tk.NORMAL)
        
        # Define colors for different log levels
        level_colors = {
            "INFO": "black",
            "WARNING": "#FF9800",
            "ERROR": "#F44336",
            "SUCCESS": "#4CAF50"
        }
        
        # Get timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format the log entry
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # Insert with appropriate color
        self.log_text.insert(tk.END, log_entry)
        
        # Apply color tag
        start_idx = self.log_text.index(f"end-{len(log_entry)+1}c")
        end_idx = self.log_text.index("end-1c")
        tag_name = f"log_{level.lower()}"
        
        if not tag_name in self.log_text.tag_names():
            self.log_text.tag_configure(tag_name, foreground=level_colors.get(level, "black"))
            
        self.log_text.tag_add(tag_name, start_idx, end_idx)
        
        # Auto-scroll to the end
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def _browse_file(self):
        """Open file dialog to select data file"""
        # Set initial directory to datasets folder if it exists
        initial_dir = os.getcwd()
        datasets_dir = os.path.join(initial_dir, "datasets")
        if os.path.exists(datasets_dir):
            initial_dir = datasets_dir
        
        file_path = filedialog.askopenfilename(
            title="Select Clinic Data File",
            initialdir=initial_dir,
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"), 
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.file_path = file_path
            self.file_path_var.set(file_path)
            self._log_message(f"Selected file: {file_path}")
            
    def _update_progress(self, value, message):
        """Update progress bar and status message"""
        self.progress_var.set(value)
        self.status_var.set(message)
        self._log_message(message)
        self.dialog.update_idletasks()
        
    def _load_data(self):
        """Load and preprocess the data"""
        if not self.file_path:
            messagebox.showwarning("Warning", "Please select a data file first.")
            self._log_message("No file selected", "WARNING")
            return
            
        try:
            self.load_btn.config(state="disabled")
            self._update_progress(10, "Checking file...")
            
            if not os.path.exists(self.file_path):
                error_msg = "Selected file does not exist"
                self._log_message(error_msg, "ERROR")
                raise FileNotFoundError(error_msg)
                
            self._update_progress(20, "Initializing data processor...")
            
            # Check file size and warn if large
            file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
            if file_size_mb > 50:  # Warn if file is larger than 50 MB
                self._log_message(f"Large file detected: {file_size_mb:.1f} MB. Loading may take longer.", "WARNING")
                
            # Pass memory optimization flag to processor if method supports it
            if hasattr(self.processor, 'set_memory_optimization'):
                self.processor.set_memory_optimization(self.optimize_memory_var.get())
                self._log_message(f"Memory optimization: {'enabled' if self.optimize_memory_var.get() else 'disabled'}")
            
            # Load the data
            self._update_progress(40, "Loading data...")
            start_time = datetime.now()
            success, message = self.processor.load_data(self.file_path)
            end_time = datetime.now()
            load_time = (end_time - start_time).total_seconds()
            
            if not success:
                self._log_message(f"Error loading data: {message}", "ERROR")
                raise Exception(message)
                
            self._log_message(f"Data loaded in {load_time:.2f} seconds", "SUCCESS")
            
            # Add data summary info to log
            if hasattr(self.processor, 'data') and self.processor.data is not None:
                row_count = len(self.processor.data)
                column_count = len(self.processor.data.columns) if hasattr(self.processor.data, 'columns') else 0
                self._log_message(f"Loaded {row_count} rows with {column_count} columns", "INFO")
                
                # Log memory usage if pandas DataFrame
                if hasattr(self.processor.data, 'memory_usage'):
                    memory_usage_mb = self.processor.data.memory_usage(deep=True).sum() / (1024 * 1024)
                    self._log_message(f"Memory usage: {memory_usage_mb:.2f} MB", "INFO")
                
            # Perform quality checks if selected
            if self.check_quality_var.get():
                self._update_progress(60, "Performing data quality checks...")
                self._log_message("Running data quality checks...")
                quality_issues = self.processor._assess_data_quality(self.processor.data)
                
                if quality_issues:
                    # Show quality issues in a separate window
                    issue_count = sum(len(items) for items in quality_issues.values())
                    self._log_message(f"Found {issue_count} data quality issues", "WARNING")
                    self._show_quality_report(quality_issues)
                else:
                    self._log_message("No data quality issues found", "SUCCESS")
                    
            self._update_progress(100, "Data loaded successfully!")
            self.success = True
            
            # Close dialog after a short delay
            self.dialog.after(2000, self.dialog.destroy)
            
        except Exception as e:
            self._update_progress(0, f"Error: {str(e)}")
            self._log_message(f"Exception during data loading: {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
            self.load_btn.config(state="normal")
            
    def _show_quality_report(self, issues):
        """Show data quality issues in a separate window"""
        report_window = tk.Toplevel(self.dialog)
        report_window.title("Data Quality Report")
        report_window.geometry("600x500")
        
        # Make window modal
        report_window.transient(self.dialog)
        report_window.grab_set()
        
        # Add scrolled text widget
        text_widget = scrolledtext.ScrolledText(
            report_window,
            wrap=tk.WORD,
            font=("Consolas", 10),
            background="#F8F8F8"
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Define tags for styling
        text_widget.tag_configure("header", font=("Consolas", 12, "bold"))
        text_widget.tag_configure("category", font=("Consolas", 11, "bold"))
        text_widget.tag_configure("item", font=("Consolas", 10))
        text_widget.tag_configure("info", foreground="blue")
        text_widget.tag_configure("warning", foreground="#FF9800")
        text_widget.tag_configure("error", foreground="#F44336")
        
        # Add report content
        text_widget.insert(tk.END, "Data Quality Report\n\n", "header")
        
        # Calculate severity counts
        high_count = 0
        medium_count = 0
        low_count = 0
        
        for category, items in issues.items():
            # Determine severity based on category
            severity = "info"
            if "Missing" in category or "Error" in category:
                severity = "error"
                high_count += len(items)
            elif "Inconsistent" in category or "Invalid" in category:
                severity = "warning"
                medium_count += len(items)
            else:
                low_count += len(items)
                
            text_widget.insert(tk.END, f"{category}:\n", "category")
            for item in items:
                text_widget.insert(tk.END, f"  • {item}\n", ("item", severity))
            text_widget.insert(tk.END, "\n")
            
        # Add summary at the top
        total_issues = high_count + medium_count + low_count
        summary_text = f"Summary: Found {total_issues} issues\n"
        summary_text += f"  • {high_count} high severity issues\n" if high_count > 0 else ""
        summary_text += f"  • {medium_count} medium severity issues\n" if medium_count > 0 else ""
        summary_text += f"  • {low_count} low severity issues\n\n" if low_count > 0 else "\n"
        
        # Insert summary at the beginning after the header
        current_text = text_widget.get("1.0", tk.END)
        header_end = text_widget.search("\n\n", "1.0", tk.END) + "+2c"
        text_widget.insert(header_end, summary_text)
            
        text_widget.config(state="disabled")  # Make read-only
        
        # Add action buttons at the bottom
        button_frame = ttk.Frame(report_window)
        button_frame.pack(pady=(0, 10))
        
        # Save report button
        save_btn = ttk.Button(
            button_frame,
            text="Save Report",
            command=lambda: self._save_quality_report(issues, text_widget.get("1.0", tk.END))
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_btn = ttk.Button(
            button_frame,
            text="Close",
            command=report_window.destroy
        )
        close_btn.pack(side=tk.LEFT)
        
    def _save_quality_report(self, issues, report_text):
        """Save the quality report to a file"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Save Quality Report",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'w') as f:
                    f.write(report_text)
                messagebox.showinfo("Report Saved", f"Quality report saved to {file_path}")
                self._log_message(f"Saved quality report to {file_path}", "SUCCESS")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {str(e)}")
            self._log_message(f"Error saving quality report: {str(e)}", "ERROR")
        
    def show(self):
        """Show the dialog and return whether data was loaded successfully"""
        self.dialog.wait_window()
        return self.success 