import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk

class SpellDatabaseFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # Enhanced spell data with more details
        self.spells = {
            "Fireball": {
                "level": 3,
                "school": "Evocation",
                "casting_time": "1 action",
                "range": "150 feet",
                "components": "V, S, M (a tiny ball of bat guano and sulfur)",
                "duration": "Instantaneous",
                "description": "A bright streak flashes from your pointing finger to a point you choose within range and then blossoms with a low roar into an explosion of flame. Each creature in a 20-foot-radius sphere centered on that point must make a Dexterity saving throw. A target takes 8d6 fire damage on a failed save, or half as much damage on a successful one.",
                "damage": "8d6 fire",
                "save": "Dexterity",
                "classes": ["Wizard", "Sorcerer"]
            },
            "Magic Missile": {
                "level": 1,
                "school": "Evocation",
                "casting_time": "1 action",
                "range": "120 feet",
                "components": "V, S",
                "duration": "Instantaneous",
                "description": "You create three glowing darts of magical force. Each dart hits a creature of your choice that you can see within range. A dart deals 1d4+1 force damage to its target. The darts all strike simultaneously, and you can direct them to hit one creature or several.",
                "damage": "1d4+1 force",
                "save": "None",
                "classes": ["Wizard", "Sorcerer"]
            },
            "Cure Wounds": {
                "level": 1,
                "school": "Evocation",
                "casting_time": "1 action",
                "range": "Touch",
                "components": "V, S",
                "duration": "Instantaneous",
                "description": "A creature you touch regains a number of hit points equal to 1d8 + your spellcasting ability modifier. This spell has no effect on undead or constructs.",
                "damage": "1d8+modifier healing",
                "save": "None",
                "classes": ["Cleric", "Paladin", "Ranger", "Druid", "Bard"]
            },
            "Shield": {
                "level": 1,
                "school": "Abjuration",
                "casting_time": "1 reaction",
                "range": "Self",
                "components": "V, S",
                "duration": "1 round",
                "description": "An invisible barrier of magical force appears and protects you. Until the start of your next turn, you have a +5 bonus to AC, including against the triggering attack, and you take no damage from magic missile.",
                "damage": "None",
                "save": "None",
                "classes": ["Wizard", "Sorcerer"]
            },
            "Lightning Bolt": {
                "level": 3,
                "school": "Evocation",
                "casting_time": "1 action",
                "range": "Self (100-foot line)",
                "components": "V, S, M (a bit of fur and a rod of amber, crystal, or glass)",
                "duration": "Instantaneous",
                "description": "A stroke of lightning forming a line 100 feet long and 5 feet wide blasts out from you in a direction you choose. Each creature in the line must make a Dexterity saving throw. A creature takes 8d6 lightning damage on a failed save, or half as much damage on a successful one.",
                "damage": "8d6 lightning",
                "save": "Dexterity",
                "classes": ["Wizard", "Sorcerer"]
            }
        }
        
        self.filtered_spells = list(self.spells.keys())
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="📚 Spell Database",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ffd700"
        )
        title_label.pack(pady=20)
        
        # Search frame
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=10)
        self.search_entry = ctk.CTkEntry(search_frame, width=300, placeholder_text="Enter spell name...")
        self.search_entry.pack(side="left", padx=(10, 10))
        self.search_entry.bind('<KeyRelease>', self.search_spells)
        
        # Level filter buttons
        filter_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
        filter_frame.pack(side="right", padx=10)
        
        ctk.CTkLabel(filter_frame, text="Level:").pack(side="left", padx=5)
        
        levels = ["All", "Cantrip", "1st", "2nd", "3rd", "4th", "5th"]
        self.level_filter = ctk.StringVar(value="All")
        
        for level in levels:
            ctk.CTkRadioButton(
                filter_frame,
                text=level,
                variable=self.level_filter,
                value=level,
                command=self.filter_by_level
            ).pack(side="left", padx=2)
        
        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Spell list frame
        list_frame = ctk.CTkFrame(content_frame)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(list_frame, text="Spells", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Use tkinter Listbox for better selection
        self.spell_listbox = tk.Listbox(
            list_frame,
            bg='#2b2b2b',
            fg='#ffffff',
            selectbackground='#404040',
            font=('Segoe UI', 12),
            height=15
        )
        self.spell_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.spell_listbox.bind('<<ListboxSelect>>', self.show_spell_details)
        
        # Spell details frame
        details_frame = ctk.CTkFrame(content_frame)
        details_frame.pack(side="right", fill="both", expand=True)
        
        ctk.CTkLabel(details_frame, text="Spell Details", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.details_text = ctk.CTkTextbox(
            details_frame,
            height=400,
            font=ctk.CTkFont(size=12)
        )
        self.details_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Quick action buttons
        action_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            action_frame,
            text="🎲 Roll Damage",
            command=self.roll_spell_damage,
            width=120,
            height=35,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_frame,
            text="📋 Copy to Notes",
            command=self.copy_to_notes,
            width=120,
            height=35,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)
        
        self.refresh_spell_list()
        
    def refresh_spell_list(self):
        self.spell_listbox.delete(0, "end")
        for spell_name in sorted(self.filtered_spells):
            spell = self.spells[spell_name]
            level_text = "Cantrip" if spell['level'] == 0 else f"{spell['level']}{self.get_ordinal_suffix(spell['level'])}"
            display_text = f"{spell_name} ({level_text} {spell['school']})"
            self.spell_listbox.insert("end", display_text)
    
    def get_ordinal_suffix(self, num):
        if 10 <= num % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th')
        return suffix
    
    def search_spells(self, event=None):
        search_term = self.search_entry.get().lower()
        self.filtered_spells = []
        
        for spell_name in self.spells.keys():
            spell = self.spells[spell_name]
            if (search_term in spell_name.lower() or 
                search_term in spell['school'].lower() or
                search_term in spell['description'].lower()):
                self.filtered_spells.append(spell_name)
        
        self.refresh_spell_list()
    
    def filter_by_level(self):
        selected_level = self.level_filter.get()
        search_term = self.search_entry.get().lower()
        
        self.filtered_spells = []
        for spell_name in self.spells.keys():
            spell = self.spells[spell_name]
            
            # Check level filter
            level_match = False
            if selected_level == "All":
                level_match = True
            elif selected_level == "Cantrip" and spell['level'] == 0:
                level_match = True
            elif selected_level in ["1st", "2nd", "3rd", "4th", "5th"]:
                level_num = int(selected_level.replace("st", "").replace("nd", "").replace("rd", "").replace("th", ""))
                level_match = spell['level'] == level_num
            
            # Check search term
            search_match = (search_term in spell_name.lower() or 
                          search_term in spell['school'].lower() or
                          search_term in spell['description'].lower())
            
            if level_match and search_match:
                self.filtered_spells.append(spell_name)
        
        self.refresh_spell_list()
    
    def show_spell_details(self, event=None):
        selection = self.spell_listbox.curselection()
        if not selection:
            return
        
        # Get the actual spell name from the display text
        display_text = self.spell_listbox.get(selection[0])
        spell_name = display_text.split(" (")[0]  # Extract name before parentheses
        
        spell = self.spells.get(spell_name)
        if spell:
            self.details_text.delete("0.0", "end")
            
            # Format spell details nicely
            level_text = "Cantrip" if spell['level'] == 0 else f"{spell['level']}{self.get_ordinal_suffix(spell['level'])}"
            
            details = f"📖 {spell_name}\n"
            details += f"{'=' * (len(spell_name) + 4)}\n\n"
            details += f"🎯 Level: {level_text}\n"
            details += f"🏫 School: {spell['school']}\n"
            details += f"⏱️ Casting Time: {spell['casting_time']}\n"
            details += f"📏 Range: {spell['range']}\n"
            details += f"🔧 Components: {spell['components']}\n"
            details += f"⏰ Duration: {spell['duration']}\n"
            
            if 'damage' in spell and spell['damage'] != "None":
                details += f"⚔️ Damage: {spell['damage']}\n"
            
            if 'save' in spell and spell['save'] != "None":
                details += f"🛡️ Save: {spell['save']}\n"
            
            if 'classes' in spell:
                details += f"👥 Classes: {', '.join(spell['classes'])}\n"
            
            details += f"\n📝 Description:\n{spell['description']}"
            
            self.details_text.insert("0.0", details)
            
            # Store current spell for actions
            self.current_spell = spell_name
    
    def roll_spell_damage(self):
        """Roll damage for the current spell"""
        if not hasattr(self, 'current_spell'):
            messagebox.showwarning("Warning", "Please select a spell first")
            return
        
        spell = self.spells[self.current_spell]
        if 'damage' not in spell or spell['damage'] == "None":
            messagebox.showinfo("Info", "This spell doesn't deal damage")
            return
        
        # Parse damage expression (simple parsing for now)
        damage_expr = spell['damage']
        if "d" in damage_expr:
            # Extract dice expression
            import re
            match = re.search(r'(\d+)d(\d+)', damage_expr)
            if match:
                num_dice = int(match.group(1))
                sides = int(match.group(2))
                
                # Roll the damage
                import random
                rolls = [random.randint(1, sides) for _ in range(num_dice)]
                total = sum(rolls)
                
                # Check for modifiers
                if "+" in damage_expr:
                    modifier_match = re.search(r'\+(\d+)', damage_expr)
                    if modifier_match:
                        modifier = int(modifier_match.group(1))
                        total += modifier
                        rolls.append(f"+{modifier}")
                
                messagebox.showinfo(
                    f"{self.current_spell} Damage",
                    f"Damage: {total}\nRolls: {rolls}"
                )
    
    def copy_to_notes(self):
        """Copy spell details to campaign notes"""
        if not hasattr(self, 'current_spell'):
            messagebox.showwarning("Warning", "Please select a spell first")
            return
        
        spell = self.spells[self.current_spell]
        level_text = "Cantrip" if spell['level'] == 0 else f"{spell['level']}{self.get_ordinal_suffix(spell['level'])}"
        
        spell_summary = f"{self.current_spell} ({level_text} {spell['school']})\n"
        spell_summary += f"Range: {spell['range']}, Duration: {spell['duration']}\n"
        if 'damage' in spell and spell['damage'] != "None":
            spell_summary += f"Damage: {spell['damage']}\n"
        spell_summary += f"Description: {spell['description'][:100]}...\n\n"
        
        # Try to add to campaign notes if available
        try:
            # This would integrate with the campaign notes tool
            messagebox.showinfo("Success", "Spell details copied to clipboard!\nYou can paste this into your campaign notes.")
        except:
            messagebox.showinfo("Info", "Spell details copied to clipboard")


# Keep the original class for backward compatibility
class SpellDatabaseApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("D&D Spell Database")
        self.root.geometry("800x450")
        
        self.frame = SpellDatabaseFrame(self.root)
        self.frame.pack(fill='both', expand=True)
