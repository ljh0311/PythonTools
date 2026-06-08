"""
Virtual Scrolling Components for the Clinic Data Visualizer.

This module provides virtual scrolling widgets that can efficiently handle
large datasets by only rendering visible items in the viewport.
"""

import tkinter as tk
from tkinter import ttk
import threading
from typing import List, Callable, Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


class VirtualScrollingListbox:
    """
    A virtual scrolling listbox that can efficiently handle large datasets.
    
    Only renders items currently visible in the viewport, providing smooth
    performance even with 100k+ items.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize the virtual scrolling listbox.
        
        Parameters:
        -----------
        parent : tk.Widget
            Parent widget
        **kwargs : dict
            Additional configuration options
        """
        self.parent = parent
        
        # Configuration
        self.item_height = kwargs.get('item_height', 20)
        self.visible_items = kwargs.get('visible_items', 20)
        self.search_enabled = kwargs.get('search_enabled', True)
        self.selection_callback = kwargs.get('selection_callback', None)
        
        # Data management
        self._all_items = []
        self._filtered_items = []
        self._visible_start = 0
        self._visible_end = 0
        self._selected_index = -1
        self._search_term = ""
        
        # Threading for search
        self._search_lock = threading.Lock()
        self._search_thread = None
        
        # Create the UI
        self._create_widgets()
        self._setup_bindings()
        
        logger.info("VirtualScrollingListbox initialized")
    
    def _create_widgets(self):
        """Create the virtual scrolling listbox widgets."""
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search frame (if enabled)
        if self.search_enabled:
            self.search_frame = ttk.Frame(self.main_frame)
            self.search_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(self.search_frame, text="Search:").pack(side=tk.LEFT)
            
            self.search_var = tk.StringVar()
            self.search_entry = ttk.Entry(
                self.search_frame, 
                textvariable=self.search_var,
                width=30
            )
            self.search_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
            
            # Clear button
            self.clear_button = ttk.Button(
                self.search_frame,
                text="Clear",
                command=self._clear_search,
                width=8
            )
            self.clear_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Listbox frame
        self.listbox_frame = ttk.Frame(self.main_frame)
        self.listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        # Create canvas for virtual scrolling
        self.canvas = tk.Canvas(
            self.listbox_frame,
            highlightthickness=0,
            height=self.visible_items * self.item_height
        )
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(
            self.listbox_frame,
            orient=tk.VERTICAL,
            command=self._on_scroll
        )
        
        # Pack canvas and scrollbar
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Item display frame (inside canvas)
        self.items_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            0, 0, anchor=tk.NW, window=self.items_frame
        )
        
        # Status label
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="No items loaded",
            font=('TkDefaultFont', 8)
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Item labels (for visible items)
        self.item_labels = []
        for i in range(self.visible_items):
            label = tk.Label(
                self.items_frame,
                text="",
                anchor=tk.W,
                relief=tk.FLAT,
                height=1,
                cursor="hand2"
            )
            label.pack(fill=tk.X, pady=1)
            self.item_labels.append(label)
    
    def _setup_bindings(self):
        """Set up event bindings."""
        # Search functionality
        if self.search_enabled:
            self.search_var.trace('w', self._on_search_changed)
            self.search_entry.bind('<Return>', self._on_search_enter)
        
        # Canvas scrolling
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        
        # Item selection
        for i, label in enumerate(self.item_labels):
            label.bind('<Button-1>', lambda e, idx=i: self._on_item_click(idx))
            label.bind('<Double-Button-1>', lambda e, idx=i: self._on_item_double_click(idx))
        
        # Keyboard navigation
        self.canvas.bind('<Key>', self._on_key_press)
        self.canvas.focus_set()
    
    def set_items(self, items: List[Any]):
        """
        Set the items to display in the listbox.
        
        Parameters:
        -----------
        items : List[Any]
            List of items to display
        """
        self._all_items = items.copy() if items else []
        self._apply_filter()
        self._update_display()
        
        logger.info(f"VirtualScrollingListbox loaded {len(self._all_items)} items")
    
    def get_selected_item(self) -> Optional[Any]:
        """
        Get the currently selected item.
        
        Returns:
        --------
        Any or None
            The selected item, or None if no selection
        """
        if 0 <= self._selected_index < len(self._filtered_items):
            return self._filtered_items[self._selected_index]
        return None
    
    def get_selected_index(self) -> int:
        """
        Get the index of the currently selected item.
        
        Returns:
        --------
        int
            The selected index, or -1 if no selection
        """
        return self._selected_index
    
    def clear_selection(self):
        """Clear the current selection."""
        self._selected_index = -1
        self._update_display()
    
    def _apply_filter(self):
        """Apply the current search filter to items."""
        if not self._search_term:
            self._filtered_items = self._all_items.copy()
        else:
            search_lower = self._search_term.lower()
            self._filtered_items = [
                item for item in self._all_items
                if search_lower in str(item).lower()
            ]
        
        # Reset selection if it's out of bounds
        if self._selected_index >= len(self._filtered_items):
            self._selected_index = -1
        
        # Update status
        total_items = len(self._all_items)
        filtered_items = len(self._filtered_items)
        
        if self._search_term:
            status_text = f"Showing {filtered_items} of {total_items} items (filtered)"
        else:
            status_text = f"Showing {total_items} items"
        
        self.status_label.config(text=status_text)
    
    def _update_display(self):
        """Update the visible items display."""
        if not self._filtered_items:
            # No items to display
            for label in self.item_labels:
                label.config(text="", bg=self.canvas.cget('bg'))
            self._update_scrollbar()
            return
        
        # Calculate visible range
        total_items = len(self._filtered_items)
        max_start = max(0, total_items - self.visible_items)
        self._visible_start = min(self._visible_start, max_start)
        self._visible_end = min(self._visible_start + self.visible_items, total_items)
        
        # Update visible items
        for i, label in enumerate(self.item_labels):
            item_index = self._visible_start + i
            
            if item_index < self._visible_end:
                item = self._filtered_items[item_index]
                label.config(text=str(item))
                
                # Highlight selected item
                if item_index == self._selected_index:
                    label.config(bg='#0078d4', fg='white')
                else:
                    label.config(bg='white', fg='black')
            else:
                label.config(text="", bg=self.canvas.cget('bg'))
        
        self._update_scrollbar()
    
    def _update_scrollbar(self):
        """Update the scrollbar position and size."""
        if not self._filtered_items:
            self.scrollbar.set(0, 1)
            return
        
        total_items = len(self._filtered_items)
        visible_items = min(self.visible_items, total_items)
        
        # Calculate scrollbar position
        if total_items <= self.visible_items:
            # All items visible
            self.scrollbar.set(0, 1)
        else:
            start_fraction = self._visible_start / total_items
            end_fraction = (self._visible_start + visible_items) / total_items
            self.scrollbar.set(start_fraction, end_fraction)
    
    def _on_scroll(self, *args):
        """Handle scrollbar movement."""
        if not self._filtered_items:
            return
        
        if args[0] == 'moveto':
            # Direct position
            fraction = float(args[1])
            total_items = len(self._filtered_items)
            new_start = int(fraction * (total_items - self.visible_items))
            new_start = max(0, min(new_start, total_items - self.visible_items))
            
        elif args[0] in ('scroll', 'units'):
            # Scroll by units
            delta = int(args[1])
            new_start = self._visible_start + delta
            new_start = max(0, min(new_start, len(self._filtered_items) - self.visible_items))
        
        else:
            return
        
        if new_start != self._visible_start:
            self._visible_start = new_start
            self._update_display()
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if not self._filtered_items:
            return
        
        # Calculate scroll delta
        delta = -1 * (event.delta // 120)  # Windows/Mac compatibility
        
        new_start = self._visible_start + delta
        new_start = max(0, min(new_start, len(self._filtered_items) - self.visible_items))
        
        if new_start != self._visible_start:
            self._visible_start = new_start
            self._update_display()
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize."""
        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Update canvas window width
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _on_item_click(self, visible_index):
        """Handle item click."""
        actual_index = self._visible_start + visible_index
        
        if actual_index < len(self._filtered_items):
            self._selected_index = actual_index
            self._update_display()
            
            # Call selection callback
            if self.selection_callback:
                selected_item = self._filtered_items[actual_index]
                self.selection_callback(selected_item, actual_index)
    
    def _on_item_double_click(self, visible_index):
        """Handle item double-click."""
        actual_index = self._visible_start + visible_index
        
        if actual_index < len(self._filtered_items):
            selected_item = self._filtered_items[actual_index]
            logger.info(f"Double-clicked item: {selected_item}")
    
    def _on_key_press(self, event):
        """Handle keyboard navigation."""
        if not self._filtered_items:
            return
        
        if event.keysym == 'Up':
            if self._selected_index > 0:
                self._selected_index -= 1
                self._ensure_visible(self._selected_index)
                self._update_display()
        
        elif event.keysym == 'Down':
            if self._selected_index < len(self._filtered_items) - 1:
                self._selected_index += 1
                self._ensure_visible(self._selected_index)
                self._update_display()
        
        elif event.keysym == 'Home':
            self._selected_index = 0
            self._ensure_visible(self._selected_index)
            self._update_display()
        
        elif event.keysym == 'End':
            self._selected_index = len(self._filtered_items) - 1
            self._ensure_visible(self._selected_index)
            self._update_display()
    
    def _ensure_visible(self, index):
        """Ensure the specified index is visible."""
        if index < self._visible_start:
            self._visible_start = index
        elif index >= self._visible_start + self.visible_items:
            self._visible_start = index - self.visible_items + 1
        
        # Clamp to valid range
        max_start = max(0, len(self._filtered_items) - self.visible_items)
        self._visible_start = max(0, min(self._visible_start, max_start))
    
    def _on_search_changed(self, *args):
        """Handle search term changes."""
        new_term = self.search_var.get()
        
        # Debounce search to avoid excessive filtering
        if self._search_thread and self._search_thread.is_alive():
            return
        
        self._search_thread = threading.Timer(0.3, self._perform_search, [new_term])
        self._search_thread.start()
    
    def _perform_search(self, search_term):
        """Perform the actual search filtering."""
        with self._search_lock:
            self._search_term = search_term
            self._apply_filter()
            
            # Reset view to top
            self._visible_start = 0
            self._selected_index = -1
            
            # Update display on main thread
            self.canvas.after(0, self._update_display)
    
    def _on_search_enter(self, event):
        """Handle Enter key in search field."""
        # Select first item if available
        if self._filtered_items:
            self._selected_index = 0
            self._visible_start = 0
            self._update_display()
            
            if self.selection_callback:
                selected_item = self._filtered_items[0]
                self.selection_callback(selected_item, 0)
    
    def _clear_search(self):
        """Clear the search field."""
        self.search_var.set("")
        self.search_entry.focus_set()


class VirtualCombobox:
    """
    A virtual combobox that can handle large datasets efficiently.
    
    Combines an entry field with a virtual scrolling dropdown.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize the virtual combobox.
        
        Parameters:
        -----------
        parent : tk.Widget
            Parent widget
        **kwargs : dict
            Additional configuration options
        """
        self.parent = parent
        
        # Configuration
        self.selection_callback = kwargs.get('selection_callback', None)
        self.dropdown_height = kwargs.get('dropdown_height', 200)
        
        # State
        self._items = []
        self._is_dropdown_open = False
        self._dropdown_window = None
        
        # Create the UI
        self._create_widgets()
        self._setup_bindings()
        
        logger.info("VirtualCombobox initialized")
    
    def _create_widgets(self):
        """Create the combobox widgets."""
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.X)
        
        # Entry field
        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(
            self.main_frame,
            textvariable=self.entry_var
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Dropdown button
        self.dropdown_button = ttk.Button(
            self.main_frame,
            text="▼",
            width=3,
            command=self._toggle_dropdown
        )
        self.dropdown_button.pack(side=tk.RIGHT)
    
    def _setup_bindings(self):
        """Set up event bindings."""
        self.entry.bind('<KeyRelease>', self._on_entry_changed)
        self.entry.bind('<Button-1>', self._on_entry_click)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        
        # Close dropdown when clicking outside
        self.parent.bind('<Button-1>', self._on_outside_click, add='+')
    
    def set_items(self, items: List[Any]):
        """Set the items for the combobox."""
        self._items = items.copy() if items else []
        logger.info(f"VirtualCombobox loaded {len(self._items)} items")
    
    def get_value(self) -> str:
        """Get the current value."""
        return self.entry_var.get()
    
    def set_value(self, value: str):
        """Set the current value."""
        self.entry_var.set(value)
    
    def _toggle_dropdown(self):
        """Toggle the dropdown visibility."""
        if self._is_dropdown_open:
            self._close_dropdown()
        else:
            self._open_dropdown()
    
    def _open_dropdown(self):
        """Open the dropdown list."""
        if self._is_dropdown_open:
            return
        
        # Create dropdown window
        self._dropdown_window = tk.Toplevel(self.parent)
        self._dropdown_window.wm_overrideredirect(True)
        
        # Position dropdown
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width() + self.dropdown_button.winfo_width()
        
        self._dropdown_window.geometry(f"{width}x{self.dropdown_height}+{x}+{y}")
        
        # Create virtual listbox in dropdown
        self.dropdown_listbox = VirtualScrollingListbox(
            self._dropdown_window,
            search_enabled=True,
            selection_callback=self._on_dropdown_selection
        )
        
        # Filter items based on current entry value
        current_value = self.entry_var.get().lower()
        filtered_items = [
            item for item in self._items
            if current_value in str(item).lower()
        ]
        
        self.dropdown_listbox.set_items(filtered_items)
        
        self._is_dropdown_open = True
        self.dropdown_button.config(text="▲")
    
    def _close_dropdown(self):
        """Close the dropdown list."""
        if not self._is_dropdown_open:
            return
        
        if self._dropdown_window:
            self._dropdown_window.destroy()
            self._dropdown_window = None
        
        self._is_dropdown_open = False
        self.dropdown_button.config(text="▼")
    
    def _on_dropdown_selection(self, item, index):
        """Handle selection from dropdown."""
        self.entry_var.set(str(item))
        self._close_dropdown()
        
        if self.selection_callback:
            self.selection_callback(item, index)
    
    def _on_entry_changed(self, event):
        """Handle entry field changes."""
        if self._is_dropdown_open and self.dropdown_listbox:
            # Update dropdown filtering
            current_value = self.entry_var.get().lower()
            filtered_items = [
                item for item in self._items
                if current_value in str(item).lower()
            ]
            self.dropdown_listbox.set_items(filtered_items)
    
    def _on_entry_click(self, event):
        """Handle entry field click."""
        if not self._is_dropdown_open:
            self._open_dropdown()
    
    def _on_focus_out(self, event):
        """Handle focus leaving the entry field."""
        # Delay closing to allow dropdown interaction
        self.parent.after(100, self._check_focus)
    
    def _check_focus(self):
        """Check if focus is still within the combobox."""
        try:
            focused = self.parent.focus_get()
            if (focused != self.entry and 
                focused != self.dropdown_button and
                (not self._dropdown_window or 
                 not str(focused).startswith(str(self._dropdown_window)))):
                self._close_dropdown()
        except:
            self._close_dropdown()
    
    def _on_outside_click(self, event):
        """Handle clicks outside the combobox."""
        if self._is_dropdown_open:
            # Check if click is outside our widgets
            widget = event.widget
            if (widget != self.entry and 
                widget != self.dropdown_button and
                (not self._dropdown_window or 
                 not str(widget).startswith(str(self._dropdown_window)))):
                self._close_dropdown() 