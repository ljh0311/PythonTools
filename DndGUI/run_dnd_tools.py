#!/usr/bin/env python3
"""
D&D Tools Launcher
A simple launcher for the D&D tools collection
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    root = tk.Tk()
    root.title("D&D Tools Collection")
    root.geometry("500x400")
    root.configure(bg='#2b2b2b')
    
    # Title
    title_label = ttk.Label(
        root,
        text="🎲 D&D Tools Collection",
        font=('Arial', 18, 'bold'),
        foreground='#ffd700',
        background='#2b2b2b'
    )
    title_label.pack(pady=30)
    
    # Description
    desc_label = ttk.Label(
        root,
        text="Choose a tool to launch:",
        font=('Arial', 12),
        foreground='#ffffff',
        background='#2b2b2b'
    )
    desc_label.pack(pady=10)
    
    # Tools frame
    tools_frame = ttk.Frame(root)
    tools_frame.pack(pady=20, padx=20, fill='both', expand=True)
    
    def open_dice_roller():
        try:
            from tools.dice_roller import DiceRollerApp
            app = DiceRollerApp()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Dice Roller: {str(e)}")
    
    def open_spell_database():
        try:
            from tools.spell_database import SpellDatabaseApp
            app = SpellDatabaseApp()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Spell Database: {str(e)}")
    
    def open_initiative_tracker():
        try:
            from tools.initiative_tracker import InitiativeTrackerApp
            app = InitiativeTrackerApp()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Initiative Tracker: {str(e)}")
    
    def open_monster_manual():
        try:
            from tools.monster_manual import MonsterManualApp
            app = MonsterManualApp()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Monster Manual: {str(e)}")
    
    def open_campaign_notes():
        try:
            from tools.campaign_notes import CampaignNotesApp
            app = CampaignNotesApp()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Campaign Notes: {str(e)}")
    
    # Tool buttons
    tools = [
        ("🎲 Dice Roller", open_dice_roller, "Roll dice with modifiers"),
        ("📚 Spell Database", open_spell_database, "Look up spells and details"),
        ("⚔️ Initiative Tracker", open_initiative_tracker, "Track combat initiative"),
        ("🐉 Monster Manual", open_monster_manual, "Quick monster reference"),
        ("📝 Campaign Notes", open_campaign_notes, "Organize campaign information")
    ]
    
    for name, command, description in tools:
        btn_frame = ttk.Frame(tools_frame)
        btn_frame.pack(fill='x', pady=5)
        
        btn = ttk.Button(
            btn_frame,
            text=name,
            command=command,
            style='Tool.TButton'
        )
        btn.pack(side='left', padx=(0, 10))
        
        desc = ttk.Label(
            btn_frame,
            text=description,
            font=('Arial', 9),
            foreground='#cccccc',
            background='#2b2b2b'
        )
        desc.pack(side='left')
    
    # Exit button
    exit_btn = ttk.Button(
        root,
        text="Exit",
        command=root.quit
    )
    exit_btn.pack(pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    main()
