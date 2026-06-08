import customtkinter as ctk
from tkinter import messagebox
import random
import tkinter as tk

class InitiativeTrackerFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.combatants = []
        self.current_turn = 0
        self.round_number = 1
        self.combat_active = False
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="⚔️ Initiative Tracker",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ffd700"
        )
        title_label.pack(pady=20)
        
        # Turn guidance
        guidance_label = ctk.CTkLabel(
            self,
            text="🎯 Turn Guide: Add combatants → Roll initiative → Start combat → Use 'Next Turn' to advance",
            font=ctk.CTkFont(size=12),
            text_color="#4caf50"
        )
        guidance_label.pack(pady=(0, 10))
        
        # Combat status frame
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        # Round counter
        self.round_label = ctk.CTkLabel(
            status_frame,
            text="Round: 1",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4caf50"
        )
        self.round_label.pack(side="left", padx=20, pady=10)
        
        # Combat status
        self.combat_status_label = ctk.CTkLabel(
            status_frame,
            text="Combat: Inactive",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ff6b6b"
        )
        self.combat_status_label.pack(side="right", padx=20, pady=10)
        
        # Add combatant frame
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(add_frame, text="Add Combatant", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Input fields
        input_frame = ctk.CTkFrame(add_frame)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Name entry
        ctk.CTkLabel(input_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.name_entry = ctk.CTkEntry(input_frame, width=150)
        self.name_entry.grid(row=0, column=1, padx=(10, 20), pady=5)
        
        # Initiative entry
        ctk.CTkLabel(input_frame, text="Initiative:").grid(row=0, column=2, sticky="w", padx=10, pady=5)
        self.initiative_entry = ctk.CTkEntry(input_frame, width=80)
        self.initiative_entry.grid(row=0, column=3, padx=(10, 20), pady=5)
        
        # HP entry
        ctk.CTkLabel(input_frame, text="Max HP:").grid(row=0, column=4, sticky="w", padx=10, pady=5)
        self.hp_entry = ctk.CTkEntry(input_frame, width=80)
        self.hp_entry.grid(row=0, column=5, padx=(10, 0), pady=5)
        
        # AC entry
        ctk.CTkLabel(input_frame, text="AC:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.ac_entry = ctk.CTkEntry(input_frame, width=80)
        self.ac_entry.grid(row=1, column=1, padx=(10, 20), pady=5)
        
        # Type selection
        ctk.CTkLabel(input_frame, text="Type:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
        self.type_var = ctk.StringVar(value="PC")
        type_menu = ctk.CTkOptionMenu(
            input_frame,
            values=["PC", "NPC", "Enemy"],
            variable=self.type_var,
            width=80
        )
        type_menu.grid(row=1, column=3, padx=(10, 20), pady=5)
        
        # Add button
        add_btn = ctk.CTkButton(
            input_frame, 
            text="Add Combatant", 
            command=self.add_combatant,
            fg_color="#4caf50",
            hover_color="#388e3c"
        )
        add_btn.grid(row=2, column=0, columnspan=6, pady=(10, 0))
        
        # Combat controls frame
        controls_frame = ctk.CTkFrame(self)
        controls_frame.pack(fill="x", padx=20, pady=10)
        
        # Control buttons
        ctk.CTkButton(
            controls_frame, 
            text="🎲 Roll Initiative", 
            command=self.roll_initiative,
            fg_color="#2196f3",
            hover_color="#1565c0"
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            controls_frame, 
            text="⏭️ Next Turn", 
            command=self.next_turn,
            fg_color="#ff9800",
            hover_color="#e68900"
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            controls_frame, 
            text="🔄 New Round", 
            command=self.new_round,
            fg_color="#9c27b0",
            hover_color="#7b1fa2"
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            controls_frame, 
            text="🗑️ Clear All", 
            command=self.clear_combatants,
            fg_color="#f44336",
            hover_color="#d32f2f"
        ).pack(side="left")
        
        # Initiative order frame
        order_frame = ctk.CTkFrame(self)
        order_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(order_frame, text="Initiative Order", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Initiative listbox with better formatting
        self.initiative_listbox = tk.Listbox(
            order_frame,
            bg='#2b2b2b',
            fg='#ffffff',
            selectbackground='#404040',
            font=('Consolas', 12),
            height=12
        )
        self.initiative_listbox.pack(side="left", fill="both", expand=True, padx=10, pady=(0, 10))
        self.initiative_listbox.bind('<Double-Button-1>', self.edit_combatant)
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(order_frame, command=self.initiative_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.initiative_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Current turn indicator
        self.turn_label = ctk.CTkLabel(
            self,
            text="No combat started",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ff6b6b"
        )
        self.turn_label.pack(pady=10)
        
        # Turn action guide
        self.turn_guide_label = ctk.CTkLabel(
            self,
            text="💡 On your turn: Move → Action → Bonus Action → Free Action → End Turn",
            font=ctk.CTkFont(size=12),
            text_color="#4caf50"
        )
        self.turn_guide_label.pack(pady=(0, 10))
        
        # Bind Enter key to add combatant
        self.name_entry.bind('<Return>', lambda e: self.add_combatant())
        self.initiative_entry.bind('<Return>', lambda e: self.add_combatant())
        self.hp_entry.bind('<Return>', lambda e: self.add_combatant())
        
    def add_combatant(self):
        name = self.name_entry.get().strip()
        initiative = self.initiative_entry.get().strip()
        hp = self.hp_entry.get().strip()
        ac = self.ac_entry.get().strip()
        
        if not name:
            messagebox.showwarning("Warning", "Please enter a name")
            return
        
        if not initiative:
            messagebox.showwarning("Warning", "Please enter initiative")
            return
        
        try:
            initiative = int(initiative)
            hp = int(hp) if hp else 0
            ac = int(ac) if ac else 10
        except ValueError:
            messagebox.showerror("Error", "Initiative, HP, and AC must be numbers")
            return
        
        combatant = {
            'name': name,
            'initiative': initiative,
            'hp': hp,
            'current_hp': hp,
            'ac': ac,
            'type': self.type_var.get(),
            'conditions': []
        }
        
        self.combatants.append(combatant)
        self.clear_entries()
        self.update_initiative_list()
        
    def clear_entries(self):
        self.name_entry.delete(0, "end")
        self.initiative_entry.delete(0, "end")
        self.hp_entry.delete(0, "end")
        self.ac_entry.delete(0, "end")
        self.name_entry.focus()
        
    def roll_initiative(self):
        if not self.combatants:
            messagebox.showwarning("Warning", "No combatants added")
            return
        
        # Sort by initiative (highest first)
        self.combatants.sort(key=lambda x: x['initiative'], reverse=True)
        self.current_turn = 0
        self.round_number = 1
        self.combat_active = True
        self.update_initiative_list()
        self.update_turn_indicator()
        self.update_combat_status()
        
    def next_turn(self):
        if not self.combatants or not self.combat_active:
            return
        
        self.current_turn = (self.current_turn + 1) % len(self.combatants)
        
        # Check if we've completed a round
        if self.current_turn == 0:
            self.round_number += 1
        
        self.update_initiative_list()
        self.update_turn_indicator()
        self.update_combat_status()
        
    def new_round(self):
        if not self.combatants:
            return
        
        self.round_number += 1
        self.update_combat_status()
        messagebox.showinfo("New Round", f"Round {self.round_number} begins!")
        
    def clear_combatants(self):
        if messagebox.askyesno("Confirm", "Clear all combatants?"):
            self.combatants = []
            self.current_turn = 0
            self.round_number = 1
            self.combat_active = False
            self.update_initiative_list()
            self.turn_label.configure(text="No combat started")
            self.update_combat_status()
            
    def edit_combatant(self, event):
        """Edit combatant HP and conditions"""
        selection = self.initiative_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        combatant = self.combatants[idx]
        
        # Create edit dialog
        edit_window = ctk.CTkToplevel(self)
        edit_window.title(f"Edit {combatant['name']}")
        edit_window.geometry("400x300")
        edit_window.resizable(False, False)
        
        # HP adjustment
        ctk.CTkLabel(edit_window, text="Current HP:").pack(pady=5)
        hp_entry = ctk.CTkEntry(edit_window, width=100)
        hp_entry.pack(pady=5)
        hp_entry.insert(0, str(combatant['current_hp']))
        
        # Quick HP buttons
        hp_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        hp_frame.pack(pady=10)
        
        ctk.CTkButton(
            hp_frame,
            text="-5",
            command=lambda: self.adjust_hp(hp_entry, -5),
            width=50
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            hp_frame,
            text="-1",
            command=lambda: self.adjust_hp(hp_entry, -1),
            width=50
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            hp_frame,
            text="+1",
            command=lambda: self.adjust_hp(hp_entry, 1),
            width=50
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            hp_frame,
            text="+5",
            command=lambda: self.adjust_hp(hp_entry, 5),
            width=50
        ).pack(side="left", padx=5)
        
        # Conditions
        ctk.CTkLabel(edit_window, text="Conditions:").pack(pady=5)
        conditions_entry = ctk.CTkEntry(edit_window, width=200)
        conditions_entry.pack(pady=5)
        conditions_entry.insert(0, ", ".join(combatant['conditions']))
        
        # Save button
        def save_changes():
            try:
                new_hp = int(hp_entry.get())
                new_conditions = [c.strip() for c in conditions_entry.get().split(",") if c.strip()]
                
                combatant['current_hp'] = max(0, new_hp)  # HP can't go below 0
                combatant['conditions'] = new_conditions
                
                self.update_initiative_list()
                edit_window.destroy()
                
            except ValueError:
                messagebox.showerror("Error", "HP must be a number")
        
        ctk.CTkButton(
            edit_window,
            text="Save Changes",
            command=save_changes,
            fg_color="#4caf50",
            hover_color="#388e3c"
        ).pack(pady=20)
        
    def adjust_hp(self, hp_entry, amount):
        """Adjust HP by the given amount"""
        try:
            current = int(hp_entry.get())
            new_hp = max(0, current + amount)
            hp_entry.delete(0, "end")
            hp_entry.insert(0, str(new_hp))
        except ValueError:
            pass
            
    def update_initiative_list(self):
        self.initiative_listbox.delete(0, "end")
        
        for i, combatant in enumerate(self.combatants):
            turn_indicator = " → " if i == self.current_turn else "   "
            type_icon = {"PC": "👤", "NPC": "🤝", "Enemy": "👹"}.get(combatant['type'], "❓")
            
            # Format the display line
            display_text = f"{turn_indicator}{type_icon} {combatant['name']}"
            display_text += f" (Initiative: {combatant['initiative']}, HP: {combatant['current_hp']}/{combatant['hp']}, AC: {combatant['ac']})"
            
            # Add conditions if any
            if combatant['conditions']:
                display_text += f" [{', '.join(combatant['conditions'])}]"
            
            self.initiative_listbox.insert("end", display_text)
            
            # Highlight current turn
            if i == self.current_turn:
                self.initiative_listbox.itemconfig("end", bg='#404040')
                
    def update_turn_indicator(self):
        if self.combatants and self.combat_active:
            current = self.combatants[self.current_turn]
            self.turn_label.configure(text=f"Current Turn: {current['name']} (Round {self.round_number})")
        else:
            self.turn_label.configure(text="No combat started")
            
    def update_combat_status(self):
        if self.combat_active:
            self.combat_status_label.configure(text=f"Combat: Active (Round {self.round_number})", text_color="#4caf50")
        else:
            self.combat_status_label.configure(text="Combat: Inactive", text_color="#ff6b6b")


# Keep the original class for backward compatibility
class InitiativeTrackerApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("D&D Initiative Tracker")
        self.root.geometry("800x450")
        
        self.frame = InitiativeTrackerFrame(self.root)
        self.frame.pack(fill='both', expand=True)
