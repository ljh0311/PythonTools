import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def create_scrollable_text_frame(parent, error_handler=None):
    """
    Create a simple text frame without scrollbars.
    Returns the frame and the text widget.
    If error_handler is provided, it will be called on error.
    """
    try:
        frame = ttk.Frame(parent)
        text_widget = tk.Text(
            frame,
            wrap=tk.NONE,
            font=("Consolas", 9),
            padx=16,
            pady=12,
            spacing1=4,
            spacing2=0,
            spacing3=4,
            bg="#f9f9f9",
            relief=tk.FLAT,
            selectbackground="#0078d4",
            selectforeground="white",
            height=20,  # Minimum height for testing
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        return frame, text_widget

    except Exception as e:
        # Show error dialog for any error in creating the text frame
        if error_handler is not None:
            error_handler(
                e,
                context={
                    "operation": "create_scrollable_text_frame",
                    "component": "ScrollablePanel"
                }
            )
        return None, None

def create_simple_scrollable_frame(parent, colors=None):
    """
    Create a simple scrollable frame for general content (not figures).
    
    Args:
        parent: Parent widget
        colors: Color scheme dictionary
        
    Returns:
        ttk.Frame: The scrollable frame
    """
    if colors is None:
        colors = {"card": "#ffffff"}
    
    # Create a simple frame that can be used for content
    frame = ttk.Frame(parent, style="Card.TFrame")
    frame.pack(fill=tk.BOTH, expand=True)
    
    return frame

def create_simple_scrollable_tab(figure, tab_name, parent):
    """
    Create a simple scrollable tab for embedding matplotlib figures.
    
    Args:
        figure: Matplotlib figure to display
        tab_name: Name of the tab
        parent: Parent widget
        
    Returns:
        ttk.Frame: The scrollable tab frame
    """
    try:
        # Create a frame for the tab
        tab_frame = ttk.Frame(parent)
        tab_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas for scrolling
        canvas = tk.Canvas(tab_frame, bg="white", highlightthickness=0)
        
        # Create scrollbars
        v_scrollbar = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(tab_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        
        # Configure canvas
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create a frame inside the canvas for the figure
        figure_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=figure_frame, anchor="nw")
        
        # Embed the matplotlib figure
        canvas_widget = FigureCanvasTkAgg(figure, figure_frame)
        canvas_widget.draw()
        canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure scroll region
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        figure_frame.bind("<Configure>", configure_scroll_region)
        
        # Add mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind("<MouseWheel>", on_mousewheel)
        
        return tab_frame
        
    except Exception as e:
        print(f"Error creating scrollable tab: {e}")
        # Fallback: create a simple frame with the figure
        tab_frame = ttk.Frame(parent)
        canvas_widget = FigureCanvasTkAgg(figure, tab_frame)
        canvas_widget.draw()
        canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return tab_frame
    
def create_scrollable_tab(figure, tab_name, root, right_panel=None, vis_notebook=None, colors=None, logger=None):
    """
    Create a scrollable tab that supports both vertical and horizontal scrolling,
    and fills the entire space of the right_panel.

    Args:
        figure: Matplotlib figure to display
        tab_name: Name of the tab
        root: Root window for screen size detection
        right_panel: The right panel widget to size against
        vis_notebook: The notebook widget to add tabs to
        colors: Color scheme dictionary
        logger: Logger instance for error handling

    Returns:
        ttk.Frame: The scrollable tab frame
    """
    # Responsive scaling based on screen size
    screen_width = root.winfo_screenwidth()
    if screen_width < 1366:
        scale_factor = 0.7
    elif screen_width < 1920:
        scale_factor = 0.85
    else:
        scale_factor = 1.0

    # Default colors if not provided
    if colors is None:
        colors = {"card": "#ffffff"}

    RENDERING_CONFIG = {
        "min_width": int(800 * scale_factor),
        "min_height": int(600 * scale_factor),
        "background_color": colors.get("card", "#ffffff"),
        "scroll_delay_ms": 100,
        "auto_resize_canvas": True,
        "enable_horizontal_scroll": True,
        "enable_vertical_scroll": True,
        "figure_dpi": None,
        "figure_scale": scale_factor,
        "scaling_finalized": False,  # Flag to prevent scaling changes after initial decision
        "ignore_scrollbar_events": False,  # Flag to ignore scrollbar-triggered resize events
    }

    # The tab frame should fill the right_panel
    if vis_notebook is None:
        # Create a temporary notebook if none provided
        vis_notebook = ttk.Notebook(root)
    
    tab = ttk.Frame(vis_notebook, style="Card.TFrame")
    tab.pack_propagate(False)
    
    # Get right panel dimensions for proper scaling
    if right_panel is not None:
        # Get the actual dimensions of the right panel
        right_panel.update_idletasks()  # Ensure dimensions are current
        
        panel_width = right_panel.winfo_width()
        panel_height = right_panel.winfo_height()
        
        # Get window dimensions for minimum size calculation
        window_width = root.winfo_width()
        window_height = root.winfo_height()
        
        # Calculate minimum frame size (80% of window size)
        min_frame_width = int(window_width * 0.8)
        min_frame_height = int(window_height * 0.8)
        
        # Use panel dimensions if available, otherwise use screen-based scaling
        if panel_width > 0 and panel_height > 0:
            # Check if frame is too small for dynamic scaling
            if panel_width < min_frame_width or panel_height < min_frame_height:
                # Disable dynamic scaling - use fixed minimum sizes
                RENDERING_CONFIG["auto_resize_canvas"] = False
                RENDERING_CONFIG["min_width"] = int(800 * scale_factor)
                RENDERING_CONFIG["min_height"] = int(600 * scale_factor)
                RENDERING_CONFIG["scaling_finalized"] = True  # Lock the decision
                print(f"SCROLLABLE PANEL: Frame too small ({panel_width}x{panel_height}), disabling dynamic scaling. Min required: {min_frame_width}x{min_frame_height}")
            else:
                # Frame is large enough for dynamic scaling
                # Account for padding and scrollbars
                available_width = max(panel_width - 40, RENDERING_CONFIG["min_width"])  # 20px padding on each side
                available_height = max(panel_height - 80, RENDERING_CONFIG["min_height"])  # Account for title bar and padding
                
                # Update rendering config with panel-based dimensions
                RENDERING_CONFIG["min_width"] = available_width
                RENDERING_CONFIG["min_height"] = available_height
                RENDERING_CONFIG["scaling_finalized"] = True  # Lock the decision
                print(f"SCROLLABLE PANEL: Frame size adequate ({panel_width}x{panel_height}), using dynamic scaling")
            
            # Make the tab fill the right_panel
            tab.configure(width=panel_width, height=panel_height)
        else:
            # Panel dimensions not available yet, use screen-based scaling
            print(f"Panel dimensions not available yet ({panel_width}x{panel_height}), using screen-based scaling")
            RENDERING_CONFIG["auto_resize_canvas"] = False
            RENDERING_CONFIG["min_width"] = int(800 * scale_factor)
            RENDERING_CONFIG["min_height"] = int(600 * scale_factor)
    
    tab.grid_propagate(False)

    # Create a frame to hold canvas and scrollbars with proper layout
    scroll_frame = ttk.Frame(tab)
    scroll_frame.pack(fill=tk.BOTH, expand=True)

    # Canvas fills the scroll frame
    canvas = tk.Canvas(
        scroll_frame, bg=RENDERING_CONFIG["background_color"], highlightthickness=0
    )

    # Configure scrollbars
    if RENDERING_CONFIG["enable_vertical_scroll"]:
        v_scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=v_scrollbar.set)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add event handlers to prevent resize on scrollbar interaction
        def on_v_scrollbar_click(event):
            RENDERING_CONFIG["ignore_scrollbar_events"] = True
            # Reset after a short delay
            root.after(100, lambda: RENDERING_CONFIG.update({"ignore_scrollbar_events": False}))
        
        v_scrollbar.bind("<Button-1>", on_v_scrollbar_click)
        
    if RENDERING_CONFIG["enable_horizontal_scroll"]:
        h_scrollbar = ttk.Scrollbar(scroll_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        canvas.configure(xscrollcommand=h_scrollbar.set)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add event handlers to prevent resize on scrollbar interaction
        def on_h_scrollbar_click(event):
            RENDERING_CONFIG["ignore_scrollbar_events"] = True
            # Reset after a short delay
            root.after(100, lambda: RENDERING_CONFIG.update({"ignore_scrollbar_events": False}))
        
        h_scrollbar.bind("<Button-1>", on_h_scrollbar_click)
    
    # Pack canvas last so it fills remaining space
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Set content frame size based on figure dimensions with responsive scaling
    fig_width, fig_height = figure.get_size_inches()
    dpi = figure.get_dpi()
    pixel_width = int(fig_width * dpi * RENDERING_CONFIG["figure_scale"])
    pixel_height = int(fig_height * dpi * RENDERING_CONFIG["figure_scale"])

    content_frame = ttk.Frame(canvas, style="Card.TFrame")
    content_frame.config(
        width=max(pixel_width, RENDERING_CONFIG["min_width"]),
        height=max(pixel_height, RENDERING_CONFIG["min_height"]),
    )

    canvas_window = canvas.create_window((0, 0), window=content_frame, anchor=tk.NW)

    try:
        # Apply figure scaling if configured
        if RENDERING_CONFIG["figure_scale"] != 1.0:
            figure.set_size_inches(
                figure.get_size_inches() * RENDERING_CONFIG["figure_scale"]
            )
        if RENDERING_CONFIG["figure_dpi"]:
            figure.set_dpi(RENDERING_CONFIG["figure_dpi"])

        fig_canvas = FigureCanvasTkAgg(figure, content_frame)
        fig_canvas.draw()
        fig_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    except Exception as e:
        if logger:
            logger.error(f"Error creating matplotlib canvas: {e}")
        ttk.Label(
            content_frame, text=f"Error displaying {tab_name}: {str(e)}"
        ).pack(pady=20)

    def _configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        # Only auto-resize if dynamic scaling is enabled
        if RENDERING_CONFIG["auto_resize_canvas"]:
            canvas.itemconfig(
                canvas_window,
                width=canvas.winfo_width(),
                height=canvas.winfo_height(),
            )

    def _on_canvas_configure(event):
        # Ignore scrollbar-triggered events if scaling is finalized
        if RENDERING_CONFIG["scaling_finalized"] and RENDERING_CONFIG["ignore_scrollbar_events"]:
            return
            
        # Respect the finalized scaling decision
        if RENDERING_CONFIG["auto_resize_canvas"]:
            # Always fill the right_panel (tab) area
            new_width = max(event.width, content_frame.winfo_reqwidth())
            new_height = max(event.height, content_frame.winfo_reqheight())
            canvas.itemconfig(canvas_window, width=new_width, height=new_height)
        else:
            # When dynamic scaling is disabled, maintain minimum size
            canvas.itemconfig(
                canvas_window,
                width=max(event.width, RENDERING_CONFIG["min_width"]),
                height=max(event.height, RENDERING_CONFIG["min_height"]),
            )

    content_frame.bind("<Configure>", _configure_scroll_region)
    canvas.bind("<Configure>", _on_canvas_configure)
    
    # Add mouse wheel event handling to prevent resize on scrolling
    def on_mousewheel(event):
        RENDERING_CONFIG["ignore_scrollbar_events"] = True
        # Reset after a short delay
        root.after(100, lambda: RENDERING_CONFIG.update({"ignore_scrollbar_events": False}))
    
    canvas.bind("<MouseWheel>", on_mousewheel)

    tab.after(
        RENDERING_CONFIG["scroll_delay_ms"],
        lambda: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    
    # Deferred scaling check - run after window is fully rendered
    # Only make the decision once, don't change it after initial setup
    def deferred_scaling_check():
        # If scaling decision is already finalized, don't change it
        if RENDERING_CONFIG["scaling_finalized"]:
            return
            
        if right_panel is not None:
            right_panel.update_idletasks()
            panel_width = right_panel.winfo_width()
            panel_height = right_panel.winfo_height()
            window_width = root.winfo_width()
            window_height = root.winfo_height()
            
            min_frame_width = int(window_width * 0.8)
            min_frame_height = int(window_height * 0.8)
            
            if panel_width > 0 and panel_height > 0:
                if panel_width < min_frame_width or panel_height < min_frame_height:
                    print(f"Deferred check: Frame too small ({panel_width}x{panel_height}), keeping fixed scaling")
                    # Ensure dynamic scaling stays disabled
                    RENDERING_CONFIG["auto_resize_canvas"] = False
                    RENDERING_CONFIG["scaling_finalized"] = True
                else:
                    print(f"Deferred check: Frame adequate ({panel_width}x{panel_height}), enabling dynamic scaling")
                    # Only enable if it wasn't already disabled
                    if RENDERING_CONFIG["auto_resize_canvas"]:
                        available_width = max(panel_width - 40, RENDERING_CONFIG["min_width"])
                        available_height = max(panel_height - 80, RENDERING_CONFIG["min_height"])
                        RENDERING_CONFIG["min_width"] = available_width
                        RENDERING_CONFIG["min_height"] = available_height
                        RENDERING_CONFIG["scaling_finalized"] = True
    
    # Schedule the deferred check
    root.after(200, deferred_scaling_check)
    
    return tab