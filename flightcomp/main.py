"""
Aviation Operations Assistant
A tool for both pilots and air traffic controllers to assist with aviation communications and operations.

This is the main entry point for the application. Run from project root (e.g. python main.py or python -m flightcomp).
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, List, Optional, Tuple

from PIL import Image, ImageTk

from views.role_selection import RoleSelectionScreen
from views.main_window import MainWindow
from views.atc_window import ATCWindow
from utils.config import ensure_config_directory, Config
from utils.logging_config import get_logger, setup_logging
from models.atc_model import ATCModel

logger = get_logger(__name__)

# Global config set in main() and used by load_appropriate_window / show_airport_selection_dialog
config: Optional[Config] = None


def check_dependencies() -> bool:
    """Check if all required dependencies are installed"""
    try:
        import pyttsx3
        import pygame
        from PIL import Image, ImageTk

        return True
    except ImportError as e:
        messagebox.showerror(
            "Missing Dependencies",
            f"Required dependency missing: {e}\n\n"
            "Please install required dependencies using:\n"
            "pip install -r requirements.txt",
        )
        return False


def check_ollama_availability() -> Tuple[bool, List[str]]:
    """Check if Ollama is available and working. Returns (is_available, list of model names)."""
    try:
        from utils.ollama_client import OllamaClient

        client = OllamaClient()
        return client.is_available(), client.get_available_models()
    except ImportError:
        return False, []
    except Exception as e:
        logger.debug("Ollama check failed: %s", e)
        return False, []


def show_ollama_status_dialog(parent: tk.Misc) -> None:
    """Show a minimalist status bar with Ollama status."""
    # Check if a status bar already exists and destroy it
    if hasattr(parent, '_ollama_status_bar') and parent._ollama_status_bar.winfo_exists():
        parent._ollama_status_bar.destroy()
    
    # Check Ollama status
    is_available, models = check_ollama_availability()
    
    # Create minimalist status bar frame
    status_bar = ttk.Frame(parent, relief=tk.SUNKEN, borderwidth=1)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 0))
    
    # Store reference to prevent duplicates
    parent._ollama_status_bar = status_bar
    
    # Create inner frame for content with minimal padding
    content_frame = ttk.Frame(status_bar, padding="8 4")
    content_frame.pack(fill=tk.X)
    
    # Status text
    if is_available:
        status_text = "✅ Ollama: Available"
        status_color = "green"
        model_count = len(models) if models else 0
        models_text = f"({model_count} model{'s' if model_count != 1 else ''})" if model_count > 0 else "(No models)"
    else:
        status_text = "❌ Ollama: Not Available"
        status_color = "red"
        models_text = "(No models)"
    
    # Status label
    status_label = ttk.Label(
        content_frame,
        text=status_text,
        font=("Arial", 9),
        foreground=status_color
    )
    status_label.pack(side=tk.LEFT, padx=(0, 8))
    
    # Model count label
    models_label = ttk.Label(
        content_frame,
        text=models_text,
        font=("Arial", 8),
        foreground="gray"
    )
    models_label.pack(side=tk.LEFT)
    
    # Auto-dismiss after 5 seconds if Ollama is available
    if is_available:
        def dismiss_status_bar():
            if hasattr(parent, '_ollama_status_bar') and parent._ollama_status_bar.winfo_exists():
                parent._ollama_status_bar.destroy()
                delattr(parent, '_ollama_status_bar')
        parent.after(5000, dismiss_status_bar)


def load_appropriate_window(root: tk.Tk, role: str) -> Optional[Any]:
    """Load the appropriate window based on the selected role. Returns the app instance or None if canceled."""
    if config is None:
        logger.error("Config not initialized")
        return None
    # First destroy any existing widgets to clear the screen
    for widget in root.winfo_children():
        widget.destroy()

    if role == "pilot":
        # Load pilot-specific configuration
        pilot_config = {
            "experience_level": config.get("experience_level", "beginner"),
            "aircraft_type": config.get("aircraft_type", "single_engine"),
            "voice_enabled": config.get("voice_enabled", True),
            "voice_rate": config.get("voice_rate", 150),
            "phraseology_region": config.get("phraseology_region", "US"),
            "auto_save_notes": config.get("auto_save_notes", True),
            "notes_directory": config.get("notes_directory", "atc_notes"),
        }

        # Create pilot interface with configuration
        app = MainWindow(root)

        # Apply pilot-specific settings
        if pilot_config["voice_enabled"]:
            app.speech_engine.rate = pilot_config["voice_rate"]

        return app
    elif role == "atc":
        # For ATC role, we need to select an airport first
        # Load the ATCModel to get available airports
        from models.atc_model import ATCModel

        atc_model = ATCModel()
        logger.debug("Created ATCModel with %d airports", len(atc_model.airports))
        for airport_name, airport_data in atc_model.airports.items():
            logger.debug("  %s (runways: %s)", airport_name, ", ".join(airport_data.runways))

        # Get the last selected airport from config
        last_airport = config.get("last_selected_airport")

        # Show airport selection dialog
        selected_airport, remember_choice = show_airport_selection_dialog(
            root, atc_model.airports, last_airport
        )

        if selected_airport is None:
            # User canceled airport selection
            return None

        # Save the selected airport for next time if user chose to remember
        if remember_choice:
            config.set("last_selected_airport", selected_airport)
            config.save_config()

        # Create a dictionary of airport data from the AirportConfiguration objects
        airports_dict = {}
        for name, airport_obj in atc_model.airports.items():
            # Convert AirportConfiguration to dict
            airports_dict[name] = airport_obj.to_dict()

        # Pass the config and converted airport data to the ATCWindow
        app = ATCWindow(root, config, airports_dict, selected_airport)

        return app
    else:
        messagebox.showerror("Error", f"Unknown role: {role}")
        return None


def show_airport_selection_dialog(
    parent: tk.Misc, airports: Any, last_airport: Optional[str] = None
) -> Tuple[Optional[str], bool]:
    """Show a modern dialog for the user to select an airport using a Treeview. Returns (selected_airport, remember_choice)."""

    airport_dialog = tk.Toplevel(parent)
    airport_dialog.title("Select Airport")
    airport_dialog.geometry("650x550")  # Adjusted size
    airport_dialog.transient(parent)
    airport_dialog.grab_set()

    # Center the dialog on parent
    airport_dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (650 // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (550 // 2)
    airport_dialog.geometry(f"+{x}+{y}")
    airport_dialog.resizable(False, False)

    # Dialog content
    ttk.Label(
        airport_dialog, text="Select an Airport to Manage", font=("Arial", 16, "bold")
    ).pack(pady=(20, 5))

    ttk.Label(
        airport_dialog,
        text="Choose from the available airports below:",
        font=("Arial", 10),
    ).pack(pady=(0, 20))

    # Create frame for the airport list with scrollbar
    list_frame = ttk.Frame(airport_dialog)
    list_frame.pack(fill="both", expand=True, padx=20, pady=5)

    # --- Treeview Implementation ---
    style = ttk.Style(airport_dialog)
    style.configure(
        "Treeview", rowheight=35, font=("Arial", 10), fieldbackground="#F0F0F0"
    )
    style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
    style.map("Treeview", background=[("selected", "#0078D7")])
    style.layout(
        "Treeview", [("Treeview.treearea", {"sticky": "nswe"})]
    )  # Remove borders

    tree = ttk.Treeview(
        list_frame,
        columns=("name", "icao", "runways"),
        show="headings",
        selectmode="browse",
        height=8,
    )
    tree.heading("name", text="Airport Name")
    tree.heading("icao", text="ICAO")
    tree.heading("runways", text="Runways")

    tree.column("name", width=300, anchor="w", stretch=tk.YES)
    tree.column("icao", width=80, anchor="center", stretch=tk.NO)
    tree.column("runways", width=150, anchor="w", stretch=tk.NO)

    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Add data to Treeview
    tree.tag_configure("oddrow", background="#F7F7F7")
    tree.tag_configure("evenrow", background="#FFFFFF")

    airport_map = {}  # From tree item id to airport key
    id_map = {}  # From airport key to tree item id

    for i, (airport_name, airport_obj) in enumerate(airports.items()):
        tag = "oddrow" if i % 2 != 0 else "evenrow"
        runway_list = ", ".join(airport_obj.runways)

        # Add a space for padding
        display_name = f" {airport_name}"
        display_runways = f" {runway_list}"

        item_id = tree.insert(
            "",
            "end",
            values=(display_name, airport_obj.icao, display_runways),
            tags=(tag,),
        )
        airport_map[item_id] = airport_name
        id_map[airport_name] = item_id

    # Select the last used airport if it exists, otherwise select the first item
    if last_airport and last_airport in id_map:
        item_to_select = id_map[last_airport]
        tree.selection_set(item_to_select)
        tree.see(item_to_select)
    else:
        children = tree.get_children()
        if children:
            tree.selection_set(children[0])
            tree.see(children[0])

    # Info label at the bottom
    info_text = "Double-click an airport or click 'Open Selected Airport' to start managing the airport."
    ttk.Label(
        airport_dialog,
        text=info_text,
        wraplength=460,
        justify="center",
        font=("Arial", 9),
    ).pack(pady=(15, 5))

    # Result variable to store the selected airport
    selected_airport = [None]
    remember_choice = [False]

    # Add a checkbox for remembering the choice
    remember_var = tk.BooleanVar(value=True)
    remember_checkbox = ttk.Checkbutton(
        airport_dialog,
        text="Remember my airport choice for next time",
        variable=remember_var,
    )
    remember_checkbox.pack(pady=(5, 15))

    # Button frame
    button_frame = ttk.Frame(airport_dialog)
    button_frame.pack(pady=(0, 20))

    def on_open():
        selected_item = tree.selection()
        if selected_item:
            selected_airport[0] = airport_map[selected_item[0]]
            remember_choice[0] = remember_var.get()
            airport_dialog.destroy()
        else:
            messagebox.showwarning("No Selection", "Please select an airport first.")

    def on_cancel():
        airport_dialog.destroy()

    # Create and style buttons
    open_button = ttk.Button(
        button_frame,
        text="Open Selected Airport",
        command=on_open,
        width=25,
        style="Accent.TButton",
    )
    open_button.pack(side="left", padx=10)

    cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel, width=15)
    cancel_button.pack(side="left", padx=10)

    style.configure(
        "Accent.TButton",
        font=("Arial", 10, "bold"),
        foreground="white",
        background="#0078D7",
    )

    # Bind events
    tree.bind("<Double-Button-1>", lambda e: on_open())
    tree.bind("<Return>", lambda e: on_open())

    # Focus on the listbox
    tree.focus_set()

    # Wait for the dialog to be closed
    parent.wait_window(airport_dialog)

    return selected_airport[0], remember_choice[0]


def on_role_selected(role: str, root: tk.Tk, config: Config) -> None:
    """Handle when a role is selected from the role selection screen."""
    # Save the selected role if requested
    remember_preference = config.get("remember_role_preference", False)
    if remember_preference:
        config.set("preferred_role", role)
        config.save_config()

    # Load the appropriate window
    new_app = load_appropriate_window(root, role)
    # If the user canceled airport selection for ATC role, keep the role selection screen
    # (The role selection screen will be redrawn in load_appropriate_window if canceled)


def main() -> int:
    """Main entry point for the application. Returns exit code (0 success, 1 error)."""
    setup_logging()
    # Check dependencies
    if not check_dependencies():
        return 1

    # Make sure the config directory exists
    ensure_config_directory()

    # Load the configuration
    global config
    config = Config()

    try:
        # Create the main window
        root = tk.Tk()
        root.title("Aviation Assistant")

        # Set icon
        try:
            # Create the icon directory if it doesn't exist
            if not os.path.exists("icons"):
                os.makedirs("icons")

            # Create a simple icon if one doesn't exist
            icon_path = os.path.join("icons", "icon.png")
            if not os.path.exists(icon_path):
                # Create a simple blue square icon
                img = Image.new("RGB", (64, 64), color=(65, 105, 225))
                img.save(icon_path)

            # Use the icon
            if os.name == "nt":  # Windows
                root.iconbitmap(default=icon_path)
            else:  # Linux/Mac
                img = ImageTk.PhotoImage(file=icon_path)
                root.tk.call("wm", "iconphoto", root._w, img)
        except Exception as e:
            logger.warning("Error setting icon: %s", e)
            # Continue without an icon

        # Check Ollama availability in background
        def check_ollama_on_startup():
            """Check Ollama availability after UI is loaded"""
            try:
                is_available, models = check_ollama_availability()

                if not is_available:
                    # Show notification about Ollama not being available
                    def show_ollama_notification():
                        result = messagebox.askyesno(
                            "AI Features Not Available",
                            "Ollama AI integration is not available.\n\n"
                            "This means AI-powered ATC responses will use fallback mode.\n\n"
                            "Would you like to see setup instructions for Ollama?",
                        )
                        if result:
                            show_ollama_status_dialog(root)

                    # Schedule the notification to show after the main window is ready
                    root.after(1000, show_ollama_notification)

            except Exception as e:
                logger.warning("Error checking Ollama availability: %s", e)

        # Check if there's a saved role preference
        saved_role = config.get("preferred_role")
        if saved_role and config.get("skip_role_selection", False):
            # If there's a saved role and skip_role_selection is True, load the appropriate window
            app = load_appropriate_window(root, saved_role)
        else:
            # Show the role selection screen
            app = RoleSelectionScreen(
                root, lambda role: on_role_selected(role, root, config)
            )

        # Check Ollama availability after UI is loaded
        root.after(100, check_ollama_on_startup)

        # Run the application
        root.mainloop()
    except Exception as e:
        error_message = (
            f"An unexpected error occurred:\n{str(e)}\n\n{traceback.format_exc()}"
        )
        logger.exception("Unexpected error in main")
        messagebox.showerror("Error", error_message)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
