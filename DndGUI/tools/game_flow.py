import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os

class GameFlowFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.current_phase = "preparation"
        self.session_data = {
            "session_number": 1,
            "current_phase": "preparation",
            "completed_phases": [],
            "notes": {}
        }
        
        self.setup_ui()
        self.load_session_data()
        
    def setup_ui(self):
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="🎯 Game Flow Guide",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ffd700"
        )
        title_label.grid(row=0, column=0, pady=20)
        
        # Main content area
        content_frame = ctk.CTkFrame(self)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)
        
        # Phase selector
        phase_frame = ctk.CTkFrame(content_frame)
        phase_frame.grid(row=0, column=0, sticky="ew", pady=10)
        phase_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            phase_frame,
            text="Current Game Phase:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=10)
        
        self.phase_var = tk.StringVar(value="preparation")
        phase_options = [
            ("preparation", "📋 Session Preparation"),
            ("character_setup", "👤 Character Setup"),
            ("roleplay", "🎭 Roleplay & Exploration"),
            ("combat", "⚔️ Combat"),
            ("rest", "😴 Rest & Recovery"),
            ("session_end", "🏁 Session End")
        ]
        
        for i, (value, text) in enumerate(phase_options):
            ctk.CTkRadioButton(
                phase_frame,
                text=text,
                variable=self.phase_var,
                value=value,
                command=self.on_phase_change
            ).grid(row=1, column=i, padx=10, pady=10)
        
        # Phase content
        self.phase_content = ctk.CTkScrollableFrame(content_frame)
        self.phase_content.grid(row=1, column=0, sticky="nsew", pady=10)
        self.phase_content.grid_columnconfigure(0, weight=1)
        
        # Action buttons
        action_frame = ctk.CTkFrame(content_frame)
        action_frame.grid(row=2, column=0, sticky="ew", pady=10)
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)
        action_frame.grid_columnconfigure(2, weight=1)
        
        ctk.CTkButton(
            action_frame,
            text="✅ Complete Phase",
            command=self.complete_phase,
            fg_color="#4caf50",
            hover_color="#388e3c",
            height=40
        ).grid(row=0, column=0, padx=10, pady=10)
        
        ctk.CTkButton(
            action_frame,
            text="📝 Add Note",
            command=self.add_phase_note,
            fg_color="#2196f3",
            hover_color="#1565c0",
            height=40
        ).grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkButton(
            action_frame,
            text="💾 Save Session",
            command=self.save_session,
            fg_color="#ff9800",
            hover_color="#e68900",
            height=40
        ).grid(row=0, column=2, padx=10, pady=10)
        
        # Initialize phase content
        self.on_phase_change()
        
    def on_phase_change(self):
        """Update the phase content when phase changes"""
        phase = self.phase_var.get()
        self.current_phase = phase
        
        # Clear existing content
        for widget in self.phase_content.winfo_children():
            widget.destroy()
        
        # Show phase-specific content
        if phase == "preparation":
            self.show_preparation_phase()
        elif phase == "character_setup":
            self.show_character_setup_phase()
        elif phase == "roleplay":
            self.show_roleplay_phase()
        elif phase == "combat":
            self.show_combat_phase()
        elif phase == "rest":
            self.show_rest_phase()
        elif phase == "session_end":
            self.show_session_end_phase()
            
    def show_preparation_phase(self):
        """Show session preparation guidance"""
        ctk.CTkLabel(
            self.phase_content,
            text="📋 Session Preparation",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffd700"
        ).grid(row=0, column=0, pady=20)
        
        steps = [
            "1. 📚 Review your character sheet and update any changes",
            "2. 🎲 Check your dice and make sure they're ready",
            "3. 📝 Review campaign notes from previous sessions",
            "4. ✨ Prepare spells and abilities you plan to use",
            "5. 🍕 Get snacks and drinks ready",
            "6. 📱 Close distracting apps and focus on the game"
        ]
        
        for i, step in enumerate(steps):
            ctk.CTkLabel(
                self.phase_content,
                text=step,
                font=ctk.CTkFont(size=14),
                justify="left"
            ).grid(row=i+1, column=0, sticky="w", padx=20, pady=5)
            
        # Quick actions
        ctk.CTkLabel(
            self.phase_content,
            text="Quick Actions:",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4caf50"
        ).grid(row=len(steps)+1, column=0, pady=(20, 10))
        
        action_buttons = ctk.CTkFrame(self.phase_content, fg_color="transparent")
        action_buttons.grid(row=len(steps)+2, column=0, sticky="ew", padx=20)
        
        ctk.CTkButton(
            action_buttons,
            text="📋 Open Character Sheet",
            command=lambda: self.parent.master.tabview.set("📜 Character Sheet"),
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_buttons,
            text="📝 Open Campaign Notes",
            command=lambda: self.parent.master.tabview.set("📝 Campaign Notes"),
            width=150
        ).pack(side="left", padx=5)
        
    def show_character_setup_phase(self):
        """Show character setup guidance"""
        ctk.CTkLabel(
            self.phase_content,
            text="👤 Character Setup",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffd700"
        ).grid(row=0, column=0, pady=20)
        
        steps = [
            "1. 📋 Import or create your character if you haven't already",
            "2. 🎲 Roll for initiative if combat is starting",
            "3. ✨ Prepare your spells and abilities for the session",
            "4. 📊 Check your current HP, AC, and other stats",
            "5. 🎭 Think about your character's motivations and goals",
            "6. 🤝 Coordinate with other players on tactics"
        ]
        
        for i, step in enumerate(steps):
            ctk.CTkLabel(
                self.phase_content,
                text=step,
                font=ctk.CTkFont(size=14),
                justify="left"
            ).grid(row=i+1, column=0, sticky="w", padx=20, pady=5)
            
        # Quick actions
        ctk.CTkLabel(
            self.phase_content,
            text="Quick Actions:",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4caf50"
        ).grid(row=len(steps)+1, column=0, pady=(20, 10))
        
        action_buttons = ctk.CTkFrame(self.phase_content, fg_color="transparent")
        action_buttons.grid(row=len(steps)+2, column=0, sticky="ew", padx=20)
        
        ctk.CTkButton(
            action_buttons,
            text="📋 Character Sheet",
            command=lambda: self.parent.master.tabview.set("📜 Character Sheet"),
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_buttons,
            text="⚔️ Initiative Tracker",
            command=lambda: self.parent.master.tabview.set("⚔️ Initiative Tracker"),
            width=150
        ).pack(side="left", padx=5)
        
    def show_roleplay_phase(self):
        """Show roleplay and exploration guidance"""
        ctk.CTkLabel(
            self.phase_content,
            text="🎭 Roleplay & Exploration",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffd700"
        ).grid(row=0, column=0, pady=20)
        
        steps = [
            "1. 🎭 Stay in character and think about their personality",
            "2. 👂 Listen to other players and the DM",
            "3. 🗣️ Ask questions about the environment and NPCs",
            "4. 🎲 Roll skill checks when needed (Perception, Investigation, etc.)",
            "5. 📝 Take notes about important information",
            "6. 🤝 Work with your party to solve problems"
        ]
        
        for i, step in enumerate(steps):
            ctk.CTkLabel(
                self.phase_content,
                text=step,
                font=ctk.CTkFont(size=14),
                justify="left"
            ).grid(row=i+1, column=0, sticky="w", padx=20, pady=5)
            
        # Quick actions
        ctk.CTkLabel(
            self.phase_content,
            text="Quick Actions:",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4caf50"
        ).grid(row=len(steps)+1, column=0, pady=(20, 10))
        
        action_buttons = ctk.CTkFrame(self.phase_content, fg_color="transparent")
        action_buttons.grid(row=len(steps)+2, column=0, sticky="ew", padx=20)
        
        ctk.CTkButton(
            action_buttons,
            text="🎲 Roll Dice",
            command=lambda: self.parent.master.tabview.set("🎲 Dice Roller"),
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_buttons,
            text="📝 Campaign Notes",
            command=lambda: self.parent.master.tabview.set("📝 Campaign Notes"),
            width=150
        ).pack(side="left", padx=5)
        
    def show_combat_phase(self):
        """Show combat guidance"""
        ctk.CTkLabel(
            self.phase_content,
            text="⚔️ Combat",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffd700"
        ).grid(row=0, column=0, pady=20)
        
        steps = [
            "1. ⚔️ Check the initiative order and wait for your turn",
            "2. 🎲 Roll for attack rolls and damage when attacking",
            "3. 🛡️ Roll for saving throws when targeted by spells/effects",
            "4. ✨ Use spells and abilities strategically",
            "5. 📊 Track your HP and conditions",
            "6. 🤝 Coordinate with allies for tactical advantage"
        ]
        
        for i, step in enumerate(steps):
            ctk.CTkLabel(
                self.phase_content,
                text=step,
                font=ctk.CTkFont(size=14),
                justify="left"
            ).grid(row=i+1, column=0, sticky="w", padx=20, pady=5)
            
        # Quick actions
        ctk.CTkLabel(
            self.phase_content,
            text="Quick Actions:",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4caf50"
        ).grid(row=len(steps)+1, column=0, pady=(20, 10))
        
        action_buttons = ctk.CTkFrame(self.phase_content, fg_color="transparent")
        action_buttons.grid(row=len(steps)+2, column=0, sticky="ew", padx=20)
        
        ctk.CTkButton(
            action_buttons,
            text="⚔️ Initiative Tracker",
            command=lambda: self.parent.master.tabview.set("⚔️ Initiative Tracker"),
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_buttons,
            text="🎲 Quick Roll",
            command=lambda: self.parent.master.tabview.set("🎲 Dice Roller"),
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_buttons,
            text="✨ Spell Database",
            command=lambda: self.parent.master.tabview.set("📚 Spell Database"),
            width=150
        ).pack(side="left", padx=5)
        
    def show_rest_phase(self):
        """Show rest and recovery guidance"""
        ctk.CTkLabel(
            self.phase_content,
            text="😴 Rest & Recovery",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffd700"
        ).grid(row=0, column=0, pady=20)
        
        steps = [
            "1. 💤 Take a short rest (1 hour) or long rest (8 hours)",
            "2. 🎲 Roll hit dice to recover HP during short rest",
            "3. ✨ Recover spell slots and abilities during long rest",
            "4. 📝 Update your character sheet with changes",
            "5. 🍕 Take a real break - stretch, eat, hydrate",
            "6. 🎭 Reflect on the session and plan ahead"
        ]
        
        for i, step in enumerate(steps):
            ctk.CTkLabel(
                self.phase_content,
                text=step,
                font=ctk.CTkFont(size=14),
                justify="left"
            ).grid(row=i+1, column=0, sticky="w", padx=20, pady=5)
            
        # Quick actions
        ctk.CTkLabel(
            self.phase_content,
            text="Quick Actions:",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4caf50"
        ).grid(row=len(steps)+1, column=0, pady=(20, 10))
        
        action_buttons = ctk.CTkFrame(self.phase_content, fg_color="transparent")
        action_buttons.grid(row=len(steps)+2, column=0, sticky="ew", padx=20)
        
        ctk.CTkButton(
            action_buttons,
            text="📋 Update Character",
            command=lambda: self.parent.master.tabview.set("📜 Character Sheet"),
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_buttons,
            text="📝 Session Notes",
            command=lambda: self.parent.master.tabview.set("📝 Campaign Notes"),
            width=150
        ).pack(side="left", padx=5)
        
    def show_session_end_phase(self):
        """Show session end guidance"""
        ctk.CTkLabel(
            self.phase_content,
            text="🏁 Session End",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffd700"
        ).grid(row=0, column=0, pady=20)
        
        steps = [
            "1. 📝 Write down important events and decisions",
            "2. 🎭 Note character development and roleplay moments",
            "3. 💰 Track experience points and treasure gained",
            "4. 📋 Update character sheet with any changes",
            "5. 🤝 Thank the DM and other players",
            "6. 📅 Schedule the next session if possible"
        ]
        
        for i, step in enumerate(steps):
            ctk.CTkLabel(
                self.phase_content,
                text=step,
                font=ctk.CTkFont(size=14),
                justify="left"
            ).grid(row=i+1, column=0, sticky="w", padx=20, pady=5)
            
        # Quick actions
        ctk.CTkLabel(
            self.phase_content,
            text="Quick Actions:",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4caf50"
        ).grid(row=len(steps)+1, column=0, pady=(20, 10))
        
        action_buttons = ctk.CTkFrame(self.phase_content, fg_color="transparent")
        action_buttons.grid(row=len(steps)+2, column=0, sticky="ew", padx=20)
        
        ctk.CTkButton(
            action_buttons,
            text="📝 Final Notes",
            command=lambda: self.parent.master.tabview.set("📝 Campaign Notes"),
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_buttons,
            text="💾 Save Everything",
            command=self.save_session,
            width=150
        ).pack(side="left", padx=5)
        
    def complete_phase(self):
        """Mark the current phase as complete"""
        phase = self.phase_var.get()
        if phase not in self.session_data["completed_phases"]:
            self.session_data["completed_phases"].append(phase)
            messagebox.showinfo("Phase Complete", f"Phase '{phase}' marked as complete!")
            self.save_session()
        else:
            messagebox.showinfo("Already Complete", "This phase is already marked as complete!")
            
    def add_phase_note(self):
        """Add a note for the current phase"""
        phase = self.phase_var.get()
        note = tk.simpledialog.askstring("Add Note", f"Add a note for {phase}:")
        if note:
            if phase not in self.session_data["notes"]:
                self.session_data["notes"][phase] = []
            self.session_data["notes"][phase].append(note)
            messagebox.showinfo("Note Added", "Note added successfully!")
            self.save_session()
            
    def save_session(self):
        """Save session data to file"""
        try:
            with open("session_data.json", "w") as f:
                json.dump(self.session_data, f, indent=2)
            messagebox.showinfo("Saved", "Session data saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save session data: {str(e)}")
            
    def load_session_data(self):
        """Load session data from file"""
        try:
            if os.path.exists("session_data.json"):
                with open("session_data.json", "r") as f:
                    self.session_data = json.load(f)
        except Exception as e:
            print(f"Failed to load session data: {str(e)}")

# For backward compatibility
class GameFlowApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Game Flow Guide")
        self.root.geometry("800x600")
        
        self.frame = GameFlowFrame(self.root)
        self.frame.pack(fill="both", expand=True)
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = GameFlowApp()
    app.run()
