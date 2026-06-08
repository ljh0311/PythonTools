"""
Enhanced Export Components for the Clinic Data Visualizer.

This module provides advanced export functionality including multiple formats,
batch export, templates, and performance optimization.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import logging
from pathlib import Path
import zipfile

# Import for different export formats
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.backends.backend_svg as svg_backend

logger = logging.getLogger(__name__)


class ExportTemplate:
    """
    Represents an export template with predefined settings.
    """
    
    def __init__(self, name: str, settings: Dict[str, Any]):
        """
        Initialize an export template.
        
        Parameters:
        -----------
        name : str
            Template name
        settings : Dict[str, Any]
            Template settings
        """
        self.name = name
        self.settings = settings.copy()
        self.created = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'name': self.name,
            'settings': self.settings,
            'created': self.created.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportTemplate':
        """Create template from dictionary."""
        template = cls(data['name'], data['settings'])
        if 'created' in data:
            template.created = datetime.fromisoformat(data['created'])
        return template


class BatchExportJob:
    """
    Represents a batch export job with multiple visualizations.
    """
    
    def __init__(self, name: str, visualizations: List[str], settings: Dict[str, Any]):
        """
        Initialize a batch export job.
        
        Parameters:
        -----------
        name : str
            Job name
        visualizations : List[str]
            List of visualization types to export
        settings : Dict[str, Any]
            Export settings
        """
        self.name = name
        self.visualizations = visualizations.copy()
        self.settings = settings.copy()
        self.created = datetime.now()
        self.status = "pending"
        self.progress = 0
        self.results = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            'name': self.name,
            'visualizations': self.visualizations,
            'settings': self.settings,
            'created': self.created.isoformat(),
            'status': self.status,
            'progress': self.progress
        }


class EnhancedExportManager:
    """
    Advanced export manager with multiple formats, batch export, and templates.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize the enhanced export manager.
        
        Parameters:
        -----------
        parent : tk.Widget
            Parent widget
        **kwargs : dict
            Additional configuration options
        """
        self.parent = parent
        
        # Configuration
        self.visualization_factory = kwargs.get('visualization_factory', None)
        self.data_processor = kwargs.get('data_processor', None)
        self.templates_file = kwargs.get('templates_file', 'export_templates.json')
        
        # State
        self.templates = {}
        self.current_job = None
        self.export_thread = None
        
        # Supported formats
        self.formats = {
            'PNG': {'extension': '.png', 'description': 'Portable Network Graphics'},
            'PDF': {'extension': '.pdf', 'description': 'Portable Document Format'},
            'SVG': {'extension': '.svg', 'description': 'Scalable Vector Graphics'},
            'JPEG': {'extension': '.jpg', 'description': 'JPEG Image'},
            'EPS': {'extension': '.eps', 'description': 'Encapsulated PostScript'},
            'TIFF': {'extension': '.tiff', 'description': 'Tagged Image File Format'}
        }
        
        # Create the UI
        self._create_widgets()
        self._load_templates()
        
        logger.info("EnhancedExportManager initialized")
    
    def _create_widgets(self):
        """Create the export manager widgets."""
        # Main notebook for different export modes
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Single export tab
        self._create_single_export_tab()
        
        # Batch export tab
        self._create_batch_export_tab()
        
        # Templates tab
        self._create_templates_tab()
    
    def _create_single_export_tab(self):
        """Create the single export tab."""
        self.single_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_frame, text="Single Export")
        
        # Format selection
        format_frame = ttk.LabelFrame(self.single_frame, text="Export Format")
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.format_var = tk.StringVar(value="PNG")
        for i, (fmt, info) in enumerate(self.formats.items()):
            row = i // 3
            col = i % 3
            
            rb = ttk.Radiobutton(
                format_frame,
                text=f"{fmt} ({info['extension']})",
                variable=self.format_var,
                value=fmt
            )
            rb.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
        
        # Quality settings
        quality_frame = ttk.LabelFrame(self.single_frame, text="Quality Settings")
        quality_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # DPI setting
        dpi_frame = ttk.Frame(quality_frame)
        dpi_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(dpi_frame, text="DPI:").pack(side=tk.LEFT)
        self.dpi_var = tk.StringVar(value="300")
        dpi_combo = ttk.Combobox(
            dpi_frame,
            textvariable=self.dpi_var,
            values=["72", "150", "300", "600", "1200"],
            width=10,
            state="readonly"
        )
        dpi_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Size settings
        size_frame = ttk.Frame(quality_frame)
        size_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(size_frame, text="Size:").pack(side=tk.LEFT)
        
        self.width_var = tk.StringVar(value="1920")
        ttk.Label(size_frame, text="Width:").pack(side=tk.LEFT, padx=(10, 0))
        width_entry = ttk.Entry(size_frame, textvariable=self.width_var, width=8)
        width_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        self.height_var = tk.StringVar(value="1080")
        ttk.Label(size_frame, text="Height:").pack(side=tk.LEFT, padx=(10, 0))
        height_entry = ttk.Entry(size_frame, textvariable=self.height_var, width=8)
        height_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Additional options
        options_frame = ttk.LabelFrame(self.single_frame, text="Options")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.transparent_var = tk.BooleanVar()
        transparent_cb = ttk.Checkbutton(
            options_frame,
            text="Transparent background",
            variable=self.transparent_var
        )
        transparent_cb.pack(anchor=tk.W, padx=5, pady=2)
        
        self.optimize_var = tk.BooleanVar(value=True)
        optimize_cb = ttk.Checkbutton(
            options_frame,
            text="Optimize for file size",
            variable=self.optimize_var
        )
        optimize_cb.pack(anchor=tk.W, padx=5, pady=2)
        
        # Export button
        export_button = ttk.Button(
            self.single_frame,
            text="Export Current Visualization",
            command=self._export_single,
            style="Accent.TButton"
        )
        export_button.pack(pady=10)
    
    def _create_batch_export_tab(self):
        """Create the batch export tab."""
        self.batch_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_frame, text="Batch Export")
        
        # Visualization selection
        viz_frame = ttk.LabelFrame(self.batch_frame, text="Select Visualizations")
        viz_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollable frame for visualization checkboxes
        canvas = tk.Canvas(viz_frame)
        scrollbar = ttk.Scrollbar(viz_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Visualization checkboxes (will be populated dynamically)
        self.viz_vars = {}
        self.viz_checkboxes_frame = scrollable_frame
        
        # Batch settings
        batch_settings_frame = ttk.LabelFrame(self.batch_frame, text="Batch Settings")
        batch_settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Output directory
        dir_frame = ttk.Frame(batch_settings_frame)
        dir_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(dir_frame, text="Output Directory:").pack(side=tk.LEFT)
        self.output_dir_var = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        dir_entry = ttk.Entry(dir_frame, textvariable=self.output_dir_var)
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        browse_button = ttk.Button(
            dir_frame,
            text="Browse",
            command=self._browse_output_dir,
            width=8
        )
        browse_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Batch format
        batch_format_frame = ttk.Frame(batch_settings_frame)
        batch_format_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(batch_format_frame, text="Format:").pack(side=tk.LEFT)
        self.batch_format_var = tk.StringVar(value="PNG")
        batch_format_combo = ttk.Combobox(
            batch_format_frame,
            textvariable=self.batch_format_var,
            values=list(self.formats.keys()),
            state="readonly",
            width=10
        )
        batch_format_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Create archive option
        self.create_archive_var = tk.BooleanVar(value=True)
        archive_cb = ttk.Checkbutton(
            batch_settings_frame,
            text="Create ZIP archive",
            variable=self.create_archive_var
        )
        archive_cb.pack(anchor=tk.W, padx=5, pady=2)
        
        # Progress bar
        self.progress_frame = ttk.Frame(self.batch_frame)
        self.progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=2)
        
        self.progress_label = ttk.Label(self.progress_frame, text="Ready")
        self.progress_label.pack(anchor=tk.W)
        
        # Batch export buttons
        batch_buttons_frame = ttk.Frame(self.batch_frame)
        batch_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.batch_export_button = ttk.Button(
            batch_buttons_frame,
            text="Start Batch Export",
            command=self._start_batch_export,
            style="Accent.TButton"
        )
        self.batch_export_button.pack(side=tk.LEFT)
        
        self.cancel_button = ttk.Button(
            batch_buttons_frame,
            text="Cancel",
            command=self._cancel_batch_export,
            state="disabled"
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(5, 0))
    
    def _create_templates_tab(self):
        """Create the templates tab."""
        self.templates_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.templates_frame, text="Templates")
        
        # Template list
        list_frame = ttk.LabelFrame(self.templates_frame, text="Export Templates")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Template listbox
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.template_listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE)
        self.template_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        template_scrollbar = ttk.Scrollbar(
            listbox_frame,
            orient=tk.VERTICAL,
            command=self.template_listbox.yview
        )
        template_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.template_listbox.config(yscrollcommand=template_scrollbar.set)
        
        # Template buttons
        template_buttons_frame = ttk.Frame(self.templates_frame)
        template_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        save_template_button = ttk.Button(
            template_buttons_frame,
            text="Save Current as Template",
            command=self._save_template
        )
        save_template_button.pack(side=tk.LEFT)
        
        load_template_button = ttk.Button(
            template_buttons_frame,
            text="Load Template",
            command=self._load_template
        )
        load_template_button.pack(side=tk.LEFT, padx=(5, 0))
        
        delete_template_button = ttk.Button(
            template_buttons_frame,
            text="Delete Template",
            command=self._delete_template
        )
        delete_template_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Template details
        details_frame = ttk.LabelFrame(self.templates_frame, text="Template Details")
        details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.template_details_text = tk.Text(
            details_frame,
            height=6,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.template_details_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Bind template selection
        self.template_listbox.bind('<<ListboxSelect>>', self._on_template_select)
    
    def populate_visualizations(self, available_visualizations: Dict[str, List[str]]):
        """
        Populate the visualization checkboxes for batch export.
        
        Parameters:
        -----------
        available_visualizations : Dict[str, List[str]]
            Dictionary of visualization categories and their types
        """
        # Clear existing checkboxes
        for widget in self.viz_checkboxes_frame.winfo_children():
            widget.destroy()
        
        self.viz_vars = {}
        
        # Create checkboxes for each visualization
        row = 0
        for category, viz_types in available_visualizations.items():
            # Category header
            category_label = ttk.Label(
                self.viz_checkboxes_frame,
                text=category,
                font=('TkDefaultFont', 10, 'bold')
            )
            category_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
            row += 1
            
            # Visualization checkboxes
            for viz_type in viz_types:
                var = tk.BooleanVar()
                self.viz_vars[viz_type] = var
                
                cb = ttk.Checkbutton(
                    self.viz_checkboxes_frame,
                    text=viz_type.replace('_', ' ').title(),
                    variable=var
                )
                cb.grid(row=row, column=0, sticky=tk.W, padx=(20, 0), pady=1)
                row += 1
        
        logger.info(f"Populated {len(self.viz_vars)} visualization options for batch export")
    
    def _export_single(self):
        """Export a single visualization."""
        # Get current settings
        settings = self._get_current_settings()
        
        # Get file path
        format_info = self.formats[settings['format']]
        file_path = filedialog.asksaveasfilename(
            title="Export Visualization",
            defaultextension=format_info['extension'],
            filetypes=[(settings['format'], f"*{format_info['extension']}")]
        )
        
        if not file_path:
            return
        
        try:
            # Get current figure (this would need to be passed from the main application)
            current_figure = plt.gcf()
            
            if current_figure is None:
                messagebox.showerror("Error", "No visualization to export")
                return
            
            # Apply settings and export
            self._export_figure(current_figure, file_path, settings)
            
            messagebox.showinfo("Success", f"Visualization exported to:\n{file_path}")
            logger.info(f"Single export completed: {file_path}")
        
        except Exception as e:
            logger.error(f"Error during single export: {e}")
            messagebox.showerror("Error", f"Export failed: {str(e)}")
    
    def _start_batch_export(self):
        """Start batch export process."""
        # Get selected visualizations
        selected_viz = [
            viz_type for viz_type, var in self.viz_vars.items()
            if var.get()
        ]
        
        if not selected_viz:
            messagebox.showwarning("Warning", "Please select at least one visualization to export")
            return
        
        # Validate output directory
        output_dir = self.output_dir_var.get()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create output directory: {e}")
                return
        
        # Create batch job
        settings = self._get_current_settings()
        settings['format'] = self.batch_format_var.get()
        settings['output_dir'] = output_dir
        settings['create_archive'] = self.create_archive_var.get()
        
        self.current_job = BatchExportJob(
            name=f"Batch Export {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            visualizations=selected_viz,
            settings=settings
        )
        
        # Update UI
        self.batch_export_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.progress_var.set(0)
        self.progress_label.config(text="Starting batch export...")
        
        # Start export thread
        self.export_thread = threading.Thread(target=self._run_batch_export)
        self.export_thread.daemon = True
        self.export_thread.start()
        
        logger.info(f"Started batch export: {len(selected_viz)} visualizations")
    
    def _run_batch_export(self):
        """Run the batch export process in a separate thread."""
        try:
            job = self.current_job
            total_viz = len(job.visualizations)
            exported_files = []
            
            for i, viz_type in enumerate(job.visualizations):
                if job.status == "cancelled":
                    break
                
                # Update progress
                progress = (i / total_viz) * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"Exporting {viz_type}... ({i+1}/{total_viz})")
                
                try:
                    # Generate visualization
                    if self.visualization_factory and self.data_processor:
                        data = self.data_processor.get_data()
                        figure = self.visualization_factory.create_visualization(viz_type, data)
                        
                        if figure:
                            # Create filename
                            format_ext = self.formats[job.settings['format']]['extension']
                            filename = f"{viz_type}{format_ext}"
                            file_path = os.path.join(job.settings['output_dir'], filename)
                            
                            # Export figure
                            self._export_figure(figure, file_path, job.settings)
                            exported_files.append(file_path)
                            
                            # Close figure to free memory
                            plt.close(figure)
                            
                            job.results.append({
                                'visualization': viz_type,
                                'file_path': file_path,
                                'status': 'success'
                            })
                        else:
                            job.results.append({
                                'visualization': viz_type,
                                'status': 'failed',
                                'error': 'Failed to generate visualization'
                            })
                    
                except Exception as e:
                    logger.error(f"Error exporting {viz_type}: {e}")
                    job.results.append({
                        'visualization': viz_type,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Create archive if requested
            if job.settings.get('create_archive', False) and exported_files:
                archive_path = os.path.join(
                    job.settings['output_dir'],
                    f"{job.name}.zip"
                )
                
                self.progress_label.config(text="Creating archive...")
                
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in exported_files:
                        zipf.write(file_path, os.path.basename(file_path))
                
                job.results.append({
                    'type': 'archive',
                    'file_path': archive_path,
                    'status': 'success'
                })
            
            # Complete
            if job.status != "cancelled":
                job.status = "completed"
                self.progress_var.set(100)
                self.progress_label.config(text=f"Completed: {len(exported_files)} files exported")
                
                # Show completion message
                self.parent.after(0, self._show_batch_completion)
            
        except Exception as e:
            logger.error(f"Batch export error: {e}")
            job.status = "failed"
            self.parent.after(0, lambda: messagebox.showerror("Error", f"Batch export failed: {e}"))
        
        finally:
            # Reset UI
            self.parent.after(0, self._reset_batch_ui)
    
    def _cancel_batch_export(self):
        """Cancel the current batch export."""
        if self.current_job:
            self.current_job.status = "cancelled"
            self.progress_label.config(text="Cancelling...")
            logger.info("Batch export cancelled by user")
    
    def _reset_batch_ui(self):
        """Reset the batch export UI."""
        self.batch_export_button.config(state="normal")
        self.cancel_button.config(state="disabled")
    
    def _show_batch_completion(self):
        """Show batch export completion dialog."""
        if not self.current_job:
            return
        
        successful = len([r for r in self.current_job.results if r.get('status') == 'success'])
        failed = len([r for r in self.current_job.results if r.get('status') == 'failed'])
        
        message = f"Batch export completed!\n\n"
        message += f"Successful: {successful}\n"
        message += f"Failed: {failed}\n"
        message += f"Output directory: {self.current_job.settings['output_dir']}"
        
        messagebox.showinfo("Batch Export Complete", message)
    
    def _export_figure(self, figure, file_path: str, settings: Dict[str, Any]):
        """
        Export a figure with the specified settings.
        
        Parameters:
        -----------
        figure : matplotlib.figure.Figure
            Figure to export
        file_path : str
            Output file path
        settings : Dict[str, Any]
            Export settings
        """
        # Apply settings
        dpi = int(settings.get('dpi', 300))
        transparent = settings.get('transparent', False)
        optimize = settings.get('optimize', True)
        
        # Set figure size if specified
        if 'width' in settings and 'height' in settings:
            width_inches = int(settings['width']) / dpi
            height_inches = int(settings['height']) / dpi
            figure.set_size_inches(width_inches, height_inches)
        
        # Export based on format
        format_name = settings.get('format', 'PNG').lower()
        
        if format_name == 'pdf':
            with PdfPages(file_path) as pdf:
                pdf.savefig(
                    figure,
                    dpi=dpi,
                    transparent=transparent,
                    bbox_inches='tight' if optimize else None
                )
        else:
            figure.savefig(
                file_path,
                format=format_name,
                dpi=dpi,
                transparent=transparent,
                bbox_inches='tight' if optimize else None,
                optimize=optimize if format_name in ['png', 'jpg', 'jpeg'] else False
            )
        
        logger.info(f"Exported figure to {file_path} (format: {format_name}, dpi: {dpi})")
    
    def _get_current_settings(self) -> Dict[str, Any]:
        """Get current export settings."""
        return {
            'format': self.format_var.get(),
            'dpi': self.dpi_var.get(),
            'width': self.width_var.get(),
            'height': self.height_var.get(),
            'transparent': self.transparent_var.get(),
            'optimize': self.optimize_var.get()
        }
    
    def _browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir_var.get()
        )
        
        if directory:
            self.output_dir_var.set(directory)
    
    def _load_templates(self):
        """Load export templates from file."""
        try:
            if os.path.exists(self.templates_file):
                with open(self.templates_file, 'r') as f:
                    data = json.load(f)
                
                self.templates = {}
                for name, template_data in data.items():
                    self.templates[name] = ExportTemplate.from_dict(template_data)
                
                self._update_template_list()
                logger.info(f"Loaded {len(self.templates)} export templates")
        
        except Exception as e:
            logger.error(f"Error loading export templates: {e}")
            self.templates = {}
    
    def _save_templates(self):
        """Save export templates to file."""
        try:
            data = {}
            for name, template in self.templates.items():
                data[name] = template.to_dict()
            
            with open(self.templates_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.templates)} export templates")
        
        except Exception as e:
            logger.error(f"Error saving export templates: {e}")
    
    def _update_template_list(self):
        """Update the template listbox."""
        self.template_listbox.delete(0, tk.END)
        
        for name in sorted(self.templates.keys()):
            self.template_listbox.insert(tk.END, name)
    
    def _save_template(self):
        """Save current settings as a template."""
        name = tk.simpledialog.askstring(
            "Save Template",
            "Enter a name for this export template:",
            parent=self.parent
        )
        
        if name:
            settings = self._get_current_settings()
            template = ExportTemplate(name, settings)
            self.templates[name] = template
            
            self._update_template_list()
            self._save_templates()
            
            messagebox.showinfo("Success", f"Template '{name}' saved successfully")
            logger.info(f"Saved export template: {name}")
    
    def _load_template(self):
        """Load the selected template."""
        selection = self.template_listbox.curselection()
        
        if selection:
            name = self.template_listbox.get(selection[0])
            template = self.templates[name]
            
            # Apply template settings
            settings = template.settings
            
            self.format_var.set(settings.get('format', 'PNG'))
            self.dpi_var.set(settings.get('dpi', '300'))
            self.width_var.set(settings.get('width', '1920'))
            self.height_var.set(settings.get('height', '1080'))
            self.transparent_var.set(settings.get('transparent', False))
            self.optimize_var.set(settings.get('optimize', True))
            
            messagebox.showinfo("Success", f"Template '{name}' loaded successfully")
            logger.info(f"Loaded export template: {name}")
        else:
            messagebox.showwarning("Warning", "Please select a template to load")
    
    def _delete_template(self):
        """Delete the selected template."""
        selection = self.template_listbox.curselection()
        
        if selection:
            name = self.template_listbox.get(selection[0])
            
            result = messagebox.askyesno(
                "Delete Template",
                f"Are you sure you want to delete the template '{name}'?"
            )
            
            if result:
                del self.templates[name]
                self._update_template_list()
                self._save_templates()
                
                # Clear details
                self.template_details_text.config(state=tk.NORMAL)
                self.template_details_text.delete(1.0, tk.END)
                self.template_details_text.config(state=tk.DISABLED)
                
                messagebox.showinfo("Success", f"Template '{name}' deleted successfully")
                logger.info(f"Deleted export template: {name}")
        else:
            messagebox.showwarning("Warning", "Please select a template to delete")
    
    def _on_template_select(self, event):
        """Handle template selection."""
        selection = self.template_listbox.curselection()
        
        if selection:
            name = self.template_listbox.get(selection[0])
            template = self.templates[name]
            
            # Show template details
            details = f"Template: {name}\n"
            details += f"Created: {template.created.strftime('%Y-%m-%d %H:%M')}\n\n"
            details += "Settings:\n"
            
            for key, value in template.settings.items():
                details += f"  {key}: {value}\n"
            
            self.template_details_text.config(state=tk.NORMAL)
            self.template_details_text.delete(1.0, tk.END)
            self.template_details_text.insert(1.0, details)
            self.template_details_text.config(state=tk.DISABLED) 