"""
Aviation Operations Assistant
A tool for both pilots and air traffic controllers to assist with aviation communications and operations.

This is the main entry point for the application.
"""
import os
import sys
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import traceback

from views.role_selection import RoleSelectionScreen
from views.main_window import MainWindow
from views.atc_window import ATCWindow
from utils.config import ensure_config_directory, Config
from models.atc_model import ATCModel

def check_dependencies():
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
            "pip install -r requirements.txt"
        )
        return False

def load_appropriate_window(root, role):
    """Load the appropriate window based on selected role"""
    # First destroy any existing widgets
    for widget in root.winfo_children():
        widget.destroy()
    
    # Then reconfigure the window with a new title
    if role == "pilot":
        root.title("Pilot ATC Assistant")
        app = MainWindow(root)
        return app
    elif role == "atc":
        root.title("ATC Operations Assistant")
        
        # Create an ATC model with default airports
        atc_model = ATCModel()
        
        # Print debugging information about the model
        print(f"Created ATCModel with {len(atc_model.airports)} airports:")
        for airport_name, airport_data in atc_model.airports.items():
            print(f"  - {airport_name} (runways: {', '.join(airport_data.runways)})")
        
        # Create a dictionary of airport data from the AirportConfiguration objects
        airports_dict = {}
        for name, airport_obj in atc_model.airports.items():
            # Convert AirportConfiguration to dict
            airports_dict[name] = airport_obj.to_dict()
        
        # Show airport selection dialog
        last_airport = config.get("last_airport")
        selected_airport = show_airport_selection_dialog(root, atc_model.airports, last_airport)
        if not selected_airport:  # User canceled the selection
            # Show role selection again
            RoleSelectionScreen(root, lambda r: on_role_selected(r, root, config))
            return None
        
        # Remember the selected airport for next time
        config.set("last_airport", selected_airport)
        config.save_config()
        
        # Set the current airport in the dictionary
        for airport_name in airports_dict:
            if airport_name == selected_airport:
                # This is the selected airport - nothing specific to set here
                pass
        
        # Pass the config and converted airport data to the ATCWindow
        app = ATCWindow(root, config, airports_dict)
        
        # Set the current airport after initialization
        app.current_airport = selected_airport
        app.update_airport_config()
        
        return app
    else:
        messagebox.showerror("Error", f"Unknown role: {role}")
        return None

def show_airport_selection_dialog(parent, airports, last_airport=None):
    """Show a dialog for the user to select an airport"""
    airport_dialog = tk.Toplevel(parent)
    airport_dialog.title("Select Airport")
    airport_dialog.geometry("400x450")
    airport_dialog.transient(parent)  # Make dialog modal
    airport_dialog.grab_set()
    
    # Center the dialog on parent
    airport_dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (450 // 2)
    airport_dialog.geometry(f"+{x}+{y}")
    
    # Dialog content
    tk.Label(
        airport_dialog, 
        text="Select an airport to manage:",
        font=("Arial", 12, "bold")
    ).pack(pady=(20, 10))
    
    # Create frame for the airport list with scrollbar
    list_frame = tk.Frame(airport_dialog)
    list_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")
    
    airport_listbox = tk.Listbox(
        list_frame,
        height=15,
        width=40,
        selectmode="single",
        font=("Arial", 10),
        yscrollcommand=scrollbar.set
    )
    airport_listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=airport_listbox.yview)
    
    # Add airports to the listbox with details
    airport_index_map = {}  # Map airport names to listbox indices
    for idx, (airport_name, airport_obj) in enumerate(airports.items()):
        icao = airport_obj.icao
        num_runways = len(airport_obj.runways)
        display_text = f"{airport_name} ({num_runways} runways)"
        airport_listbox.insert("end", display_text)
        airport_index_map[airport_name] = idx
    
    # Select the last used airport if it exists, otherwise select first item
    if last_airport and last_airport in airport_index_map:
        airport_listbox.selection_set(airport_index_map[last_airport])
        airport_listbox.see(airport_index_map[last_airport])  # Scroll to show the selection
    elif airport_listbox.size() > 0:
        airport_listbox.selection_set(0)
    
    # Info label at the bottom
    info_text = "Select an airport from the list and click 'Open' to start managing the airport."
    tk.Label(
        airport_dialog,
        text=info_text,
        wraplength=360,
        justify="center"
    ).pack(pady=(0, 10))
    
    # Result variable to store the selected airport
    selected_airport = [None]  # Using a list as a container to modify from inner function
    
    # Button frame
    button_frame = tk.Frame(airport_dialog)
    button_frame.pack(pady=(0, 20))
    
    def on_open():
        selected_idx = airport_listbox.curselection()
        if selected_idx:
            # Get the display text and extract the airport name
            display_text = airport_listbox.get(selected_idx[0])
            selected_name = display_text.split(" (")[0]  # Extract airport name without runway count
            selected_airport[0] = selected_name
            airport_dialog.destroy()
            
    def on_cancel():
        airport_dialog.destroy()
    
    tk.Button(
        button_frame, 
        text="Open Selected Airport",
        command=on_open,
        width=20,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 10, "bold")
    ).pack(side="left", padx=5)
    
    tk.Button(
        button_frame, 
        text="Cancel",
        command=on_cancel,
        width=10
    ).pack(side="left", padx=5)
    
    # Double-click to select
    airport_listbox.bind("<Double-Button-1>", lambda e: on_open())
    
    # Wait for the dialog to be closed
    parent.wait_window(airport_dialog)
    
    return selected_airport[0]

def on_role_selected(role, root, config):
    """Handle when a role is selected from the role selection screen"""
    # Save the selected role if requested
    remember_preference = config.get("remember_role_preference", False)
    if remember_preference:
        config.set("preferred_role", role)
        config.save_config()
    
    # Load the appropriate window
    new_app = load_appropriate_window(root, role)
    # If the user canceled airport selection for ATC role, keep the role selection screen
    # (The role selection screen will be redrawn in load_appropriate_window if canceled)

def main():
    """Main entry point for the application"""
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
                img = Image.new('RGB', (64, 64), color=(65, 105, 225))
                img.save(icon_path)
            
            # Use the icon
            if os.name == 'nt':  # Windows
                root.iconbitmap(default=icon_path)
            else:  # Linux/Mac
                img = ImageTk.PhotoImage(file=icon_path)
                root.tk.call('wm', 'iconphoto', root._w, img)
        except Exception as e:
            print(f"Error setting icon: {e}")
            # Continue without an icon
        
        # Check if there's a saved role preference
        saved_role = config.get("preferred_role")
        if saved_role and config.get("skip_role_selection", False):
            # If there's a saved role and skip_role_selection is True, load the appropriate window
            app = load_appropriate_window(root, saved_role)
        else:
            # Show the role selection screen
            app = RoleSelectionScreen(root, lambda role: on_role_selected(role, root, config))
        
        # Run the application
        root.mainloop()
    except Exception as e:
        error_message = f"An unexpected error occurred:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_message)
        messagebox.showerror("Error", error_message)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 