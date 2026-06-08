"""
Smart Filtering Components for the Clinic Data Visualizer.

This module provides intelligent filtering capabilities including auto-complete,
filter suggestions, presets, and history for improved user experience.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import logging
from collections import defaultdict, Counter
import pandas as pd

logger = logging.getLogger(__name__)


class AutoCompleteEntry:
    """
    An entry widget with auto-complete functionality.
    
    Provides suggestions based on available data values and user history.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize the auto-complete entry.
        
        Parameters:
        -----------
        parent : tk.Widget
            Parent widget
        **kwargs : dict
            Additional configuration options
        """
        self.parent = parent
        
        # Configuration
        self.suggestions = kwargs.get('suggestions', [])
        self.max_suggestions = kwargs.get('max_suggestions', 10)
        self.selection_callback = kwargs.get('selection_callback', None)
        self.case_sensitive = kwargs.get('case_sensitive', False)
        
        # State
        self._suggestion_window = None
        self._suggestion_listbox = None
        self._is_suggestion_open = False
        
        # Create the UI
        self._create_widgets()
        self._setup_bindings()
        
        logger.info("AutoCompleteEntry initialized")
    
    def _create_widgets(self):
        """Create the auto-complete entry widgets."""
        # Entry field
        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(
            self.parent,
            textvariable=self.entry_var
        )
        self.entry.pack(fill=tk.X)
    
    def _setup_bindings(self):
        """Set up event bindings."""
        self.entry.bind('<KeyRelease>', self._on_key_release)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        self.entry.bind('<Button-1>', self._on_click)
        
        # Navigation keys
        self.entry.bind('<Down>', self._on_down_key)
        self.entry.bind('<Up>', self._on_up_key)
        self.entry.bind('<Return>', self._on_return_key)
        self.entry.bind('<Escape>', self._on_escape_key)
    
    def set_suggestions(self, suggestions: List[str]):
        """Set the available suggestions."""
        self.suggestions = suggestions.copy() if suggestions else []
        logger.info(f"AutoCompleteEntry loaded {len(self.suggestions)} suggestions")
    
    def get_value(self) -> str:
        """Get the current value."""
        return self.entry_var.get()
    
    def set_value(self, value: str):
        """Set the current value."""
        self.entry_var.set(value)
    
    def _get_matching_suggestions(self, text: str) -> List[str]:
        """Get suggestions that match the input text."""
        if not text:
            return []
        
        if self.case_sensitive:
            matches = [s for s in self.suggestions if text in s]
        else:
            text_lower = text.lower()
            matches = [s for s in self.suggestions if text_lower in s.lower()]
        
        # Sort by relevance (exact matches first, then starts with, then contains)
        exact_matches = []
        starts_with = []
        contains = []
        
        for match in matches:
            match_lower = match.lower() if not self.case_sensitive else match
            text_check = text.lower() if not self.case_sensitive else text
            
            if match_lower == text_check:
                exact_matches.append(match)
            elif match_lower.startswith(text_check):
                starts_with.append(match)
            else:
                contains.append(match)
        
        # Combine and limit results
        result = exact_matches + starts_with + contains
        return result[:self.max_suggestions]
    
    def _show_suggestions(self, suggestions: List[str]):
        """Show the suggestions dropdown."""
        if not suggestions:
            self._hide_suggestions()
            return
        
        # Create suggestion window if it doesn't exist
        if not self._suggestion_window:
            self._suggestion_window = tk.Toplevel(self.parent)
            self._suggestion_window.wm_overrideredirect(True)
            
            # Create listbox for suggestions
            self._suggestion_listbox = tk.Listbox(
                self._suggestion_window,
                height=min(len(suggestions), self.max_suggestions)
            )
            self._suggestion_listbox.pack(fill=tk.BOTH, expand=True)
            
            # Bind selection
            self._suggestion_listbox.bind('<Double-Button-1>', self._on_suggestion_select)
            self._suggestion_listbox.bind('<Return>', self._on_suggestion_select)
        
        # Clear and populate listbox
        self._suggestion_listbox.delete(0, tk.END)
        for suggestion in suggestions:
            self._suggestion_listbox.insert(tk.END, suggestion)
        
        # Position window
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = self.entry.winfo_width()
        height = min(len(suggestions), self.max_suggestions) * 20 + 4
        
        self._suggestion_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Update listbox height
        self._suggestion_listbox.config(height=min(len(suggestions), self.max_suggestions))
        
        self._is_suggestion_open = True
    
    def _hide_suggestions(self):
        """Hide the suggestions dropdown."""
        if self._suggestion_window:
            self._suggestion_window.destroy()
            self._suggestion_window = None
            self._suggestion_listbox = None
        
        self._is_suggestion_open = False
    
    def _on_key_release(self, event):
        """Handle key release events."""
        if event.keysym in ('Up', 'Down', 'Return', 'Escape'):
            return
        
        text = self.entry_var.get()
        suggestions = self._get_matching_suggestions(text)
        self._show_suggestions(suggestions)
    
    def _on_focus_out(self, event):
        """Handle focus out events."""
        # Delay hiding to allow selection
        self.parent.after(100, self._check_focus)
    
    def _check_focus(self):
        """Check if focus is still within the auto-complete widget."""
        try:
            focused = self.parent.focus_get()
            if (focused != self.entry and 
                (not self._suggestion_listbox or focused != self._suggestion_listbox)):
                self._hide_suggestions()
        except:
            self._hide_suggestions()
    
    def _on_click(self, event):
        """Handle entry click."""
        text = self.entry_var.get()
        if text:
            suggestions = self._get_matching_suggestions(text)
            self._show_suggestions(suggestions)
    
    def _on_down_key(self, event):
        """Handle down arrow key."""
        if self._is_suggestion_open and self._suggestion_listbox:
            current = self._suggestion_listbox.curselection()
            if current:
                next_index = min(current[0] + 1, self._suggestion_listbox.size() - 1)
            else:
                next_index = 0
            
            self._suggestion_listbox.selection_clear(0, tk.END)
            self._suggestion_listbox.selection_set(next_index)
            self._suggestion_listbox.see(next_index)
            return 'break'
    
    def _on_up_key(self, event):
        """Handle up arrow key."""
        if self._is_suggestion_open and self._suggestion_listbox:
            current = self._suggestion_listbox.curselection()
            if current:
                prev_index = max(current[0] - 1, 0)
            else:
                prev_index = self._suggestion_listbox.size() - 1
            
            self._suggestion_listbox.selection_clear(0, tk.END)
            self._suggestion_listbox.selection_set(prev_index)
            self._suggestion_listbox.see(prev_index)
            return 'break'
    
    def _on_return_key(self, event):
        """Handle return key."""
        if self._is_suggestion_open and self._suggestion_listbox:
            selection = self._suggestion_listbox.curselection()
            if selection:
                self._select_suggestion(selection[0])
            return 'break'
    
    def _on_escape_key(self, event):
        """Handle escape key."""
        self._hide_suggestions()
        return 'break'
    
    def _on_suggestion_select(self, event):
        """Handle suggestion selection."""
        if self._suggestion_listbox:
            selection = self._suggestion_listbox.curselection()
            if selection:
                self._select_suggestion(selection[0])
    
    def _select_suggestion(self, index: int):
        """Select a suggestion by index."""
        if self._suggestion_listbox and 0 <= index < self._suggestion_listbox.size():
            suggestion = self._suggestion_listbox.get(index)
            self.entry_var.set(suggestion)
            self._hide_suggestions()
            
            if self.selection_callback:
                self.selection_callback(suggestion)


class FilterPresetManager:
    """
    Manager for filter presets and favorites.
    
    Allows users to save, load, and manage filter configurations.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize the filter preset manager.
        
        Parameters:
        -----------
        parent : tk.Widget
            Parent widget
        **kwargs : dict
            Additional configuration options
        """
        self.parent = parent
        
        # Configuration
        self.preset_file = kwargs.get('preset_file', 'filter_presets.json')
        self.apply_callback = kwargs.get('apply_callback', None)
        
        # State
        self.presets = {}
        
        # Create the UI
        self._create_widgets()
        self._load_presets()
        
        logger.info("FilterPresetManager initialized")
    
    def _create_widgets(self):
        """Create the preset manager widgets."""
        # Main frame
        self.main_frame = ttk.LabelFrame(self.parent, text="Filter Presets")
        self.main_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Preset selection frame
        self.selection_frame = ttk.Frame(self.main_frame)
        self.selection_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(self.selection_frame, text="Preset:").pack(side=tk.LEFT)
        
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(
            self.selection_frame,
            textvariable=self.preset_var,
            state='readonly',
            width=20
        )
        self.preset_combo.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Buttons frame
        self.buttons_frame = ttk.Frame(self.main_frame)
        self.buttons_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.apply_button = ttk.Button(
            self.buttons_frame,
            text="Apply",
            command=self._apply_preset,
            width=8
        )
        self.apply_button.pack(side=tk.LEFT)
        
        self.save_button = ttk.Button(
            self.buttons_frame,
            text="Save",
            command=self._save_preset,
            width=8
        )
        self.save_button.pack(side=tk.LEFT, padx=(5, 0))
        
        self.delete_button = ttk.Button(
            self.buttons_frame,
            text="Delete",
            command=self._delete_preset,
            width=8
        )
        self.delete_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Quick presets frame
        self.quick_frame = ttk.Frame(self.main_frame)
        self.quick_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(self.quick_frame, text="Quick:").pack(side=tk.LEFT)
        
        # Common quick preset buttons
        quick_presets = [
            ("Today", self._create_today_filter),
            ("This Week", self._create_week_filter),
            ("This Month", self._create_month_filter),
            ("Clear All", self._clear_filters)
        ]
        
        for name, callback in quick_presets:
            btn = ttk.Button(
                self.quick_frame,
                text=name,
                command=callback,
                width=10
            )
            btn.pack(side=tk.LEFT, padx=(5, 0))
    
    def _load_presets(self):
        """Load presets from file."""
        try:
            if os.path.exists(self.preset_file):
                with open(self.preset_file, 'r') as f:
                    self.presets = json.load(f)
                
                # Update combobox
                preset_names = list(self.presets.keys())
                self.preset_combo['values'] = preset_names
                
                logger.info(f"Loaded {len(self.presets)} filter presets")
            else:
                self.presets = {}
                self.preset_combo['values'] = []
        
        except Exception as e:
            logger.error(f"Error loading presets: {e}")
            self.presets = {}
            self.preset_combo['values'] = []
    
    def _save_presets(self):
        """Save presets to file."""
        try:
            with open(self.preset_file, 'w') as f:
                json.dump(self.presets, f, indent=2)
            
            logger.info(f"Saved {len(self.presets)} filter presets")
        
        except Exception as e:
            logger.error(f"Error saving presets: {e}")
            messagebox.showerror("Error", f"Failed to save presets: {e}")
    
    def save_current_filters(self, filters: Dict[str, Any], name: str = None):
        """
        Save the current filter configuration as a preset.
        
        Parameters:
        -----------
        filters : Dict[str, Any]
            Current filter configuration
        name : str, optional
            Name for the preset (will prompt if not provided)
        """
        if not name:
            name = tk.simpledialog.askstring(
                "Save Preset",
                "Enter a name for this filter preset:",
                parent=self.parent
            )
        
        if name:
            self.presets[name] = {
                'filters': filters.copy(),
                'created': datetime.now().isoformat(),
                'description': f"Saved on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
            
            # Update combobox
            preset_names = list(self.presets.keys())
            self.preset_combo['values'] = preset_names
            self.preset_var.set(name)
            
            self._save_presets()
            
            logger.info(f"Saved filter preset: {name}")
    
    def _apply_preset(self):
        """Apply the selected preset."""
        preset_name = self.preset_var.get()
        
        if preset_name and preset_name in self.presets:
            filters = self.presets[preset_name]['filters']
            
            if self.apply_callback:
                self.apply_callback(filters)
            
            logger.info(f"Applied filter preset: {preset_name}")
        else:
            messagebox.showwarning("Warning", "Please select a preset to apply.")
    
    def _save_preset(self):
        """Save current filters as a new preset."""
        # This would typically get current filters from the parent component
        # For now, we'll show a placeholder message
        messagebox.showinfo(
            "Save Preset",
            "This feature requires integration with the filter component.\n"
            "Use the save_current_filters() method to save presets programmatically."
        )
    
    def _delete_preset(self):
        """Delete the selected preset."""
        preset_name = self.preset_var.get()
        
        if preset_name and preset_name in self.presets:
            result = messagebox.askyesno(
                "Delete Preset",
                f"Are you sure you want to delete the preset '{preset_name}'?"
            )
            
            if result:
                del self.presets[preset_name]
                
                # Update combobox
                preset_names = list(self.presets.keys())
                self.preset_combo['values'] = preset_names
                self.preset_var.set("")
                
                self._save_presets()
                
                logger.info(f"Deleted filter preset: {preset_name}")
        else:
            messagebox.showwarning("Warning", "Please select a preset to delete.")
    
    def _create_today_filter(self):
        """Create a filter for today's data."""
        today = datetime.now().strftime('%d/%m/%Y')
        filters = {
            'start_date': today,
            'end_date': today
        }
        
        if self.apply_callback:
            self.apply_callback(filters)
        
        logger.info("Applied 'Today' quick filter")
    
    def _create_week_filter(self):
        """Create a filter for this week's data."""
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        filters = {
            'start_date': start_of_week.strftime('%d/%m/%Y'),
            'end_date': end_of_week.strftime('%d/%m/%Y')
        }
        
        if self.apply_callback:
            self.apply_callback(filters)
        
        logger.info("Applied 'This Week' quick filter")
    
    def _create_month_filter(self):
        """Create a filter for this month's data."""
        today = datetime.now()
        start_of_month = today.replace(day=1)
        
        # Get last day of month
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        filters = {
            'start_date': start_of_month.strftime('%d/%m/%Y'),
            'end_date': end_of_month.strftime('%d/%m/%Y')
        }
        
        if self.apply_callback:
            self.apply_callback(filters)
        
        logger.info("Applied 'This Month' quick filter")
    
    def _clear_filters(self):
        """Clear all filters."""
        filters = {}
        
        if self.apply_callback:
            self.apply_callback(filters)
        
        logger.info("Cleared all filters")


class FilterHistoryManager:
    """
    Manager for filter history and recent filters.
    
    Tracks and provides access to recently used filter configurations.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize the filter history manager.
        
        Parameters:
        -----------
        parent : tk.Widget
            Parent widget
        **kwargs : dict
            Additional configuration options
        """
        self.parent = parent
        
        # Configuration
        self.history_file = kwargs.get('history_file', 'filter_history.json')
        self.max_history = kwargs.get('max_history', 20)
        self.apply_callback = kwargs.get('apply_callback', None)
        
        # State
        self.history = []
        
        # Create the UI
        self._create_widgets()
        self._load_history()
        
        logger.info("FilterHistoryManager initialized")
    
    def _create_widgets(self):
        """Create the history manager widgets."""
        # Main frame
        self.main_frame = ttk.LabelFrame(self.parent, text="Recent Filters")
        self.main_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # History listbox
        self.history_frame = ttk.Frame(self.main_frame)
        self.history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        self.history_listbox = tk.Listbox(
            self.history_frame,
            height=5,
            selectmode=tk.SINGLE
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for history
        self.history_scrollbar = ttk.Scrollbar(
            self.history_frame,
            orient=tk.VERTICAL,
            command=self.history_listbox.yview
        )
        self.history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.config(yscrollcommand=self.history_scrollbar.set)
        
        # Buttons
        self.history_buttons_frame = ttk.Frame(self.main_frame)
        self.history_buttons_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.apply_history_button = ttk.Button(
            self.history_buttons_frame,
            text="Apply",
            command=self._apply_history_item,
            width=8
        )
        self.apply_history_button.pack(side=tk.LEFT)
        
        self.clear_history_button = ttk.Button(
            self.history_buttons_frame,
            text="Clear History",
            command=self._clear_history,
            width=12
        )
        self.clear_history_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Bind double-click
        self.history_listbox.bind('<Double-Button-1>', lambda e: self._apply_history_item())
    
    def _load_history(self):
        """Load history from file."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                
                self._update_history_display()
                
                logger.info(f"Loaded {len(self.history)} filter history items")
            else:
                self.history = []
        
        except Exception as e:
            logger.error(f"Error loading filter history: {e}")
            self.history = []
    
    def _save_history(self):
        """Save history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
            
            logger.info(f"Saved {len(self.history)} filter history items")
        
        except Exception as e:
            logger.error(f"Error saving filter history: {e}")
    
    def add_to_history(self, filters: Dict[str, Any]):
        """
        Add a filter configuration to history.
        
        Parameters:
        -----------
        filters : Dict[str, Any]
            Filter configuration to add
        """
        if not filters:
            return
        
        # Create history entry
        entry = {
            'filters': filters.copy(),
            'timestamp': datetime.now().isoformat(),
            'description': self._create_filter_description(filters)
        }
        
        # Remove duplicate if exists
        self.history = [h for h in self.history if h['filters'] != filters]
        
        # Add to beginning
        self.history.insert(0, entry)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history = self.history[:self.max_history]
        
        self._update_history_display()
        self._save_history()
        
        logger.info(f"Added filter to history: {entry['description']}")
    
    def _create_filter_description(self, filters: Dict[str, Any]) -> str:
        """Create a human-readable description of the filters."""
        parts = []
        
        if 'start_date' in filters or 'end_date' in filters:
            start = filters.get('start_date', '')
            end = filters.get('end_date', '')
            if start and end:
                if start == end:
                    parts.append(f"Date: {start}")
                else:
                    parts.append(f"Date: {start} to {end}")
            elif start:
                parts.append(f"From: {start}")
            elif end:
                parts.append(f"Until: {end}")
        
        if 'service_type' in filters and filters['service_type']:
            parts.append(f"Service: {filters['service_type']}")
        
        if 'action' in filters and filters['action']:
            parts.append(f"Action: {filters['action']}")
        
        if 'patient_id' in filters and filters['patient_id']:
            parts.append(f"Patient: {filters['patient_id']}")
        
        if not parts:
            return "No filters"
        
        return " | ".join(parts)
    
    def _update_history_display(self):
        """Update the history listbox display."""
        self.history_listbox.delete(0, tk.END)
        
        for entry in self.history:
            timestamp = datetime.fromisoformat(entry['timestamp'])
            time_str = timestamp.strftime('%m/%d %H:%M')
            display_text = f"{time_str} - {entry['description']}"
            self.history_listbox.insert(tk.END, display_text)
    
    def _apply_history_item(self):
        """Apply the selected history item."""
        selection = self.history_listbox.curselection()
        
        if selection and 0 <= selection[0] < len(self.history):
            filters = self.history[selection[0]]['filters']
            
            if self.apply_callback:
                self.apply_callback(filters)
            
            logger.info(f"Applied filter from history: {self.history[selection[0]]['description']}")
        else:
            messagebox.showwarning("Warning", "Please select a filter from history to apply.")
    
    def _clear_history(self):
        """Clear the filter history."""
        result = messagebox.askyesno(
            "Clear History",
            "Are you sure you want to clear the filter history?"
        )
        
        if result:
            self.history = []
            self._update_history_display()
            self._save_history()
            
            logger.info("Cleared filter history")


class SmartFilterSuggestionEngine:
    """
    Engine for generating intelligent filter suggestions based on data patterns.
    """
    
    def __init__(self):
        """Initialize the suggestion engine."""
        self.data_patterns = {}
        self.usage_stats = defaultdict(int)
        
        logger.info("SmartFilterSuggestionEngine initialized")
    
    def analyze_data(self, data) -> Dict[str, List[str]]:
        """
        Analyze data to extract filter suggestions.
        
        Parameters:
        -----------
        data : pandas.DataFrame
            Data to analyze
            
        Returns:
        --------
        Dict[str, List[str]]
            Dictionary of column names to suggested values
        """
        suggestions = {}
        
        if data is None or data.empty:
            return suggestions
        
        # Analyze categorical columns
        categorical_columns = [
            'Service Area', 'Service Type', 'Action', 'Patient ID', 'Location'
        ]
        
        for column in categorical_columns:
            if column in data.columns:
                # Get most common values
                value_counts = data[column].value_counts()
                top_values = value_counts.head(20).index.tolist()
                suggestions[column] = [str(v) for v in top_values if pd.notna(v)]
        
        # Analyze date patterns
        if 'Date' in data.columns:
            try:
                dates = pd.to_datetime(data['Date'], format='%d/%m/%Y', errors='coerce')
                date_range = dates.dropna()
                
                if not date_range.empty:
                    min_date = date_range.min()
                    max_date = date_range.max()
                    
                    # Generate common date suggestions
                    date_suggestions = []
                    
                    # Recent dates
                    today = datetime.now()
                    for days_back in [0, 1, 7, 30]:
                        date = today - timedelta(days=days_back)
                        if min_date <= date <= max_date:
                            date_suggestions.append(date.strftime('%d/%m/%Y'))
                    
                    # Month boundaries
                    current_month_start = today.replace(day=1)
                    if min_date <= current_month_start <= max_date:
                        date_suggestions.append(current_month_start.strftime('%d/%m/%Y'))
                    
                    suggestions['Date'] = date_suggestions
            
            except Exception as e:
                logger.warning(f"Error analyzing date patterns: {e}")
        
        # Store patterns for future use
        self.data_patterns = suggestions.copy()
        
        logger.info(f"Generated suggestions for {len(suggestions)} columns")
        return suggestions
    
    def get_suggestions_for_column(self, column: str, partial_value: str = "") -> List[str]:
        """
        Get suggestions for a specific column.
        
        Parameters:
        -----------
        column : str
            Column name
        partial_value : str
            Partial value to filter suggestions
            
        Returns:
        --------
        List[str]
            List of suggestions
        """
        if column not in self.data_patterns:
            return []
        
        suggestions = self.data_patterns[column]
        
        if partial_value:
            partial_lower = partial_value.lower()
            suggestions = [
                s for s in suggestions
                if partial_lower in s.lower()
            ]
        
        # Sort by usage frequency (most used first)
        suggestions.sort(key=lambda x: self.usage_stats.get(f"{column}:{x}", 0), reverse=True)
        
        return suggestions[:10]  # Limit to top 10
    
    def record_usage(self, column: str, value: str):
        """
        Record usage of a filter value for learning.
        
        Parameters:
        -----------
        column : str
            Column name
        value : str
            Filter value used
        """
        key = f"{column}:{value}"
        self.usage_stats[key] += 1
        
        logger.debug(f"Recorded usage: {key} (count: {self.usage_stats[key]})")
    
    def get_popular_combinations(self) -> List[Dict[str, str]]:
        """
        Get popular filter combinations based on usage patterns.
        
        Returns:
        --------
        List[Dict[str, str]]
            List of popular filter combinations
        """
        # This is a simplified implementation
        # In a real system, you'd analyze co-occurrence patterns
        
        combinations = []
        
        # Example combinations based on common use cases
        if 'Service Type' in self.data_patterns and 'Action' in self.data_patterns:
            service_types = self.data_patterns['Service Type'][:3]
            actions = self.data_patterns['Action'][:3]
            
            for service_type in service_types:
                for action in actions:
                    combinations.append({
                        'Service Type': service_type,
                        'Action': action,
                        'description': f"{service_type} - {action}"
                    })
        
        return combinations[:5]  # Limit to top 5 