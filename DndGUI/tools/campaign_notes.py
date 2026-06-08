import customtkinter as ctk
from tkinter import messagebox
import json
import os
import tkinter as tk


class CampaignNotesFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.notes = []
        self.current_note = None
        self.load_notes()
        self.setup_ui()

    def setup_ui(self):
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="📝 Campaign Notes",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#ffd700"
        )
        title_label.pack(pady=(18, 10))

        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=18, pady=10)

        # Left panel - Notes list
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side="left", fill="y", padx=(0, 12), pady=2)

        # Notes list title
        ctk.CTkLabel(left_frame, text="Notes", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        # Use a Listbox for selectable notes list
        self.tk_listbox = tk.Listbox(
            left_frame, width=25, height=15, exportselection=False, font=("Segoe UI", 11)
        )
        self.tk_listbox.pack(fill="both", expand=True, pady=(0, 10), padx=4)
        self.tk_listbox.bind("<<ListboxSelect>>", self.on_note_select)

        # Note buttons
        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10), padx=4)
        ctk.CTkButton(btn_frame, text="New Note", command=self.new_note, fg_color="#4caf50", hover_color="#388e3c").pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Delete", command=self.delete_note, fg_color="#f44336", hover_color="#b71c1c").pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Save", command=self.save_note, fg_color="#2196f3", hover_color="#1565c0").pack(fill="x", pady=2)

        # Right panel - Note details
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(0, 4))

        # Note title
        ctk.CTkLabel(right_frame, text="Title:").pack(anchor="w", padx=10, pady=(10, 5))
        self.title_entry = ctk.CTkEntry(right_frame, width=400)
        self.title_entry.pack(fill="x", padx=10, pady=(0, 10))

        # Note category
        ctk.CTkLabel(right_frame, text="Category:").pack(anchor="w", padx=10, pady=(0, 5))
        self.category_entry = ctk.CTkEntry(right_frame, width=200)
        self.category_entry.pack(anchor="w", padx=10, pady=(0, 10))

        # Note content
        ctk.CTkLabel(right_frame, text="Content:").pack(anchor="w", padx=10, pady=(0, 5))
        self.content_text = ctk.CTkTextbox(
            right_frame,
            height=300,
            font=ctk.CTkFont(size=12)
        )
        self.content_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Quick templates
        template_frame = ctk.CTkFrame(right_frame)
        template_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(template_frame, text="Quick Templates:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)

        template_btn_frame = ctk.CTkFrame(template_frame, fg_color="transparent")
        template_btn_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            template_btn_frame,
            text="NPC",
            command=lambda: self.insert_template("npc"),
            width=80,
            height=30,
            fg_color="#9c27b0",
            hover_color="#7b1fa2"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            template_btn_frame,
            text="Location",
            command=lambda: self.insert_template("location"),
            width=80,
            height=30,
            fg_color="#ff9800",
            hover_color="#e68900"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            template_btn_frame,
            text="Quest",
            command=lambda: self.insert_template("quest"),
            width=80,
            height=30,
            fg_color="#4caf50",
            hover_color="#388e3c"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            template_btn_frame,
            text="Session",
            command=lambda: self.insert_template("session"),
            width=80,
            height=30,
            fg_color="#2196f3",
            hover_color="#1565c0"
        ).pack(side="left", padx=5)

        self.refresh_notes_list()
        self.clear_note_data()

    def load_notes(self):
        try:
            if os.path.exists('campaign_notes.json'):
                with open('campaign_notes.json', 'r') as f:
                    self.notes = json.load(f)
        except Exception as e:
            self.notes = []
            messagebox.showerror("Error", f"Failed to load notes: {str(e)}")

    def save_notes(self):
        try:
            with open('campaign_notes.json', 'w') as f:
                json.dump(self.notes, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def refresh_notes_list(self):
        self.tk_listbox.delete(0, "end")
        for note in self.notes:
            title = note.get('title', 'Untitled')
            category = note.get('category', '')
            display = f"{title} ({category})" if category else title
            self.tk_listbox.insert("end", display)

    def new_note(self):
        new_note = {
            'title': '',
            'category': '',
            'content': '',
            'created': '',
            'modified': ''
        }
        self.notes.append(new_note)
        self.current_note = new_note
        self.refresh_notes_list()
        self.tk_listbox.select_set(len(self.notes) - 1)
        self.load_note_data()

    def delete_note(self):
        selection = self.tk_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "No note selected")
            return
        idx = selection[0]
        note_title = self.notes[idx].get('title', 'Untitled')
        if messagebox.askyesno("Confirm", f"Delete note '{note_title}'?"):
            del self.notes[idx]
            self.current_note = None
            self.refresh_notes_list()
            self.clear_note_data()
            self.save_notes()

    def save_note(self):
        if not self.current_note:
            messagebox.showwarning("Warning", "No note selected")
            return

        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Validation", "Title cannot be empty.")
            return

        category = self.category_entry.get().strip()
        content = self.content_text.get("0.0", "end").strip()

        self.current_note['title'] = title
        self.current_note['category'] = category
        self.current_note['content'] = content

        self.save_notes()
        self.refresh_notes_list()
        messagebox.showinfo("Success", "Note saved!")

    def on_note_select(self, event):
        selection = self.tk_listbox.curselection()
        if not selection:
            self.current_note = None
            self.clear_note_data()
            return
        idx = selection[0]
        self.current_note = self.notes[idx]
        self.load_note_data()

    def load_note_data(self):
        if not self.current_note:
            self.clear_note_data()
            return

        note = self.current_note

        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, note.get('title', ''))

        self.category_entry.delete(0, "end")
        self.category_entry.insert(0, note.get('category', ''))

        self.content_text.delete("0.0", "end")
        self.content_text.insert("0.0", note.get('content', ''))

    def clear_note_data(self):
        self.title_entry.delete(0, "end")
        self.category_entry.delete(0, "end")
        self.content_text.delete("0.0", "end")

    def insert_template(self, template_type):
        """Insert a template into the content area"""
        templates = {
            "npc": """NPC Name: [Name]
Race: [Race]
Class: [Class]
Level: [Level]
Alignment: [Alignment]
Description: [Physical description and personality]

Background: [History and motivations]

Quests/Goals: [What they want or need]

Relationships: [Connections to other NPCs or PCs]

Notes: [Additional information]""",

            "location": """Location Name: [Name]
Type: [City, Dungeon, Forest, etc.]
Size: [Small, Medium, Large, etc.]
Population: [Number of inhabitants]
Government: [Who's in charge]

Description: [Physical appearance and atmosphere]

Notable Features: [Important landmarks or areas]

History: [Past events and significance]

Current Events: [What's happening now]

Dangers: [Threats or hazards]

NPCs: [Important people here]""",

            "quest": """Quest Title: [Name]
Type: [Main Quest, Side Quest, etc.]
Level Range: [Recommended party level]
Reward: [XP, Gold, Items, etc.]

Description: [What the quest is about]

Objectives: [What needs to be done]
• [Objective 1]
• [Objective 2]
• [Objective 3]

NPCs Involved: [Who's giving or involved in the quest]

Locations: [Where the quest takes place]

Complications: [Potential problems or twists]

Resolution: [How it can be completed]""",

            "session": """Session #: [Number]
Date: [Date]
Party Members: [Who was present]

Summary: [What happened during the session]

Key Events: [Important moments]
• [Event 1]
• [Event 2]
• [Event 3]

NPCs Met: [New characters encountered]

Locations Visited: [Places the party went]

Combat Encounters: [Fights and their outcomes]

Loot Gained: [Items and treasure acquired]

Quests Progress: [Updates on ongoing quests]

Next Session Plans: [What the party plans to do]

DM Notes: [Behind-the-scenes information]"""
        }

        if template_type in templates:
            self.content_text.delete("0.0", "end")
            self.content_text.insert("0.0", templates[template_type])


# Keep the original class for backward compatibility
class CampaignNotesApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("D&D Campaign Notes")
        self.root.geometry("700x540")

        self.frame = CampaignNotesFrame(self.root)
        self.frame.pack(fill='both', expand=True)
