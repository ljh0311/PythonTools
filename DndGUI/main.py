import customtkinter as ctk
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.character_sheet import CharacterSheetFrame
from tools.dice_roller import DiceRollerFrame
from tools.spell_database import SpellDatabaseFrame
from tools.initiative_tracker import InitiativeTrackerFrame
from tools.monster_manual import MonsterManualFrame
from tools.campaign_notes import CampaignNotesFrame
from tools.game_flow import GameFlowFrame


class DndToolsApp:
    def __init__(self):
        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("D&D Tools Collection - Your Digital Gaming Companion")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        
        # Configure grid for better layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        self.setup_ui()
        self.setup_keyboard_shortcuts()

    def setup_ui(self):
        # Header with title and status
        header_frame = ctk.CTkFrame(self.root, height=80)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Title with gaming theme
        title_label = ctk.CTkLabel(
            header_frame,
            text="⚔️ D&D Tools Collection ⚔️",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#ffd700"
        )
        title_label.grid(row=0, column=0, padx=20, pady=20)
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Your Digital Gaming Companion",
            font=ctk.CTkFont(size=14),
            text_color="#cccccc"
        )
        subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Status indicator
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="Ready for Adventure!",
            font=ctk.CTkFont(size=12),
            text_color="#4caf50"
        )
        self.status_label.grid(row=0, column=2, padx=20, pady=20, sticky="e")

        # Create tabview for better organization
        self.tabview = ctk.CTkTabview(self.root, width=1360, height=750)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))

        # Add tabs to tabview with gaming-themed icons
        self.tabview.add("🎯 Game Flow")
        self.tabview.add("🎲 Dice Roller")
        self.tabview.add("📜 Character Sheet")
        self.tabview.add("📚 Spell Database")
        self.tabview.add("⚔️ Initiative Tracker")
        self.tabview.add("🐉 Monster Manual")
        self.tabview.add("📝 Campaign Notes")

        # Create tool frames and add them to tabs
        self.game_flow_frame = GameFlowFrame(self.tabview.tab("🎯 Game Flow"))
        self.game_flow_frame.pack(fill="both", expand=True)
        
        self.dice_roller_frame = DiceRollerFrame(self.tabview.tab("🎲 Dice Roller"))
        self.dice_roller_frame.pack(fill="both", expand=True)
        
        self.character_sheet_frame = CharacterSheetFrame(self.tabview.tab("📜 Character Sheet"))
        self.character_sheet_frame.pack(fill="both", expand=True)
        
        self.spell_database_frame = SpellDatabaseFrame(self.tabview.tab("📚 Spell Database"))
        self.spell_database_frame.pack(fill="both", expand=True)
        
        self.initiative_tracker_frame = InitiativeTrackerFrame(self.tabview.tab("⚔️ Initiative Tracker"))
        self.initiative_tracker_frame.pack(fill="both", expand=True)
        
        self.monster_manual_frame = MonsterManualFrame(self.tabview.tab("🐉 Monster Manual"))
        self.monster_manual_frame.pack(fill="both", expand=True)
        
        self.campaign_notes_frame = CampaignNotesFrame(self.tabview.tab("📝 Campaign Notes"))
        self.campaign_notes_frame.pack(fill="both", expand=True)

        # Bottom control panel
        control_frame = ctk.CTkFrame(self.root, height=60)
        control_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        control_frame.grid_columnconfigure(1, weight=1)
        
        # Quick actions
        quick_actions_label = ctk.CTkLabel(
            control_frame,
            text="Quick Actions:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffd700"
        )
        quick_actions_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Quick action buttons
        ctk.CTkButton(
            control_frame,
            text="🎲 Quick Roll (Ctrl+R)",
            command=self.quick_roll,
            width=150,
            height=35,
            fg_color="#4caf50",
            hover_color="#388e3c"
        ).grid(row=0, column=1, padx=5, pady=20)
        
        ctk.CTkButton(
            control_frame,
            text="⚔️ Next Turn (Ctrl+N)",
            command=self.next_turn,
            width=150,
            height=35,
            fg_color="#2196f3",
            hover_color="#1565c0"
        ).grid(row=0, column=2, padx=5, pady=20)
        
        ctk.CTkButton(
            control_frame,
            text="📚 Search Spells (Ctrl+S)",
            command=self.search_spells,
            width=150,
            height=35,
            fg_color="#ff9800",
            hover_color="#e68900"
        ).grid(row=0, column=3, padx=5, pady=20)
        
        # Exit button
        exit_btn = ctk.CTkButton(
            control_frame,
            text="Exit (Ctrl+Q)",
            command=self.root.quit,
            width=120,
            height=35,
            fg_color="#f44336",
            hover_color="#d32f2f"
        )
        exit_btn.grid(row=0, column=4, padx=20, pady=20, sticky="e")

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for quick access"""
        self.root.bind('<Control-r>', lambda e: self.quick_roll())
        self.root.bind('<Control-n>', lambda e: self.next_turn())
        self.root.bind('<Control-s>', lambda e: self.search_spells())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        
        # Tab switching shortcuts
        self.root.bind('<Control-1>', lambda e: self.tabview.set("🎯 Game Flow"))
        self.root.bind('<Control-2>', lambda e: self.tabview.set("🎲 Dice Roller"))
        self.root.bind('<Control-3>', lambda e: self.tabview.set("📜 Character Sheet"))
        self.root.bind('<Control-4>', lambda e: self.tabview.set("📚 Spell Database"))
        self.root.bind('<Control-5>', lambda e: self.tabview.set("⚔️ Initiative Tracker"))
        self.root.bind('<Control-6>', lambda e: self.tabview.set("🐉 Monster Manual"))
        self.root.bind('<Control-7>', lambda e: self.tabview.set("📝 Campaign Notes"))

    def quick_roll(self):
        """Quick access to dice roller"""
        self.tabview.set("🎲 Dice Roller")
        self.update_status("Dice roller activated - Ready to roll!")
        
    def next_turn(self):
        """Quick access to initiative tracker next turn"""
        self.tabview.set("⚔️ Initiative Tracker")
        if hasattr(self.initiative_tracker_frame, 'next_turn'):
            self.initiative_tracker_frame.next_turn()
        self.update_status("Initiative tracker - Next turn!")
        
    def search_spells(self):
        """Quick access to spell database"""
        self.tabview.set("📚 Spell Database")
        self.update_status("Spell database - Ready to search!")

    def update_status(self, message):
        """Update the status label with a message"""
        self.status_label.configure(text=message)
        # Clear the message after 3 seconds
        self.root.after(3000, lambda: self.status_label.configure(text="Ready for Adventure!"))

    def run(self):
        self.root.mainloop()


def main():
    app = DndToolsApp()
    app.run()


if __name__ == "__main__":
    main()
