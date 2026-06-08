"""
AI Settings Dialog for Ollama Configuration
Provides a user interface for configuring AI settings
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Callable
import threading

class AISettingsDialog:
    """Dialog for configuring AI settings"""
    
    def __init__(self, parent, config: Dict[str, Any], on_save: Callable = None):
        """
        Initialize the AI settings dialog
        
        Args:
            parent: Parent window
            config: Current configuration
            on_save: Callback function when settings are saved
        """
        self.parent = parent
        self.config = config.copy()
        self.on_save = on_save
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("AI Settings - Ollama Configuration")
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (600 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        self.dialog.resizable(False, False)
        
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        """Set up the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="AI Settings Configuration",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # General settings tab
        general_frame = ttk.Frame(notebook, padding=20)
        notebook.add(general_frame, text="General")
        self.setup_general_tab(general_frame)
        
        # Ollama settings tab
        ollama_frame = ttk.Frame(notebook, padding=20)
        notebook.add(ollama_frame, text="Ollama")
        self.setup_ollama_tab(ollama_frame)
        
        # Advanced settings tab
        advanced_frame = ttk.Frame(notebook, padding=20)
        notebook.add(advanced_frame, text="Advanced")
        self.setup_advanced_tab(advanced_frame)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Save Settings",
            command=self.save_settings,
            style="Accent.TButton"
        ).pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            button_frame,
            text="Test Connection",
            command=self.test_connection
        ).pack(side=tk.LEFT)
        
        # Configure button styles
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
    
    def setup_general_tab(self, parent):
        """Set up the general settings tab"""
        # Enable AI checkbox
        self.ai_enabled_var = tk.BooleanVar()
        ai_check = ttk.Checkbutton(
            parent,
            text="Enable AI-powered responses",
            variable=self.ai_enabled_var,
            command=self.on_ai_toggle
        )
        ai_check.pack(anchor=tk.W, pady=(0, 20))
        
        # AI Status
        status_frame = ttk.LabelFrame(parent, text="AI Status", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.status_label = ttk.Label(
            status_frame,
            text="Checking AI availability...",
            font=("Arial", 10)
        )
        self.status_label.pack(anchor=tk.W)
        
        # Response settings
        response_frame = ttk.LabelFrame(parent, text="Response Settings", padding=10)
        response_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Response type
        ttk.Label(response_frame, text="Default Response Type:").pack(anchor=tk.W)
        self.response_type_var = tk.StringVar()
        response_combo = ttk.Combobox(
            response_frame,
            textvariable=self.response_type_var,
            values=["general", "taxi", "takeoff", "landing", "approach"],
            state="readonly",
            width=20
        )
        response_combo.pack(anchor=tk.W, pady=(5, 10))
        
        # Auto-response checkbox
        self.auto_response_var = tk.BooleanVar()
        auto_check = ttk.Checkbutton(
            response_frame,
            text="Enable automatic responses",
            variable=self.auto_response_var
        )
        auto_check.pack(anchor=tk.W)
    
    def setup_ollama_tab(self, parent):
        """Set up the Ollama settings tab"""
        # Ollama URL
        url_frame = ttk.Frame(parent)
        url_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(url_frame, text="Ollama URL:").pack(anchor=tk.W)
        self.ollama_url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.ollama_url_var, width=40)
        url_entry.pack(anchor=tk.W, pady=(5, 0))
        
        # Model selection
        model_frame = ttk.Frame(parent)
        model_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(model_frame, text="Model:").pack(anchor=tk.W)
        
        model_select_frame = ttk.Frame(model_frame)
        model_select_frame.pack(anchor=tk.W, pady=(5, 0))
        
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            model_select_frame,
            textvariable=self.model_var,
            values=["llama2", "llama2:7b", "llama2:13b", "codellama", "mistral"],
            state="readonly",
            width=20
        )
        self.model_combo.pack(side=tk.LEFT)
        
        ttk.Button(
            model_select_frame,
            text="Refresh Models",
            command=self.refresh_models
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Model info
        self.model_info_label = ttk.Label(
            model_frame,
            text="",
            font=("Arial", 9, "italic"),
            foreground="gray"
        )
        self.model_info_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Connection test
        test_frame = ttk.LabelFrame(parent, text="Connection Test", padding=10)
        test_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.test_result_label = ttk.Label(
            test_frame,
            text="Click 'Test Connection' to verify Ollama connectivity",
            font=("Arial", 9)
        )
        self.test_result_label.pack(anchor=tk.W)
    
    def setup_advanced_tab(self, parent):
        """Set up the advanced settings tab"""
        # Temperature setting
        temp_frame = ttk.LabelFrame(parent, text="Generation Settings", padding=10)
        temp_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(temp_frame, text="Temperature (Creativity):").pack(anchor=tk.W)
        
        temp_scale_frame = ttk.Frame(temp_frame)
        temp_scale_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.temperature_var = tk.DoubleVar()
        temp_scale = ttk.Scale(
            temp_scale_frame,
            from_=0.0,
            to=1.0,
            variable=self.temperature_var,
            orient=tk.HORIZONTAL
        )
        temp_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.temp_value_label = ttk.Label(temp_frame, text="0.7")
        self.temp_value_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Bind temperature scale to update label
        temp_scale.configure(command=self.update_temp_label)
        
        # Context settings
        context_frame = ttk.LabelFrame(parent, text="Context Settings", padding=10)
        context_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(context_frame, text="Max History Length:").pack(anchor=tk.W)
        self.max_history_var = tk.IntVar()
        history_spin = ttk.Spinbox(
            context_frame,
            from_=5,
            to=50,
            textvariable=self.max_history_var,
            width=10
        )
        history_spin.pack(anchor=tk.W, pady=(5, 0))
        
        # Timeout settings
        timeout_frame = ttk.LabelFrame(parent, text="Timeout Settings", padding=10)
        timeout_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(timeout_frame, text="API Timeout (seconds):").pack(anchor=tk.W)
        self.timeout_var = tk.IntVar()
        timeout_spin = ttk.Spinbox(
            timeout_frame,
            from_=5,
            to=60,
            textvariable=self.timeout_var,
            width=10
        )
        timeout_spin.pack(anchor=tk.W, pady=(5, 0))
    
    def load_current_settings(self):
        """Load current settings into the UI"""
        # General settings
        self.ai_enabled_var.set(self.config.get("ai_enabled", True))
        self.response_type_var.set(self.config.get("response_type", "general"))
        self.auto_response_var.set(self.config.get("auto_response", False))
        
        # Ollama settings
        self.ollama_url_var.set(self.config.get("ollama_url", "http://localhost:11434"))
        self.model_var.set(self.config.get("ai_model", "llama2"))
        
        # Advanced settings
        self.temperature_var.set(self.config.get("ai_temperature", 0.7))
        self.max_history_var.set(self.config.get("max_history", 20))
        self.timeout_var.set(self.config.get("timeout", 30))
        
        # Update temperature label
        self.update_temp_label(self.temperature_var.get())
        
        # Check AI availability
        self.check_ai_status()
    
    def update_temp_label(self, value):
        """Update temperature value label"""
        self.temp_value_label.config(text=f"{float(value):.1f}")
    
    def on_ai_toggle(self):
        """Handle AI enable/disable toggle"""
        enabled = self.ai_enabled_var.get()
        if enabled:
            self.check_ai_status()
        else:
            self.status_label.config(text="AI disabled")
    
    def check_ai_status(self):
        """Check AI availability status"""
        def check_status():
            try:
                from utils.ollama_client import OllamaClient
                client = OllamaClient(
                    base_url=self.ollama_url_var.get(),
                    model=self.model_var.get()
                )
                
                if client.is_available():
                    self.status_label.config(text="✅ AI available and ready")
                else:
                    self.status_label.config(text="❌ AI not available")
            except Exception as e:
                self.status_label.config(text=f"❌ Error: {str(e)}")
        
        # Run in separate thread to avoid blocking UI
        threading.Thread(target=check_status, daemon=True).start()
    
    def refresh_models(self):
        """Refresh available models from Ollama"""
        def refresh():
            try:
                from utils.ollama_client import OllamaClient
                client = OllamaClient(base_url=self.ollama_url_var.get())
                models = client.get_available_models()
                
                if models:
                    self.model_combo['values'] = models
                    self.model_info_label.config(text=f"Found {len(models)} model(s)")
                else:
                    self.model_info_label.config(text="No models found")
            except Exception as e:
                self.model_info_label.config(text=f"Error: {str(e)}")
        
        threading.Thread(target=refresh, daemon=True).start()
    
    def test_connection(self):
        """Test connection to Ollama"""
        def test():
            try:
                from utils.ollama_client import OllamaClient
                client = OllamaClient(
                    base_url=self.ollama_url_var.get(),
                    model=self.model_var.get()
                )
                
                if client.is_available():
                    self.test_result_label.config(
                        text="✅ Connection successful",
                        foreground="green"
                    )
                else:
                    self.test_result_label.config(
                        text="❌ Connection failed",
                        foreground="red"
                    )
            except Exception as e:
                self.test_result_label.config(
                    text=f"❌ Error: {str(e)}",
                    foreground="red"
                )
        
        self.test_result_label.config(text="Testing connection...")
        threading.Thread(target=test, daemon=True).start()
    
    def save_settings(self):
        """Save the current settings"""
        try:
            # Collect settings
            new_config = {
                "ai_enabled": self.ai_enabled_var.get(),
                "response_type": self.response_type_var.get(),
                "auto_response": self.auto_response_var.get(),
                "ollama_url": self.ollama_url_var.get(),
                "ai_model": self.model_var.get(),
                "ai_temperature": self.temperature_var.get(),
                "max_history": self.max_history_var.get(),
                "timeout": self.timeout_var.get()
            }
            
            # Update config
            self.config.update(new_config)
            
            # Call save callback if provided
            if self.on_save:
                self.on_save(new_config)
            
            messagebox.showinfo("Success", "AI settings saved successfully!")
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
