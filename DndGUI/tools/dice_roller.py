import customtkinter as ctk
from tkinter import messagebox
import random
import re
import time
import threading

class DiceRollerFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # Animation variables
        self.rolling = False
        self.roll_history = []
        self.favorite_rolls = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the modern UI layout with CustomTkinter"""
        # Configure grid weights for better space distribution
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header section
        self.create_header()
        
        # Left side - Quick Dice and Custom Roll
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(2, weight=1)
        
        # Quick dice section
        self.create_quick_dice_section(left_frame)
        
        # Custom roll section
        self.create_custom_roll_section(left_frame)
        
        # Right side - Results and History
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        
        # Results section
        self.create_results_section(right_frame)
        
        # History section
        self.create_history_section(right_frame)
        
    def create_header(self):
        """Create the header with title and subtitle"""
        # Main title with emoji
        title_label = ctk.CTkLabel(
            self,
            text="🎲 Quick Dice Roller",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#00d4ff"
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(20, 5))
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            self,
            text="Click any dice to roll! Use quick rolls for common D&D actions.",
            font=ctk.CTkFont(size=16),
            text_color="#cccccc"
        )
        subtitle_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))
        
        # Player guidance
        guidance_label = ctk.CTkLabel(
            self,
            text="💡 Tip: Use 'Attack' for weapon attacks, 'Save' for saving throws, 'Damage' for damage rolls",
            font=ctk.CTkFont(size=12),
            text_color="#4caf50"
        )
        guidance_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
    def create_quick_dice_section(self, parent):
        """Create the quick dice buttons section"""
        dice_frame = ctk.CTkFrame(parent)
        dice_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 20))
        
        # Title
        ctk.CTkLabel(
            dice_frame,
            text="Quick Dice",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#00d4ff"
        ).pack(pady=10)
        
        # Dice buttons container
        dice_container = ctk.CTkFrame(dice_frame)
        dice_container.pack(fill="x", padx=10, pady=(0, 10))
        
        # Common dice with modern styling
        dice_types = [
            ('d4', 4, '🔸'),
            ('d6', 6, '🎲'),
            ('d8', 8, '🔷'),
            ('d10', 10, '🔶'),
            ('d12', 12, '🔺'),
            ('d20', 20, '🎯'),
            ('d100', 100, '💯')
        ]
        
        # Create dice buttons in a grid
        for i, (dice_name, sides, emoji) in enumerate(dice_types):
            row = i // 4
            col = i % 4
            
            btn = ctk.CTkButton(
                dice_container,
                text=f"{emoji}\n{dice_name}",
                font=ctk.CTkFont(size=14, weight="bold"),
                width=80,
                height=60,
                command=lambda s=sides: self.roll_simple_dice(s)
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
        # Quick roll buttons for common D&D actions
        quick_rolls = [
            ("🎯 Attack", "1d20", "#e74c3c"),
            ("🛡️ Save", "1d20", "#3498db"),
            ("💀 Death", "1d20", "#9b59b6"),
            ("⚔️ Sword", "1d8", "#f39c12"),
            ("🏹 Bow", "1d6", "#27ae60"),
            ("🔥 Fireball", "8d6", "#e67e22")
        ]
        
        quick_container = ctk.CTkFrame(dice_frame)
        quick_container.pack(fill="x", padx=10, pady=(0, 10))
        
        for i, (name, roll, color) in enumerate(quick_rolls):
            row = i // 3
            col = i % 3
            
            btn = ctk.CTkButton(
                quick_container,
                text=name,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=120,
                height=40,
                fg_color=color,
                hover_color=self.darken_color(color),
                command=lambda r=roll: self.quick_roll(r)
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
    def create_custom_roll_section(self, parent):
        """Create the custom dice roll section"""
        custom_frame = ctk.CTkFrame(parent)
        custom_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Title
        ctk.CTkLabel(
            custom_frame,
            text="Custom Roll",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#00d4ff"
        ).pack(pady=10)
        
        # Input container
        input_container = ctk.CTkFrame(custom_frame)
        input_container.pack(fill="x", padx=10, pady=(0, 10))
        
        # Label and entry
        ctk.CTkLabel(
            input_container,
            text="Dice Expression:",
            font=ctk.CTkFont(size=14),
            text_color="#ffffff"
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Modern entry field
        self.dice_entry = ctk.CTkEntry(
            input_container,
            font=ctk.CTkFont(size=16),
            placeholder_text="e.g., 2d6+3, 1d20-2",
            height=40
        )
        self.dice_entry.pack(fill="x", padx=10, pady=(0, 10))
        self.dice_entry.insert(0, "1d20")
        
        # Roll button with modern styling
        roll_btn = ctk.CTkButton(
            input_container,
            text="🎲 ROLL DICE",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#e94560",
            hover_color="#c62828",
            command=self.roll_custom_dice
        )
        roll_btn.pack(pady=(0, 10))
        
        # Bind Enter key
        self.dice_entry.bind('<Return>', lambda e: self.roll_custom_dice())
        
    def create_results_section(self, parent):
        """Create the results display section"""
        results_frame = ctk.CTkFrame(parent)
        results_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        # Title
        ctk.CTkLabel(
            results_frame,
            text="Latest Result",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#00d4ff"
        ).pack(pady=10)
        
        # Result display
        self.result_label = ctk.CTkLabel(
            results_frame,
            text="Ready to roll!",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#00ff88",
            height=80
        )
        self.result_label.pack(padx=20, pady=20, fill="x")
        
        # Roll details
        self.details_label = ctk.CTkLabel(
            results_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#cccccc"
        )
        self.details_label.pack(padx=20, pady=(0, 20))
        
    def create_history_section(self, parent):
        """Create the roll history section"""
        history_frame = ctk.CTkFrame(parent)
        history_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_rowconfigure(1, weight=1)
        
        # Title
        ctk.CTkLabel(
            history_frame,
            text="Roll History",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#00d4ff"
        ).grid(row=0, column=0, pady=10)
        
        # History text area with modern styling
        self.history_text = ctk.CTkTextbox(
            history_frame,
            font=ctk.CTkFont(size=12),
            height=200
        )
        self.history_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Control buttons
        btn_frame = ctk.CTkFrame(history_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=(0, 10))
        
        clear_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️ Clear",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35,
            fg_color="#e94560",
            hover_color="#c62828",
            command=self.clear_history
        )
        clear_btn.pack(side="left", padx=5)
                
    def roll_simple_dice(self, sides):
        """Roll a simple die with animation"""
        if self.rolling:
            return
            
        self.rolling = True
        self.animate_roll(f"d{sides}", lambda: self.perform_simple_roll(sides))
        
    def quick_roll(self, expression):
        """Quick roll with predefined expression"""
        if self.rolling:
            return
            
        self.dice_entry.delete(0, "end")
        self.dice_entry.insert(0, expression)
        self.roll_custom_dice()
        
    def roll_custom_dice(self):
        """Parse and roll custom dice expression with animation"""
        if self.rolling:
            return
            
        expression = self.dice_entry.get().strip()
        if not expression:
            messagebox.showerror("Error", "Please enter a dice expression")
            return
            
        try:
            # Validate the expression first
            self.parse_dice_expression(expression)
            self.rolling = True
            self.animate_roll(expression, lambda: self.perform_custom_roll(expression))
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid dice expression: {str(e)}")
            
    def animate_roll(self, expression, roll_function):
        """Animate the dice rolling"""
        # Show rolling animation
        self.result_label.configure(text="🎲 Rolling...")
        self.details_label.configure(text="")
        self.update()
        
        # Simulate rolling animation
        def animation():
            for i in range(3):
                time.sleep(0.1)
                self.result_label.configure(text=f"🎲 Rolling... {'.' * (i + 1)}")
                self.update()
            
            # Perform the actual roll
            roll_function()
            self.rolling = False
            
        # Run animation in separate thread to avoid blocking UI
        threading.Thread(target=animation, daemon=True).start()
        
    def perform_simple_roll(self, sides):
        """Perform a simple dice roll"""
        result = random.randint(1, sides)
        self.display_result(f"d{sides}", result, [result])
        
    def perform_custom_roll(self, expression):
        """Perform a custom dice roll"""
        try:
            result = self.parse_dice_expression(expression)
            self.display_result(expression, result, [])
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid dice expression: {str(e)}")
            self.rolling = False
            
    def parse_dice_expression(self, expression):
        """Parse dice expressions like '2d6+3', '1d20-2', etc."""
        # Remove spaces and convert to lowercase
        expr = expression.replace(' ', '').lower()
        
        # Pattern to match dice expressions
        pattern = r'^(\d*)d(\d+)([+-]\d+)?$'
        match = re.match(pattern, expr)
        
        if not match:
            raise ValueError("Invalid dice expression format")
        
        num_dice = int(match.group(1)) if match.group(1) else 1
        sides = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0
        
        if num_dice < 1 or sides < 1:
            raise ValueError("Number of dice and sides must be positive")
        
        # Roll the dice
        rolls = [random.randint(1, sides) for _ in range(num_dice)]
        total = sum(rolls) + modifier
        
        # Store detailed result
        roll_details = f"Rolls: {rolls}"
        if modifier != 0:
            roll_details += f", Modifier: {modifier:+d}"
        roll_details += f", Total: {total}"
        
        self.display_result(expression, total, rolls, roll_details)
        return total
        
    def display_result(self, expression, result, rolls, details=""):
        """Display the roll result with animation"""
        # Animate the result display
        self.result_label.configure(text=f"🎯 {result}")
        self.details_label.configure(text=details)
        
        # Add to history
        timestamp = time.strftime("%H:%M:%S")
        history_entry = f"[{timestamp}] {expression} = {result}"
        if details:
            history_entry += f" ({details})"
        
        self.roll_history.append(history_entry)
        self.update_history_display()
        
        # Highlight the result briefly
        self.result_label.configure(text_color="#ffd700")
        self.after(500, lambda: self.result_label.configure(text_color="#00ff88"))
        
    def update_history_display(self):
        """Update the history display"""
        self.history_text.delete("0.0", "end")
        for entry in self.roll_history[-15:]:  # Show last 15 rolls
            self.history_text.insert("end", entry + "\n")
        self.history_text.see("end")
        
    def clear_history(self):
        """Clear the roll history"""
        if messagebox.askyesno("Clear History", "Clear roll history?"):
            self.roll_history = []
            self.history_text.delete("0.0", "end")
            self.result_label.configure(text="Ready to roll!")
            self.details_label.configure(text="")
            
    def darken_color(self, color):
        """Darken a hex color for hover effects"""
        # Simple color darkening - you can improve this
        return "#" + "".join([hex(int(color[i:i+2], 16) // 2)[2:].zfill(2) for i in (1, 3, 5)])


# Keep the original class for backward compatibility
class DiceRollerApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("🎲 D&D Dice Roller")
        self.root.geometry("900x700")
        
        self.frame = DiceRollerFrame(self.root)
        self.frame.pack(fill='both', expand=True)
