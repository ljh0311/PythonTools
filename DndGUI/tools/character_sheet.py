import customtkinter as ctk
from tkinter import messagebox
import json
import os
import tkinter as tk


class CharacterSheetFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.characters = []
        self.current_character = None
        self.selected_index = None
        self.load_characters()
        self.setup_ui()

    def setup_ui(self):
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="📜 Character Sheet",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#ffd700"
        )
        title_label.pack(pady=(18, 5))
        
        # Character guidance
        guidance_label = ctk.CTkLabel(
            self,
            text="💡 Tip: Import from PDF or create new character → Select character → Update stats as needed",
            font=ctk.CTkFont(size=12),
            text_color="#4caf50"
        )
        guidance_label.pack(pady=(0, 10))

        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=18, pady=10)

        # Left panel - Character list
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side="left", fill="y", padx=(0, 12), pady=2)

        # Character list title
        ctk.CTkLabel(left_frame, text="Characters", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        # Use a Listbox for selectable character list
        import tkinter as tk  # Needed for Listbox
        self.tk_listbox = tk.Listbox(
            left_frame, width=25, height=15, exportselection=False, font=("Segoe UI", 11)
        )
        self.tk_listbox.pack(fill="both", expand=True, pady=(0, 10), padx=4)
        self.tk_listbox.bind("<<ListboxSelect>>", self.on_character_select)

        # Character buttons
        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10), padx=4)
        ctk.CTkButton(btn_frame, text="New Character", command=self.new_character, fg_color="#4caf50", hover_color="#388e3c").pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Import from PDF", command=self.import_character_wizard, fg_color="#ff9800", hover_color="#e68900").pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Delete", command=self.delete_character, fg_color="#f44336", hover_color="#b71c1c").pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Save", command=self.save_character, fg_color="#2196f3", hover_color="#1565c0").pack(fill="x", pady=2)

        # Right panel - Character details
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(0, 4))

        # Basic info
        basic_frame = ctk.CTkFrame(right_frame)
        basic_frame.pack(fill="x", pady=(0, 10), padx=10)

        # Name and Class
        ctk.CTkLabel(basic_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=8, pady=5)
        self.name_entry = ctk.CTkEntry(basic_frame, width=150)
        self.name_entry.grid(row=0, column=1, padx=(6, 18), pady=5)

        ctk.CTkLabel(basic_frame, text="Class:").grid(row=0, column=2, sticky="w", padx=8, pady=5)
        self.class_entry = ctk.CTkEntry(basic_frame, width=120)
        self.class_entry.grid(row=0, column=3, padx=(6, 0), pady=5)

        # Level and Race
        ctk.CTkLabel(basic_frame, text="Level:").grid(row=1, column=0, sticky="w", padx=8, pady=5)
        self.level_entry = ctk.CTkEntry(basic_frame, width=80)
        self.level_entry.grid(row=1, column=1, padx=(6, 18), pady=5)

        ctk.CTkLabel(basic_frame, text="Race:").grid(row=1, column=2, sticky="w", padx=8, pady=5)
        self.race_entry = ctk.CTkEntry(basic_frame, width=120)
        self.race_entry.grid(row=1, column=3, padx=(6, 0), pady=5)

        # Ability scores
        stats_frame = ctk.CTkFrame(right_frame)
        stats_frame.pack(fill="x", pady=(0, 10), padx=10)

        ctk.CTkLabel(stats_frame, text="Ability Scores", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        abilities = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
        self.ability_entries = {}

        abilities_frame = ctk.CTkFrame(stats_frame)
        abilities_frame.pack(fill="x", padx=10, pady=5)

        for i, ability in enumerate(abilities):
            row = i // 3
            col = i % 3

            ability_frame = ctk.CTkFrame(abilities_frame, fg_color="#222831")
            ability_frame.grid(row=row, column=col, padx=8, pady=5, sticky="ew")

            ctk.CTkLabel(ability_frame, text=f"{ability}:", font=ctk.CTkFont(weight="bold")).pack()
            entry = ctk.CTkEntry(ability_frame, width=60, justify="center")
            entry.pack(pady=2)
            self.ability_entries[ability] = entry

        # Combat stats
        combat_frame = ctk.CTkFrame(right_frame)
        combat_frame.pack(fill="x", pady=(0, 10), padx=10)

        ctk.CTkLabel(combat_frame, text="Combat", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        combat_stats_frame = ctk.CTkFrame(combat_frame)
        combat_stats_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(combat_stats_frame, text="HP:").grid(row=0, column=0, sticky="w", padx=8, pady=5)
        self.hp_entry = ctk.CTkEntry(combat_stats_frame, width=80, justify="center")
        self.hp_entry.grid(row=0, column=1, padx=(6, 18), pady=5)

        ctk.CTkLabel(combat_stats_frame, text="AC:").grid(row=0, column=2, sticky="w", padx=8, pady=5)
        self.ac_entry = ctk.CTkEntry(combat_stats_frame, width=80, justify="center")
        self.ac_entry.grid(row=0, column=3, padx=(6, 18), pady=5)

        ctk.CTkLabel(combat_stats_frame, text="Initiative:").grid(row=0, column=4, sticky="w", padx=8, pady=5)
        self.initiative_entry = ctk.CTkEntry(combat_stats_frame, width=80, justify="center")
        self.initiative_entry.grid(row=0, column=5, padx=(6, 0), pady=5)

        # Notes
        notes_frame = ctk.CTkFrame(right_frame)
        notes_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(notes_frame, text="Notes", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        self.notes_text = ctk.CTkTextbox(
            notes_frame,
            height=120,
            font=ctk.CTkFont(size=12)
        )
        self.notes_text.pack(fill="both", expand=True, padx=10, pady=5)

        self.refresh_character_list()
        self.clear_character_data()

    def import_character_wizard(self):
        """Wizard to help import character from PDF"""
        wizard = CharacterImportWizard(self)
        wizard.grab_set()  # Make the wizard modal

    def load_characters(self):
        try:
            if os.path.exists('characters.json'):
                with open('characters.json', 'r') as f:
                    self.characters = json.load(f)
        except Exception as e:
            self.characters = []
            messagebox.showerror("Error", f"Failed to load characters: {str(e)}")

    def save_characters(self):
        try:
            with open('characters.json', 'w') as f:
                json.dump(self.characters, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def refresh_character_list(self):
        self.tk_listbox.delete(0, "end")
        for char in self.characters:
            name = char.get('name', 'Unnamed')
            char_class = char.get('class', '')
            level = char.get('level', '')
            display = f"{name} ({char_class}, Lv{level})" if char_class else f"{name} (Lv{level})"
            self.tk_listbox.insert("end", display)
        # Reselect the current character if possible
        if self.selected_index is not None and 0 <= self.selected_index < len(self.characters):
            self.tk_listbox.select_set(self.selected_index)
        else:
            self.tk_listbox.selection_clear(0, "end")

    def new_character(self):
        new_char = {
            'name': '', 'class': '', 'level': 1, 'race': '',
            'abilities': {'STR': 10, 'DEX': 10, 'CON': 10, 'INT': 10, 'WIS': 10, 'CHA': 10},
            'hp': 0, 'ac': 10, 'initiative': 0, 'notes': ''
        }
        self.characters.append(new_char)
        self.selected_index = len(self.characters) - 1
        self.current_character = new_char
        self.refresh_character_list()
        self.tk_listbox.select_set(self.selected_index)
        self.load_character_data()

    def delete_character(self):
        # Get selected character from listbox
        selection = self.tk_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "No character selected")
            return
        idx = selection[0]
        char_name = self.characters[idx].get('name', 'Unnamed')
        if messagebox.askyesno("Confirm", f"Delete character '{char_name}'?"):
            del self.characters[idx]
            self.selected_index = None
            self.current_character = None
            self.refresh_character_list()
            self.clear_character_data()
            self.save_characters()

    def save_character(self):
        if self.selected_index is None or not (0 <= self.selected_index < len(self.characters)):
            messagebox.showwarning("Warning", "No character selected")
            return

        # Validate and get data from UI
        try:
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showwarning("Validation", "Name cannot be empty.")
                return
            char_class = self.class_entry.get().strip()
            level = int(self.level_entry.get() or 1)
            race = self.race_entry.get().strip()
            abilities = {}
            for ability, entry in self.ability_entries.items():
                val = entry.get()
                if not val.isdigit():
                    messagebox.showwarning("Validation", f"{ability} must be a number.")
                    return
                abilities[ability] = int(val)
            hp = int(self.hp_entry.get() or 0)
            ac = int(self.ac_entry.get() or 10)
            initiative = int(self.initiative_entry.get() or 0)
            notes = self.notes_text.get("0.0", "end").strip()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
            return

        char = self.characters[self.selected_index]
        char['name'] = name
        char['class'] = char_class
        char['level'] = level
        char['race'] = race
        char['abilities'] = abilities
        char['hp'] = hp
        char['ac'] = ac
        char['initiative'] = initiative
        char['notes'] = notes

        self.current_character = char
        self.save_characters()
        self.refresh_character_list()
        messagebox.showinfo("Success", "Character saved!")

    def on_character_select(self, event):
        selection = self.tk_listbox.curselection()
        if not selection:
            self.selected_index = None
            self.current_character = None
            self.clear_character_data()
            return
        idx = selection[0]
        self.selected_index = idx
        self.current_character = self.characters[idx]
        self.load_character_data()

    def load_character_data(self):
        if not self.current_character:
            self.clear_character_data()
            return

        char = self.current_character

        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, char.get('name', ''))

        self.class_entry.delete(0, "end")
        self.class_entry.insert(0, char.get('class', ''))

        self.level_entry.delete(0, "end")
        self.level_entry.insert(0, str(char.get('level', 1)))

        self.race_entry.delete(0, "end")
        self.race_entry.insert(0, char.get('race', ''))

        abilities = char.get('abilities', {})
        for ability, entry in self.ability_entries.items():
            entry.delete(0, "end")
            entry.insert(0, str(abilities.get(ability, 10)))

        self.hp_entry.delete(0, "end")
        self.hp_entry.insert(0, str(char.get('hp', 0)))

        self.ac_entry.delete(0, "end")
        self.ac_entry.insert(0, str(char.get('ac', 10)))

        self.initiative_entry.delete(0, "end")
        self.initiative_entry.insert(0, str(char.get('initiative', 0)))

        self.notes_text.delete("0.0", "end")
        self.notes_text.insert("0.0", char.get('notes', ''))

    def clear_character_data(self):
        self.name_entry.delete(0, "end")
        self.class_entry.delete(0, "end")
        self.level_entry.delete(0, "end")
        self.race_entry.delete(0, "end")

        for entry in self.ability_entries.values():
            entry.delete(0, "end")
            entry.insert(0, "")

        self.hp_entry.delete(0, "end")
        self.ac_entry.delete(0, "end")
        self.initiative_entry.delete(0, "end")
        self.notes_text.delete("0.0", "end")


class CharacterImportWizard(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.character_data = {}
        
        self.title("Character Import Wizard")
        self.geometry("600x700")
        self.resizable(False, False)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="📋 Character Import Wizard",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ffd700"
        )
        title_label.grid(row=0, column=0, pady=20)
        
        # Instructions
        instructions = ctk.CTkLabel(
            self,
            text="Please enter your character information from your PDF character sheet.\nFill in the fields below and click 'Import Character' when done.",
            font=ctk.CTkFont(size=14),
            text_color="#cccccc",
            justify="center"
        )
        instructions.grid(row=1, column=0, pady=(0, 20))
        
        # Main scrollable frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Basic Information
        basic_frame = ctk.CTkFrame(main_frame)
        basic_frame.grid(row=0, column=0, sticky="ew", pady=10)
        basic_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(basic_frame, text="Basic Information", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, pady=10)
        
        # Name
        ctk.CTkLabel(basic_frame, text="Character Name:").grid(row=1, column=0, sticky="w", padx=10, pady=(10, 0))
        self.name_entry = ctk.CTkEntry(basic_frame, width=300)
        self.name_entry.grid(row=2, column=0, padx=10, pady=(0, 10))
        
        # Class and Level
        ctk.CTkLabel(basic_frame, text="Class:").grid(row=3, column=0, sticky="w", padx=10, pady=(10, 0))
        self.class_entry = ctk.CTkEntry(basic_frame, width=150)
        self.class_entry.grid(row=4, column=0, sticky="w", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(basic_frame, text="Level:").grid(row=3, column=1, sticky="w", padx=10, pady=(10, 0))
        self.level_entry = ctk.CTkEntry(basic_frame, width=80)
        self.level_entry.grid(row=4, column=1, sticky="w", padx=10, pady=(0, 10))
        
        # Race
        ctk.CTkLabel(basic_frame, text="Race:").grid(row=5, column=0, sticky="w", padx=10, pady=(10, 0))
        self.race_entry = ctk.CTkEntry(basic_frame, width=200)
        self.race_entry.grid(row=6, column=0, sticky="w", padx=10, pady=(0, 10))
        
        # Ability Scores
        abilities_frame = ctk.CTkFrame(main_frame)
        abilities_frame.grid(row=1, column=0, sticky="ew", pady=10)
        abilities_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(abilities_frame, text="Ability Scores", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, pady=10)
        
        abilities = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
        self.ability_entries = {}
        
        for i, ability in enumerate(abilities):
            row = (i // 3) + 1
            col = i % 3
            
            ability_frame = ctk.CTkFrame(abilities_frame, fg_color="#222831")
            ability_frame.grid(row=row, column=col, padx=10, pady=5, sticky="ew")
            
            ctk.CTkLabel(ability_frame, text=f"{ability}:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
            entry = ctk.CTkEntry(ability_frame, width=80, justify="center")
            entry.grid(row=1, column=0, pady=5)
            self.ability_entries[ability] = entry
        
        # Combat Stats
        combat_frame = ctk.CTkFrame(main_frame)
        combat_frame.grid(row=2, column=0, sticky="ew", pady=10)
        combat_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(combat_frame, text="Combat Statistics", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, pady=10)
        
        # HP, AC, Initiative
        ctk.CTkLabel(combat_frame, text="Max HP:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.hp_entry = ctk.CTkEntry(combat_frame, width=100, justify="center")
        self.hp_entry.grid(row=1, column=1, padx=(10, 20), pady=5)
        
        ctk.CTkLabel(combat_frame, text="Armor Class:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
        self.ac_entry = ctk.CTkEntry(combat_frame, width=100, justify="center")
        self.ac_entry.grid(row=1, column=3, padx=(10, 20), pady=5)
        
        ctk.CTkLabel(combat_frame, text="Initiative:").grid(row=1, column=4, sticky="w", padx=10, pady=5)
        self.initiative_entry = ctk.CTkEntry(combat_frame, width=100, justify="center")
        self.initiative_entry.grid(row=1, column=5, padx=10, pady=5)
        
        # Notes
        notes_frame = ctk.CTkFrame(main_frame)
        notes_frame.grid(row=3, column=0, sticky="ew", pady=10)
        notes_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(notes_frame, text="Additional Notes", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, pady=10)
        
        self.notes_text = ctk.CTkTextbox(notes_frame, height=100)
        self.notes_text.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, sticky="ew", pady=20)
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(
            button_frame,
            text="Import Character",
            command=self.import_character,
            fg_color="#4caf50",
            hover_color="#388e3c",
            height=40
        ).grid(row=0, column=0, padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            fg_color="#f44336",
            hover_color="#d32f2f",
            height=40
        ).grid(row=0, column=1, padx=10)
        
    def import_character(self):
        """Import the character data"""
        try:
            # Validate required fields
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showwarning("Validation", "Character name is required!")
                return
            
            # Get all the data
            char_class = self.class_entry.get().strip()
            level = int(self.level_entry.get() or 1)
            race = self.race_entry.get().strip()
            
            # Get ability scores
            abilities = {}
            for ability, entry in self.ability_entries.items():
                val = entry.get().strip()
                if not val:
                    messagebox.showwarning("Validation", f"{ability} score is required!")
                    return
                if not val.isdigit():
                    messagebox.showwarning("Validation", f"{ability} must be a number!")
                    return
                abilities[ability] = int(val)
            
            # Get combat stats
            hp = int(self.hp_entry.get() or 0)
            ac = int(self.ac_entry.get() or 10)
            initiative = int(self.initiative_entry.get() or 0)
            notes = self.notes_text.get("0.0", "end").strip()
            
            # Create character object
            character = {
                'name': name,
                'class': char_class,
                'level': level,
                'race': race,
                'abilities': abilities,
                'hp': hp,
                'ac': ac,
                'initiative': initiative,
                'notes': notes
            }
            
            # Add to parent's character list
            self.parent.characters.append(character)
            self.parent.save_characters()
            self.parent.refresh_character_list()
            
            # Select the new character
            self.parent.selected_index = len(self.parent.characters) - 1
            self.parent.current_character = character
            self.parent.load_character_data()
            
            messagebox.showinfo("Success", f"Character '{name}' imported successfully!")
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import character: {str(e)}")


# Keep the original class for backward compatibility
class CharacterSheetApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("D&D Character Sheet")
        self.root.geometry("700x540")

        self.frame = CharacterSheetFrame(self.root)
        self.frame.pack(fill='both', expand=True)
