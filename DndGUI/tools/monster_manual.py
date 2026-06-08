import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk

class MonsterManualFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # Enhanced monster data
        self.monsters = {
            "Goblin": {
                "type": "Small humanoid (goblinoid)",
                "alignment": "Neutral Evil",
                "armor_class": 15,
                "hit_points": "2d6 (7 hp)",
                "speed": "30 ft.",
                "abilities": {
                    "STR": 8, "DEX": 14, "CON": 10, "INT": 8, "WIS": 8, "CHA": 8
                },
                "skills": "Stealth +6",
                "senses": "Darkvision 60 ft., passive Perception 9",
                "languages": "Common, Goblin",
                "challenge_rating": "1/4 (50 XP)",
                "actions": [
                    "Scimitar. Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage.",
                    "Shortbow. Ranged Weapon Attack: +4 to hit, range 80/320 ft., one target. Hit: 5 (1d6 + 2) piercing damage."
                ],
                "special_abilities": [
                    "Nimble Escape. The goblin can take the Disengage or Hide action as a bonus action on each of its turns."
                ]
            },
            "Orc": {
                "type": "Medium humanoid (orc)",
                "alignment": "Chaotic Evil",
                "armor_class": 13,
                "hit_points": "2d8 + 2 (11 hp)",
                "speed": "30 ft.",
                "abilities": {
                    "STR": 16, "DEX": 12, "CON": 16, "INT": 7, "WIS": 11, "CHA": 10
                },
                "skills": "Intimidation +2",
                "senses": "Darkvision 60 ft., passive Perception 10",
                "languages": "Common, Orc",
                "challenge_rating": "1/2 (100 XP)",
                "actions": [
                    "Greataxe. Melee Weapon Attack: +5 to hit, reach 5 ft., one target. Hit: 9 (1d12 + 3) slashing damage.",
                    "Javelin. Melee or Ranged Weapon Attack: +5 to hit, reach 5 ft. or range 30/120 ft., one target. Hit: 6 (1d6 + 3) piercing damage."
                ],
                "special_abilities": [
                    "Aggressive. As a bonus action, the orc can move up to its speed toward a hostile creature that it can see."
                ]
            },
            "Dragon, Young Red": {
                "type": "Large dragon",
                "alignment": "Chaotic Evil",
                "armor_class": 18,
                "hit_points": "17d10 + 68 (161 hp)",
                "speed": "40 ft., climb 40 ft., fly 80 ft.",
                "abilities": {
                    "STR": 23, "DEX": 10, "CON": 21, "INT": 14, "WIS": 11, "CHA": 19
                },
                "skills": "Perception +4, Stealth +3",
                "senses": "Blindsight 30 ft., darkvision 120 ft., passive Perception 14",
                "languages": "Common, Draconic",
                "challenge_rating": "10 (5,900 XP)",
                "actions": [
                    "Bite. Melee Weapon Attack: +10 to hit, reach 10 ft., one target. Hit: 17 (2d10 + 6) piercing damage plus 3 (1d6) fire damage.",
                    "Claw. Melee Weapon Attack: +10 to hit, reach 5 ft., one target. Hit: 13 (2d6 + 6) slashing damage.",
                    "Fire Breath (Recharge 5-6). The dragon exhales fire in a 30-foot cone. Each creature in that area must make a DC 17 Dexterity saving throw, taking 56 (16d6) fire damage on a failed save, or half as much damage on a successful one."
                ],
                "special_abilities": [
                    "Fire Resistance. The dragon has resistance to fire damage.",
                    "Fire Breath. The dragon can breathe fire as an action."
                ]
            }
        }
        
        self.filtered_monsters = list(self.monsters.keys())
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="🐉 Monster Manual",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ffd700"
        )
        title_label.pack(pady=20)
        
        # Search frame
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=10)
        self.search_entry = ctk.CTkEntry(search_frame, width=300, placeholder_text="Enter monster name...")
        self.search_entry.pack(side="left", padx=(10, 10))
        self.search_entry.bind('<KeyRelease>', self.search_monsters)
        
        # Main content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Monster list frame
        list_frame = ctk.CTkFrame(content_frame)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(list_frame, text="Monsters", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Use tkinter Listbox for better selection
        self.monster_listbox = tk.Listbox(
            list_frame,
            bg='#2b2b2b',
            fg='#ffffff',
            selectbackground='#404040',
            font=('Segoe UI', 12),
            height=15
        )
        self.monster_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.monster_listbox.bind('<<ListboxSelect>>', self.show_monster_details)
        
        # Monster details frame
        details_frame = ctk.CTkFrame(content_frame)
        details_frame.pack(side="right", fill="both", expand=True)
        
        ctk.CTkLabel(details_frame, text="Monster Details", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
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
            text="🎲 Roll HP",
            command=self.roll_monster_hp,
            width=120,
            height=35,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_frame,
            text="⚔️ Add to Combat",
            command=self.add_to_combat,
            width=120,
            height=35,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)
        
        self.refresh_monster_list()
        
    def refresh_monster_list(self):
        self.monster_listbox.delete(0, "end")
        for monster_name in sorted(self.filtered_monsters):
            monster = self.monsters[monster_name]
            cr = monster.get('challenge_rating', 'Unknown')
            display_text = f"{monster_name} (CR {cr})"
            self.monster_listbox.insert("end", display_text)
    
    def search_monsters(self, event=None):
        search_term = self.search_entry.get().lower()
        self.filtered_monsters = []
        
        for monster_name in self.monsters.keys():
            monster = self.monsters[monster_name]
            if (search_term in monster_name.lower() or 
                search_term in monster.get('type', '').lower() or
                search_term in monster.get('alignment', '').lower()):
                self.filtered_monsters.append(monster_name)
        
        self.refresh_monster_list()
    
    def show_monster_details(self, event=None):
        selection = self.monster_listbox.curselection()
        if not selection:
            return
        
        # Get the actual monster name from the display text
        display_text = self.monster_listbox.get(selection[0])
        monster_name = display_text.split(" (CR")[0]  # Extract name before CR
        
        monster = self.monsters.get(monster_name)
        if monster:
            self.details_text.delete("0.0", "end")
            
            # Format monster details nicely
            details = f"🐉 {monster_name}\n"
            details += f"{'=' * (len(monster_name) + 4)}\n\n"
            details += f"📋 Type: {monster.get('type', 'Unknown')}\n"
            details += f"⚖️ Alignment: {monster.get('alignment', 'Unknown')}\n"
            details += f"🛡️ Armor Class: {monster.get('armor_class', 'Unknown')}\n"
            details += f"❤️ Hit Points: {monster.get('hit_points', 'Unknown')}\n"
            details += f"🏃 Speed: {monster.get('speed', 'Unknown')}\n\n"
            
            # Ability scores
            abilities = monster.get('abilities', {})
            if abilities:
                details += "📊 Ability Scores:\n"
                for ability, score in abilities.items():
                    modifier = (score - 10) // 2
                    modifier_str = f"+{modifier}" if modifier >= 0 else str(modifier)
                    details += f"  {ability}: {score} ({modifier_str})\n"
                details += "\n"
            
            # Skills and senses
            if 'skills' in monster:
                details += f"🎯 Skills: {monster['skills']}\n"
            if 'senses' in monster:
                details += f"👁️ Senses: {monster['senses']}\n"
            if 'languages' in monster:
                details += f"🗣️ Languages: {monster['languages']}\n"
            if 'challenge_rating' in monster:
                details += f"⭐ Challenge Rating: {monster['challenge_rating']}\n"
            
            details += "\n"
            
            # Special abilities
            special_abilities = monster.get('special_abilities', [])
            if special_abilities:
                details += "✨ Special Abilities:\n"
                for ability in special_abilities:
                    details += f"  • {ability}\n"
                details += "\n"
            
            # Actions
            actions = monster.get('actions', [])
            if actions:
                details += "⚔️ Actions:\n"
                for action in actions:
                    details += f"  • {action}\n"
            
            self.details_text.insert("0.0", details)
            
            # Store current monster for actions
            self.current_monster = monster_name
    
    def roll_monster_hp(self):
        """Roll HP for the current monster"""
        if not hasattr(self, 'current_monster'):
            messagebox.showwarning("Warning", "Please select a monster first")
            return
        
        monster = self.monsters[self.current_monster]
        hp_expr = monster.get('hit_points', '')
        
        if not hp_expr or 'd' not in hp_expr:
            messagebox.showinfo("Info", "No HP dice expression found for this monster")
            return
        
        # Parse HP expression (e.g., "2d6 (7 hp)" -> roll 2d6)
        import re
        match = re.search(r'(\d+)d(\d+)', hp_expr)
        if match:
            num_dice = int(match.group(1))
            sides = int(match.group(2))
            
            # Roll the HP
            import random
            rolls = [random.randint(1, sides) for _ in range(num_dice)]
            total = sum(rolls)
            
            # Check for modifier (e.g., "2d6 + 2")
            modifier_match = re.search(r'\+(\d+)', hp_expr)
            if modifier_match:
                modifier = int(modifier_match.group(1))
                total += modifier
                rolls.append(f"+{modifier}")
            
            messagebox.showinfo(
                f"{self.current_monster} HP",
                f"Rolled HP: {total}\nRolls: {rolls}\nExpression: {hp_expr}"
            )
    
    def add_to_combat(self):
        """Add monster to initiative tracker"""
        if not hasattr(self, 'current_monster'):
            messagebox.showwarning("Warning", "Please select a monster first")
            return
        
        monster = self.monsters[self.current_monster]
        
        # Create a simple monster entry for combat
        monster_entry = {
            'name': self.current_monster,
            'initiative': 0,  # Will be rolled
            'hp': 0,  # Will be rolled
            'current_hp': 0,
            'ac': monster.get('armor_class', 10),
            'type': 'Enemy',
            'conditions': []
        }
        
        # Try to roll HP if possible
        hp_expr = monster.get('hit_points', '')
        if 'd' in hp_expr:
            import re
            match = re.search(r'(\d+)d(\d+)', hp_expr)
            if match:
                import random
                num_dice = int(match.group(1))
                sides = int(match.group(2))
                hp = sum([random.randint(1, sides) for _ in range(num_dice)])
                
                # Add modifier if present
                modifier_match = re.search(r'\+(\d+)', hp_expr)
                if modifier_match:
                    hp += int(modifier_match.group(1))
                
                monster_entry['hp'] = hp
                monster_entry['current_hp'] = hp
        
        messagebox.showinfo(
            "Monster Added",
            f"{self.current_monster} added to combat!\n"
            f"AC: {monster_entry['ac']}\n"
            f"HP: {monster_entry['hp'] if monster_entry['hp'] > 0 else 'Roll manually'}\n\n"
            "You can now add it to your initiative tracker."
        )


# Keep the original class for backward compatibility
class MonsterManualApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("D&D Monster Manual")
        self.root.geometry("800x450")
        
        self.frame = MonsterManualFrame(self.root)
        self.frame.pack(fill='both', expand=True)
