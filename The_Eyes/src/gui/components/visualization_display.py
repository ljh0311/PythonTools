"""
Visualization Display Component for the Clinic Data Visualizer application.

This module provides the main visualization display area with matplotlib
integration, toolbar, and export functionality.

Extracted from main_window.py as part of Phase 3 component splitting.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import gc

from app.utils.logger import get_logger
from app.core.dependency_injection import injectable, inject
from app.visualization.export.image_exporter import ImageExporter


@injectable
class VisualizationDisplayComponent:
    """
    Visualization display component for the main application window.
    
    Provides matplotlib integration, navigation toolbar, and export
    functionality in a focused, reusable component.
    """
    
    def __init__(self, 
                 parent: tk.Widget,
                 image_exporter: ImageExporter,
                 on_export_requested: Optional[Callable] = None):
        """
        Initialize the visualization display component.
        
        Args:
            parent: Parent widget
            image_exporter: Image export service
            on_export_requested: Callback when export is requested
        """
        self.parent = parent
        self.image_exporter = image_exporter
        self.logger = get_logger(__name__)
        
        # Callbacks
        self.on_export_requested = on_export_requested
        
        # UI components
        self.viz_frame = None
        self.canvas = None
        self.toolbar = None
        self.loading_label = None
        
        # State
        self.current_figure = None
        self.is_loading = False
        
        # Create visualization display
        self._setup_visualization_display()
        
        self.logger.debug("VisualizationDisplayComponent initialized")
    
    def _setup_visualization_display(self):
        """Create and configure the visualization display."""
        # Main visualization frame
        self.viz_frame = ttk.LabelFrame(
            self.parent,
            text="📈 Visualization",
            padding=5
        )
        self.viz_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create initial empty figure
        self._create_empty_figure()
        
        # Create loading indicator
        self._create_loading_indicator()
    
    def _get_frame_size_inches(self) -> tuple:
        """Get the frame size in inches for matplotlib figure sizing."""
        # Get frame size in pixels
        width_px = max(self.viz_frame.winfo_width(), 400)  # Minimum 400px
        height_px = max(self.viz_frame.winfo_height(), 300)  # Minimum 300px
        
        # Convert to inches (assuming 100 DPI for display)
        dpi = 100
        width_inches = width_px / dpi
        height_inches = height_px / dpi
        
        # Apply aspect ratio constraints to prevent squashing
        min_aspect_ratio = 0.5  # Minimum width/height ratio
        max_aspect_ratio = 3.0  # Maximum width/height ratio
        
        current_aspect = width_inches / height_inches if height_inches > 0 else 1
        
        if current_aspect < min_aspect_ratio:
            # Too narrow - increase width
            width_inches = height_inches * min_aspect_ratio
        elif current_aspect > max_aspect_ratio:
            # Too wide - increase height
            height_inches = width_inches / max_aspect_ratio
        
        return (width_inches, height_inches)
    
    def _get_container_dimensions(self) -> tuple:
        """Get container dimensions in pixels for chart generators."""
        width_px = max(self.viz_frame.winfo_width(), 400)
        height_px = max(self.viz_frame.winfo_height(), 300)
        return (width_px, height_px)
    
    def _create_empty_figure(self):
        """Create an empty matplotlib figure with responsive sizing."""
        # Get frame size in inches
        figsize = self._get_frame_size_inches()
        
        # Create figure with responsive size
        fig = Figure(figsize=figsize, dpi=100)
        fig.patch.set_facecolor('#f8fafc')
        
        # Add empty subplot
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'Load data and select a visualization type to begin',
                horizontalalignment='center',
                verticalalignment='center',
                transform=ax.transAxes,
                fontsize=14,
                color='#64748b')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Apply tight_layout
        try:
            fig.tight_layout()
        except Exception:
            pass
        
        # Create canvas with proper packing
        self._create_canvas_and_toolbar(fig)
        
        self.current_figure = fig
        
        # Bind resize event to update figure size
        self.viz_frame.bind('<Configure>', self._on_resize)
    
    def _create_canvas_and_toolbar(self, fig: Figure):
        """Create canvas and toolbar for a given figure."""
        # Destroy existing canvas and toolbar
        self._destroy_canvas_and_toolbar()
        
        # Create new canvas
        self.canvas = FigureCanvasTkAgg(fig, self.viz_frame)
        self.canvas.draw()
        
        # Pack canvas with proper fill and expand
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Create toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.viz_frame)
        self.toolbar.update()
        
        # Add export button to toolbar
        self._add_export_button()
        
        self.logger.debug("Canvas and toolbar created successfully")
    
    def _destroy_canvas_and_toolbar(self):
        """Destroy existing canvas and toolbar to prevent memory leaks."""
        try:
            # Destroy toolbar first
            if self.toolbar:
                self.toolbar.destroy()
                self.toolbar = None
            
            # Destroy canvas
            if self.canvas:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None
                
        except Exception as e:
            self.logger.warning(f"Error destroying canvas/toolbar: {e}")
    
    def _create_loading_indicator(self):
        """Create loading indicator."""
        self.loading_label = ttk.Label(
            self.viz_frame,
            text="🔄 Generating visualization...",
            font=("Segoe UI", 12),
            foreground="#2563eb"
        )
        # Don't pack initially - will be shown when needed
    
    def _add_export_button(self):
        """Add export button to the toolbar."""
        if self.toolbar:
            # Add separator
            self.toolbar._Spacer()
            
            # Add export button
            export_button = tk.Button(
                self.toolbar,
                text="💾 Export",
                command=self._handle_export,
                relief=tk.RAISED,
                borderwidth=1,
                padx=5
            )
            export_button.pack(side=tk.LEFT, padx=2)
    
    def _handle_export(self):
        """Handle export button click."""
        if self.on_export_requested:
            try:
                self.on_export_requested()
            except Exception as e:
                self.logger.error(f"Error in export callback: {e}")
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def show_loading(self, show: bool = True, message: str = "Generating visualization..."):
        """
        Show or hide loading indicator.
        
        Args:
            show: Whether to show the loading indicator
            message: Loading message to display
        """
        self.is_loading = show
        
        if show:
            # Update message
            self.loading_label.config(text=f"🔄 {message}")
            
            # Show loading indicator
            if not self.loading_label.winfo_viewable():
                self.loading_label.pack(pady=20)
            
            # Hide canvas temporarily
            if self.canvas and self.canvas.get_tk_widget().winfo_viewable():
                self.canvas.get_tk_widget().pack_forget()
                
        else:
            # Hide loading indicator
            if self.loading_label.winfo_viewable():
                self.loading_label.pack_forget()
            
            # Show canvas
            if self.canvas and not self.canvas.get_tk_widget().winfo_viewable():
                self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def update_figure_display(self, fig: Optional[Figure] = None):
        """
        Update the displayed figure with proper sizing and layout.
        
        Args:
            fig: New figure to display, or None to clear
        """
        try:
            # Hide loading indicator
            self.show_loading(False)
            
            if fig is None:
                # Create empty figure
                self._create_empty_figure()
                return
            
            # Close previous figure to prevent memory leaks
            if self.current_figure:
                # Check if current_figure is a dictionary (tabbed visualization)
                if isinstance(self.current_figure, dict):
                    # Close all figures in the dictionary
                    for fig in self.current_figure.values():
                        if fig is not None:
                            plt.close(fig)
                else:
                    # Close single figure
                    plt.close(self.current_figure)
                self.current_figure = None
                gc.collect()
            
            # Get container dimensions for responsive sizing
            container_width, container_height = self._get_container_dimensions()
            
            # Set figure size based on current frame size with aspect ratio constraints
            figsize = self._get_frame_size_inches()
            fig.set_size_inches(figsize, forward=True)
            
            # Apply responsive layout with container-aware adjustments
            self._apply_responsive_layout_with_container(fig, container_width, container_height)
            
            # Create new canvas and toolbar
            self._create_canvas_and_toolbar(fig)
            
            # Store current figure
            self.current_figure = fig
            
            # Bind resize event
            self.viz_frame.bind('<Configure>', self._on_resize)
            
            self.logger.debug("Figure display updated successfully")
            
        except Exception as e:
            self.logger.error(f"Error updating figure display: {e}")
            messagebox.showerror("Error", f"Failed to display visualization: {str(e)}")
    
    def _apply_responsive_layout_with_container(self, fig: Figure, container_width: int, container_height: int):
        """Apply responsive layout with container-aware adjustments."""
        try:
            # Apply tight_layout with container-aware padding
            fig.tight_layout(pad=1.5, h_pad=1.0, w_pad=1.0)
            
            # Adjust subplot parameters based on container size
            if container_width < 600:
                # Small container - increase margins
                fig.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.15)
            elif container_width < 1000:
                # Medium container - standard margins
                fig.subplots_adjust(left=0.12, right=0.95, top=0.9, bottom=0.12)
            else:
                # Large container - tighter margins
                fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.1)
            
            # Ensure text elements are readable
            self._adjust_text_elements_for_container(fig, container_width, container_height)
            
        except Exception as e:
            self.logger.warning(f"Error applying responsive layout: {e}")
            # Fallback to basic tight_layout
            try:
                fig.tight_layout()
            except Exception:
                pass
    
    def _adjust_text_elements_for_container(self, fig: Figure, container_width: int, container_height: int):
        """Adjust text elements (titles, labels, etc.) for container size."""
        try:
            # Calculate appropriate font sizes based on container size
            base_font_size = max(8, min(16, container_width // 80))
            title_font_size = max(10, min(20, container_width // 60))
            
            for ax in fig.get_axes():
                # Adjust title font size
                if ax.get_title():
                    ax.set_title(ax.get_title(), fontsize=title_font_size, pad=10)
                
                # Adjust axis label font sizes
                if ax.get_xlabel():
                    ax.set_xlabel(ax.get_xlabel(), fontsize=base_font_size)
                if ax.get_ylabel():
                    ax.set_ylabel(ax.get_ylabel(), fontsize=base_font_size)
                
                # Adjust tick label font sizes
                ax.tick_params(axis='both', labelsize=max(6, base_font_size - 2))
                
                # Adjust legend font size if present
                if ax.get_legend():
                    ax.get_legend().set_fontsize(max(6, base_font_size - 2))
                    
        except Exception as e:
            self.logger.warning(f"Error adjusting text elements: {e}")
    
    def clear_display(self):
        """Clear the visualization display."""
        self.update_figure_display(None)
    
    def export_current_visualization(self, file_path: str, format_type: str = "png"):
        """
        Export the current visualization.
        
        Args:
            file_path: Path to save the file
            format_type: Export format (png, pdf, svg, etc.)
        """
        try:
            if not self.current_figure:
                raise ValueError("No visualization to export")
            
            # Use image exporter
            success, message = self.image_exporter.export_figure(
                self.current_figure,
                file_path,
                format_type
            )
            
            if success:
                self.logger.info(f"Visualization exported: {file_path}")
                messagebox.showinfo("Export Successful", f"Visualization exported to:\n{file_path}")
            else:
                self.logger.error(f"Export failed: {message}")
                messagebox.showerror("Export Failed", message)
                
        except Exception as e:
            self.logger.error(f"Error exporting visualization: {e}")
            messagebox.showerror("Error", f"Failed to export visualization: {str(e)}")
    
    def get_current_figure(self) -> Optional[Figure]:
        """
        Get the current figure.
        
        Returns:
            Current matplotlib figure or None
        """
        return self.current_figure
    
    def has_visualization(self) -> bool:
        """
        Check if a visualization is currently displayed.
        
        Returns:
            True if a visualization is displayed, False otherwise
        """
        return self.current_figure is not None and not self.is_loading
    
    def get_viz_frame(self) -> ttk.LabelFrame:
        """
        Get the visualization frame widget.
        
        Returns:
            The visualization frame widget
        """
        return self.viz_frame
    
    def refresh_display(self):
        """Refresh the current display."""
        if self.canvas:
            self.canvas.draw()
    
    def save_figure_to_buffer(self, format_type: str = "png"):
        """
        Save the current figure to a buffer.
        
        Args:
            format_type: Format to save in
            
        Returns:
            Buffer containing the figure data
        """
        if not self.current_figure:
            return None
        
        try:
            import io
            buffer = io.BytesIO()
            self.current_figure.savefig(buffer, format=format_type, bbox_inches='tight', dpi=300)
            buffer.seek(0)
            return buffer
        except Exception as e:
            self.logger.error(f"Error saving figure to buffer: {e}")
            return None
    
    def cleanup(self):
        """Clean up resources."""
        try:
            # Close current figure
            if self.current_figure:
                # Check if current_figure is a dictionary (tabbed visualization)
                if isinstance(self.current_figure, dict):
                    # Close all figures in the dictionary
                    for fig in self.current_figure.values():
                        if fig is not None:
                            plt.close(fig)
                else:
                    # Close single figure
                    plt.close(self.current_figure)
                self.current_figure = None
            
            # Destroy canvas and toolbar
            self._destroy_canvas_and_toolbar()
            
            # Force garbage collection
            gc.collect()
            
            self.logger.debug("VisualizationDisplayComponent cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def _on_resize(self, event):
        """Handle resize events to update figure size and redraw."""
        if not self.current_figure:
            return
            
        try:
            # Get new frame size in inches with aspect ratio constraints
            figsize = self._get_frame_size_inches()
            
            # Update figure size
            self.current_figure.set_size_inches(figsize, forward=True)
            
            # Get container dimensions for responsive adjustments
            container_width, container_height = self._get_container_dimensions()
            
            # Apply responsive layout with container-aware adjustments
            self._apply_responsive_layout_with_container(self.current_figure, container_width, container_height)
            
            # Redraw the canvas
            if self.canvas:
                self.canvas.draw()
                
            self.logger.debug(f"Figure resized to {figsize}")
            
        except Exception as e:
            self.logger.error(f"Error handling resize: {e}") 
    
    def get_container_dimensions(self) -> tuple:
        """
        Get the current container dimensions for chart generators.
        
        Returns:
            Tuple of (width_px, height_px)
        """
        return self._get_container_dimensions() 