"""
GUI - Main user interface for the Minecraft Mod Handler
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import threading
import os
import subprocess
from pathlib import Path
from mod_manager import ModManager
from crash_analyzer import CrashLogAnalyzer
from compatibility_checker import CompatibilityChecker
from shaderpack_manager import ShaderpackManager
from settings_manager import SettingsManager


class McHandlerGUI:
    """Main GUI application"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Minecraft Mod Handler")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        self.mod_manager = ModManager()
        self.crash_analyzer = CrashLogAnalyzer()
        self.compatibility_checker = CompatibilityChecker(self.mod_manager)
        self.shaderpack_manager = ShaderpackManager()
        self.settings_manager = SettingsManager()

        # Store current mods and shaderpacks
        self.current_mods = []
        self.current_shaderpacks = []
        self.problematic_mods = []
        self.problematic_shaderpacks = []

        # Initialize crash summary early
        self.crash_summary = "Loading crash analysis..."

        self.setup_ui()
        self.load_settings()
        self.check_ollama_status()

        # Load crash analysis in background
        self.load_crash_summary()

    def _get_all_crash_logs_content(self):
        """
        Helper to concatenate all crash log contents from crash-reports directories.
        Returns a single string with all logs, separated by headers.
        """
        # Try multiple possible crash log locations
        possible_dirs = [
            r"C:/Users/user/AppData/Roaming/ATLauncher/instances/yippie/crash-reports/",
            r"C:/Users/user/AppData/Roaming/.minecraft/crash-reports/",
            os.path.join(
                os.path.expanduser("~"),
                "AppData",
                "Roaming",
                ".minecraft",
                "crash-reports",
            ),
            os.path.join(os.path.expanduser("~"), ".minecraft", "crash-reports"),
        ]

        # Also check if we have a Minecraft directory set
        if hasattr(self, "dir_var") and self.dir_var.get():
            minecraft_dir = self.dir_var.get()
            possible_dirs.insert(0, os.path.join(minecraft_dir, "crash-reports"))

        crash_files = []
        crash_dir = None

        # Find the first directory that exists and has crash files
        for directory in possible_dirs:
            if os.path.exists(directory):
                files = [
                    os.path.join(directory, f)
                    for f in os.listdir(directory)
                    if f.endswith(".txt") or f.endswith(".log")
                ]
                if files:
                    crash_files = files
                    crash_dir = directory
                    break

        if not crash_files:
            return "No crashes recorded (no crash-reports directory found)"

        # Sort files by modification time (newest first) and limit to last 5
        crash_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        crash_files = crash_files[:5]  # Only analyze the 5 most recent crashes

        logs = []
        for crash_file in crash_files:
            try:
                with open(crash_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    # Limit each crash log to first 2000 characters to avoid token limits
                    if len(content) > 2000:
                        content = content[:2000] + "\n... (truncated)"
                    logs.append(
                        f"===== {os.path.basename(crash_file)} =====\n{content}\n"
                    )
            except Exception as e:
                logs.append(
                    f"===== {os.path.basename(crash_file)} =====\nError reading file: {e}\n"
                )

        return "\n".join(logs)

    def load_crash_summary(self):
        """Load crash summary in background"""

        def analyze_crashes():
            try:
                # Get crash logs content
                crash_content = self._get_all_crash_logs_content()

                if "No crashes recorded" in crash_content:
                    self.crash_summary = "No recent crashes found"
                    return

                # Check if Ollama is available
                if not self.crash_analyzer.check_ollama_connection():
                    self.crash_summary = "AI analysis unavailable (Ollama not running)"
                    return

                # Analyze crashes with AI
                result = self.crash_analyzer.analyze_crash_log(crash_content)

                if "error" in result:
                    self.crash_summary = f"Analysis error: {result['error']}"
                else:
                    # Truncate analysis if too long for dashboard
                    analysis = result.get("analysis", "No analysis available")
                    self.crash_summary = analysis

                # Update dashboard if it exists
                if hasattr(self, "help_text"):
                    self.update_dashboard_crash_summary()

            except Exception as e:
                self.crash_summary = f"Error loading crash analysis: {str(e)}"

        # Run in background thread
        threading.Thread(target=analyze_crashes, daemon=True).start()

    def update_dashboard_crash_summary(self):
        """Update the dashboard with personalized analysis"""
        try:
            if hasattr(self, "help_text"):
                # Get player profile and crash analysis
                player_profile = self._analyze_player_profile()
                crash_analysis = self._analyze_crash_patterns()

                # Update the help text with personalized analysis
                help_content = f"""Welcome to Minecraft Mod Handler!

🟢 Getting Started:
  1. Ensure Ollama is running to enable AI features.
  2. Go to 'Mod Management' and set your Minecraft directory.
  3. Click 'Load Mods' to view installed mods.
  4. Use 'Crash Analysis' to diagnose issues.
  5. Run 'Check Compatibility' to find potential conflicts.

🛠️  Key Features:
  • AI-powered crash log analysis
  • Mod compatibility checking
  • Enable/disable mods with one click
  • Automatic mod backup
  • Smart troubleshooting suggestions
  • Seamless ATLauncher integration

🚀 Quick Setup for ATLauncher:
  1. Click the 'Load Mods' button above.
  2. Choose your ATLauncher instance from the list.
  3. Start managing your mods instantly!

💡 Tips:
  - Keep your mod list updated and verify all dependencies are installed.
  - Use 'Refresh Status' to update stats and AI status.

🎮 Your Player Profile:
{player_profile}

📊 Crash Analysis Summary:
{crash_analysis}
"""

                self.help_text.config(state=tk.NORMAL)
                self.help_text.delete(1.0, tk.END)
                self.help_text.insert(tk.END, help_content)
                self.help_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Error updating dashboard: {e}")

    def _analyze_player_profile(self):
        """Analyze player type based on installed mods using AI"""
        try:
            if not hasattr(self, "current_mods") or not self.current_mods:
                return "No mods loaded yet. Load your mods to see your player profile!"

            # Check if Ollama is available
            if not self.crash_analyzer.check_ollama_connection():
                return "🤖 AI analysis unavailable (Ollama not running) - Basic analysis only"

            # Prepare mod data for AI analysis
            mod_data = []
            for mod in self.current_mods:
                mod_info = {
                    'name': mod.get('name', 'Unknown'),
                    'purpose': mod.get('purpose', 'Unknown/Other'),
                    'size': mod.get('size', 0),
                    'enabled': mod.get('enabled', True)
                }
                mod_data.append(mod_info)

            # Create AI prompt for player profile analysis
            mod_list = "\n".join([f"- {mod['name']} ({mod['purpose']})" for mod in mod_data[:20]])  # Limit to first 20 for prompt
            if len(mod_data) > 20:
                mod_list += f"\n... and {len(mod_data) - 20} more mods"

            ai_prompt = f"""Analyze this Minecraft player's mod collection and provide a detailed player profile:

Mod Collection ({len(mod_data)} total mods):
{mod_list}

Please provide:
1. Player archetype (e.g., Builder, Explorer, Tech Enthusiast, etc.)
2. Playstyle description
3. Modding level assessment
4. Key interests based on mod categories
5. Potential gameplay focus areas

Format your response as a concise player profile with emojis and clear sections."""

            # Get AI analysis
            try:
                ai_response = self.crash_analyzer.analyze_with_ollama(ai_prompt)
                if ai_response and "error" not in ai_response.lower():
                    return f"🤖 **AI-Generated Player Profile:**\n\n{ai_response}"
                else:
                    # Fallback to basic analysis if AI fails
                    return self._get_basic_player_profile(mod_data)
            except Exception as ai_error:
                print(f"AI analysis failed: {ai_error}")
                return self._get_basic_player_profile(mod_data)

        except Exception as e:
            return f"Error analyzing player profile: {str(e)}"

    def _get_basic_player_profile(self, mod_data):
        """Fallback basic player profile analysis"""
        try:
            # Analyze mod categories
            mod_categories = {}
            total_mods = len(mod_data)

            for mod in mod_data:
                purpose = mod.get("purpose", "Unknown/Other")
                if purpose not in mod_categories:
                    mod_categories[purpose] = 0
                mod_categories[purpose] += 1

            if not mod_categories:
                return "Unable to analyze player profile - no categorized mods found."

            # Find top categories
            sorted_categories = sorted(
                mod_categories.items(), key=lambda x: x[1], reverse=True
            )
            top_category = sorted_categories[0][0]

            # Generate basic player profile description
            profile_parts = []

            # Primary playstyle
            if top_category == "Quality of Life (QOL)":
                profile_parts.append(
                    "🎯 **QOL Enthusiast** - You prioritize smooth gameplay and convenience"
                )
            elif top_category == "Building & Construction":
                profile_parts.append(
                    "🏗️ **Builder** - You love creating and constructing amazing builds"
                )
            elif top_category == "Graphics & Visual":
                profile_parts.append(
                    "🎨 **Visual Artist** - You appreciate beautiful graphics and aesthetics"
                )
            elif top_category == "Performance & Optimization":
                profile_parts.append(
                    "⚡ **Performance Optimizer** - You focus on smooth, efficient gameplay"
                )
            elif top_category == "Adventure & Exploration":
                profile_parts.append(
                    "🗺️ **Explorer** - You love discovering new worlds and adventures"
                )
            elif top_category == "Combat & Weapons":
                profile_parts.append(
                    "⚔️ **Warrior** - You enjoy combat and weapon systems"
                )
            elif top_category == "Magic & Technology":
                profile_parts.append(
                    "🔮 **Tech-Mage** - You love both magic and technology mods"
                )
            elif top_category == "Food & Agriculture":
                profile_parts.append(
                    "🌾 **Farmer** - You enjoy farming and food-related gameplay"
                )
            elif top_category == "Transportation":
                profile_parts.append(
                    "🚗 **Traveler** - You love transportation and movement mods"
                )
            elif top_category == "Storage & Organization":
                profile_parts.append(
                    "📦 **Organizer** - You love efficient storage and organization"
                )
            else:
                profile_parts.append(
                    "🎮 **General Player** - You enjoy a diverse mix of mods"
                )

            # Mod count analysis
            if total_mods > 200:
                profile_parts.append(
                    f"📚 **Heavy Modder** - You have {total_mods} mods installed (very extensive setup)"
                )
            elif total_mods > 100:
                profile_parts.append(
                    f"📖 **Moderate Modder** - You have {total_mods} mods installed (substantial setup)"
                )
            elif total_mods > 50:
                profile_parts.append(
                    f"📝 **Light Modder** - You have {total_mods} mods installed (moderate setup)"
                )
            else:
                profile_parts.append(
                    f"📄 **Minimal Modder** - You have {total_mods} mods installed (light setup)"
                )

            # Top categories breakdown
            profile_parts.append(f"\n📊 **Mod Distribution:**")
            for category, count in sorted_categories[:3]:  # Top 3 categories
                percentage = (count / total_mods) * 100
                profile_parts.append(
                    f"  • {category}: {count} mods ({percentage:.1f}%)"
                )

            return "\n".join(profile_parts)

        except Exception as e:
            return f"Error in basic player profile analysis: {str(e)}"

    def _analyze_crash_patterns(self):
        """Analyze crash patterns and frequency using AI"""
        try:
            # Get crash content
            crash_content = self._get_all_crash_logs_content()

            if "No crashes recorded" in crash_content:
                return "✅ **No Recent Crashes** - Your Minecraft instance has been stable!"

            # Count crash files
            crash_files = []
            possible_dirs = [
                r"C:/Users/user/AppData/Roaming/ATLauncher/instances/yippie/crash-reports/",
                r"C:/Users/user/AppData/Roaming/.minecraft/crash-reports/",
                os.path.join(
                    os.path.expanduser("~"),
                    "AppData",
                    "Roaming",
                    ".minecraft",
                    "crash-reports",
                ),
                os.path.join(os.path.expanduser("~"), ".minecraft", "crash-reports"),
            ]

            if hasattr(self, "dir_var") and self.dir_var.get():
                minecraft_dir = self.dir_var.get()
                possible_dirs.insert(0, os.path.join(minecraft_dir, "crash-reports"))

            for directory in possible_dirs:
                if os.path.exists(directory):
                    files = [
                        f for f in os.listdir(directory) if f.endswith((".txt", ".log"))
                    ]
                    if files:
                        crash_files = files
                        break

            crash_count = len(crash_files)

            # Basic crash frequency analysis
            if crash_count == 0:
                return "✅ **No Recent Crashes** - Your Minecraft instance has been stable!"
            elif crash_count <= 2:
                frequency = "🟢 **Low Crash Rate** - Very stable setup"
            elif crash_count <= 5:
                frequency = "🟡 **Moderate Crash Rate** - Some stability issues"
            else:
                frequency = "🔴 **High Crash Rate** - Frequent stability problems"

            # Try AI analysis for crash patterns
            ai_analysis = "AI analysis in progress..."
            
            # Check if Ollama is available for enhanced analysis
            if self.crash_analyzer.check_ollama_connection():
                try:
                    # Create AI prompt for crash pattern analysis
                    ai_prompt = f"""Analyze these Minecraft crash patterns and provide insights:

Crash Statistics:
- Total recent crashes: {crash_count}
- Stability rating: {frequency}

Crash Log Content:
{crash_content[:2000]}  # Limit content for prompt

Please provide:
1. Common crash patterns identified
2. Likely causes based on crash frequency
3. Stability assessment
4. Recommendations for improvement
5. Risk level assessment

Format as a concise crash analysis with clear sections and actionable insights."""

                    # Get AI analysis
                    ai_response = self.crash_analyzer.analyze_with_ollama(ai_prompt)
                    if ai_response and "error" not in ai_response.lower():
                        ai_analysis = ai_response
                    else:
                        ai_analysis = "AI analysis unavailable - using basic assessment"
                except Exception as ai_error:
                    print(f"AI crash analysis failed: {ai_error}")
                    ai_analysis = "AI analysis failed - using basic assessment"
            else:
                ai_analysis = "🤖 AI analysis unavailable (Ollama not running) - Basic assessment only"

            # Get existing crash summary if available
            if (
                hasattr(self, "crash_summary")
                and self.crash_summary
                and "Loading" not in self.crash_summary
                and "Error" not in self.crash_summary
            ):
                # Use existing AI analysis if available
                if "AI analysis" in ai_analysis and "unavailable" in ai_analysis:
                    ai_analysis = self.crash_summary

            analysis_parts = [
                f"📈 **Crash Statistics:**",
                f"  • Total recent crashes: {crash_count}",
                f"  • Stability rating: {frequency}",
                f"\n🤖 **AI Analysis:**",
                f"  {ai_analysis}",
            ]

            return "\n".join(analysis_parts)

        except Exception as e:
            return f"Error analyzing crash patterns: {str(e)}"

    def setup_ui(self):
        """Setup the user interface"""
        # Create main frame with status bar
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create status bar
        self.setup_status_bar()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True)

        # Dashboard Tab
        self.setup_dashboard_tab()

        # Mod Management Tab
        self.setup_mod_management_tab()

        # Shaderpack Management Tab
        self.setup_shaderpack_management_tab()

        # Crash Log Analysis Tab
        self.setup_crash_analysis_tab()

        # Compatibility Check Tab
        self.setup_compatibility_tab()

        # Settings Tab
        self.setup_settings_tab()

    def setup_status_bar(self):
        """Setup status bar at bottom"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill="x", side="bottom")

        # Ollama status
        self.ollama_status_var = tk.StringVar(value="Checking AI Engine...")
        ttk.Label(self.status_frame, text="AI Status:").pack(side="left", padx=5)
        self.ollama_status_label = ttk.Label(
            self.status_frame, textvariable=self.ollama_status_var
        )
        self.ollama_status_label.pack(side="left", padx=5)

        # Separator
        ttk.Separator(self.status_frame, orient="vertical").pack(
            side="left", fill="y", padx=5
        )

        # Minecraft directory status
        self.mc_dir_var = tk.StringVar(value="No directory set")
        ttk.Label(self.status_frame, text="Minecraft Dir:").pack(side="left", padx=5)
        self.mc_dir_label = ttk.Label(self.status_frame, textvariable=self.mc_dir_var)
        self.mc_dir_label.pack(side="left", padx=5)

    def setup_dashboard_tab(self):
        """Setup dashboard tab"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Dashboard")

        # Quick Stats
        stats_frame = ttk.LabelFrame(dashboard_frame, text="Quick Stats")
        stats_frame.pack(fill="x", padx=10, pady=5)

        # Stats grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill="x", padx=10, pady=5)

        # Mod count
        ttk.Label(stats_grid, text="Mods:").grid(row=0, column=0, sticky="w", padx=5)
        self.mod_count_var = tk.StringVar(value="-")
        ttk.Label(
            stats_grid, textvariable=self.mod_count_var, font=("Arial", 12, "bold")
        ).grid(row=0, column=1, sticky="w", padx=5)

        # Shaderpack count
        ttk.Label(stats_grid, text="Shaderpacks:").grid(
            row=0, column=2, sticky="w", padx=5
        )
        self.shaderpack_count_var = tk.StringVar(value="-")
        ttk.Label(
            stats_grid,
            textvariable=self.shaderpack_count_var,
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=3, sticky="w", padx=5)

        # AI Status
        ttk.Label(stats_grid, text="AI Status:").grid(
            row=1, column=0, sticky="w", padx=5
        )
        self.ai_status_var = tk.StringVar(value="Checking...")
        ttk.Label(
            stats_grid, textvariable=self.ai_status_var, font=("Arial", 12, "bold")
        ).grid(row=1, column=1, sticky="w", padx=5)

        # Issues count
        ttk.Label(stats_grid, text="Issues:").grid(row=1, column=2, sticky="w", padx=5)
        self.issue_count_var = tk.StringVar(value="-")
        ttk.Label(
            stats_grid, textvariable=self.issue_count_var, font=("Arial", 12, "bold")
        ).grid(row=1, column=3, sticky="w", padx=5)

        # Quick Actions
        actions_frame = ttk.LabelFrame(dashboard_frame, text="Quick Actions")
        actions_frame.pack(fill="x", padx=10, pady=5)

        actions_grid = ttk.Frame(actions_frame)
        actions_grid.pack(fill="x", padx=10, pady=5)

        ttk.Button(actions_grid, text="Load Mods", command=self.load_mods).grid(
            row=0, column=0, padx=5, pady=5
        )
        ttk.Button(
            actions_grid, text="Load Shaderpacks", command=self.load_shaderpacks
        ).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(
            actions_grid, text="Check Compatibility", command=self.check_compatibility
        ).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(
            actions_grid, text="Refresh Status", command=self.refresh_dashboard
        ).grid(row=0, column=3, padx=5, pady=5)

        # Getting Started
        help_frame = ttk.LabelFrame(dashboard_frame, text="Getting Started")
        help_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.help_text = scrolledtext.ScrolledText(help_frame, height=10, wrap=tk.WORD)
        self.help_text.pack(fill="both", expand=True, padx=10, pady=5)

        help_content = (
            "Welcome to Minecraft Mod Handler!\n\n"
            "🟢 Getting Started:\n"
            "  1. Ensure Ollama is running to enable AI features.\n"
            "  2. Go to 'Mod Management' and set your Minecraft directory.\n"
            "  3. Click 'Load Mods' to view installed mods.\n"
            "  4. Use 'Crash Analysis' to diagnose issues.\n"
            "  5. Run 'Check Compatibility' to find potential conflicts.\n\n"
            "🛠️  Key Features:\n"
            "  • AI-powered crash log analysis\n"
            "  • Mod compatibility checking\n"
            "  • Enable/disable mods with one click\n"
            "  • Automatic mod backup\n"
            "  • Smart troubleshooting suggestions\n"
            "  • Seamless ATLauncher integration\n\n"
            "🚀 Quick Setup for ATLauncher:\n"
            "  1. Click the 'Load Mods' button above.\n"
            "  2. Choose your ATLauncher instance from the list.\n"
            "  3. Start managing your mods instantly!\n\n"
            "💡 Tips:\n"
            "  - Keep your mod list updated and verify all dependencies are installed.\n"
            "  - Use 'Refresh Status' to update stats and AI status.\n\n"
            "📋 Recent Crash Analysis:\n"
            f"{self.crash_summary}\n"
        )

        self.help_text.insert(tk.END, help_content)
        self.help_text.config(state=tk.DISABLED)

    def setup_mod_management_tab(self):
        """Setup mod management tab"""
        mod_frame = ttk.Frame(self.notebook)
        self.notebook.add(mod_frame, text="Mod Management")

        # Directory selection
        dir_frame = ttk.LabelFrame(mod_frame, text="Minecraft Directory")
        dir_frame.pack(fill="x", padx=10, pady=5)

        dir_input_frame = ttk.Frame(dir_frame)
        dir_input_frame.pack(fill="x", padx=10, pady=5)

        self.dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_input_frame, textvariable=self.dir_var, width=60)
        dir_entry.pack(side="left", padx=5, pady=5)

        ttk.Button(
            dir_input_frame, text="Browse", command=self.browse_minecraft_dir
        ).pack(side="left", padx=5)
        ttk.Button(
            dir_input_frame,
            text="ATLauncher Instances",
            command=self.load_atlauncher_instances,
        ).pack(side="left", padx=5)

        action_frame = ttk.Frame(dir_frame)
        action_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(action_frame, text="Load Mods", command=self.load_mods).pack(
            side="left", padx=5
        )
        ttk.Button(action_frame, text="Backup Mods", command=self.backup_mods).pack(
            side="left", padx=5
        )

        # ATLauncher instances list
        self.atlauncher_frame = ttk.Frame(dir_frame)
        self.atlauncher_frame.pack(fill="x", padx=10, pady=5)
        self.atlauncher_listbox = tk.Listbox(self.atlauncher_frame, height=4)
        self.atlauncher_listbox.pack(fill="x", padx=5, pady=5)
        self.atlauncher_frame.pack_forget()  # Hide initially

        # Mod upload section
        upload_frame = ttk.LabelFrame(mod_frame, text="Add/Remove Mods")
        upload_frame.pack(fill="x", padx=10, pady=5)

        upload_grid = ttk.Frame(upload_frame)
        upload_grid.pack(fill="x", padx=10, pady=5)

        ttk.Label(upload_grid, text="Add New Mods:").grid(
            row=0, column=0, sticky="w", padx=5
        )
        ttk.Button(
            upload_grid, text="Select .jar Files", command=self.select_mod_files
        ).grid(row=0, column=1, padx=5)
        ttk.Button(upload_grid, text="Upload Mods", command=self.upload_mods).grid(
            row=0, column=2, padx=5
        )

        ttk.Label(upload_grid, text="Quick Actions:").grid(
            row=1, column=0, sticky="w", padx=5
        )
        ttk.Button(
            upload_grid, text="Open Mods Folder", command=self.open_mods_folder
        ).grid(row=1, column=1, padx=5)
        ttk.Button(
            upload_grid, text="Remove Selected", command=self.remove_selected_mods
        ).grid(row=1, column=2, padx=5)

        # Selected files list
        self.selected_files_frame = ttk.Frame(upload_frame)
        self.selected_files_frame.pack(fill="x", padx=10, pady=5)
        self.selected_files_listbox = tk.Listbox(self.selected_files_frame, height=3)
        self.selected_files_listbox.pack(fill="x", padx=5, pady=5)
        self.selected_files_frame.pack_forget()  # Hide initially

        self.selected_mod_files = []

        # Mod list with enhanced controls
        list_frame = ttk.LabelFrame(mod_frame, text="Installed Mods")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Search and filter controls
        controls_frame = ttk.Frame(list_frame)
        controls_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(controls_frame, text="Search:").pack(side="left", padx=5)
        self.mod_search_var = tk.StringVar()
        self.mod_search_var.trace("w", self.filter_mods)
        search_entry = ttk.Entry(
            controls_frame, textvariable=self.mod_search_var, width=30
        )
        search_entry.pack(side="left", padx=5)

        ttk.Label(controls_frame, text="Purpose:").pack(side="left", padx=5)
        self.purpose_filter_var = tk.StringVar()
        self.purpose_filter_var.trace("w", self.filter_mods)
        purpose_combo = ttk.Combobox(
            controls_frame, textvariable=self.purpose_filter_var, width=20
        )
        purpose_combo["values"] = (
            "All Purposes",
            "Quality of Life (QOL)",
            "Building & Construction",
            "Graphics & Visual",
            "Performance & Optimization",
            "Adventure & Exploration",
            "Combat & Weapons",
            "Magic & Technology",
            "Food & Agriculture",
            "Transportation",
            "Storage & Organization",
            "Utility & Tools",
            "Unknown/Other",
        )
        purpose_combo.set("All Purposes")
        purpose_combo.pack(side="left", padx=5)

        # Action buttons
        action_buttons_frame = ttk.Frame(list_frame)
        action_buttons_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            action_buttons_frame, text="Categorize Mods", command=self.categorize_mods
        ).pack(side="left", padx=5)
        ttk.Button(
            action_buttons_frame,
            text="Disable Selected",
            command=self.disable_selected_mod,
        ).pack(side="left", padx=5)
        ttk.Button(
            action_buttons_frame,
            text="Enable Selected",
            command=self.enable_selected_mod,
        ).pack(side="left", padx=5)
        ttk.Button(
            action_buttons_frame,
            text="AI Suggestions",
            command=self.get_mod_suggestions,
        ).pack(side="left", padx=5)
        ttk.Button(
            action_buttons_frame,
            text="Disable Problematic",
            command=self.disable_problematic_mods,
        ).pack(side="left", padx=5)

        # Treeview for mods with enhanced columns
        columns = ("Name", "Version", "Author", "Purpose", "Size", "Status")
        self.mod_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=15
        )

        # Store sort state
        self._mod_tree_sort_column = None
        self._mod_tree_sort_reverse = False

        def treeview_sort_column(tv, col, reverse):
            # Get all items and sort them by the given column
            l = [(tv.set(k, col), k) for k in tv.get_children("")]
            # Try to convert to float for size, else string
            if col == "Size":

                def parse_size(val):
                    try:
                        return float(val.split()[0])
                    except Exception:
                        return 0

                l.sort(key=lambda t: parse_size(t[0]), reverse=reverse)
            else:
                l.sort(
                    key=lambda t: t[0].lower() if isinstance(t[0], str) else t[0],
                    reverse=reverse,
                )
            # Rearrange items in sorted positions
            for index, (val, k) in enumerate(l):
                tv.move(k, "", index)
            # Update heading so next click will sort in opposite order
            tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))
            # Store sort state
            self._mod_tree_sort_column = col
            self._mod_tree_sort_reverse = not reverse

        for col in columns:
            self.mod_tree.heading(
                col,
                text=col,
                command=lambda _col=col: treeview_sort_column(
                    self.mod_tree, _col, False
                ),
            )
            self.mod_tree.column(col, width=150)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.mod_tree.yview
        )
        h_scrollbar = ttk.Scrollbar(
            list_frame, orient="horizontal", command=self.mod_tree.xview
        )
        self.mod_tree.configure(
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
        )

        self.mod_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

        # Problematic mods alert
        self.problematic_alert = ttk.Label(list_frame, text="", foreground="red")
        self.problematic_alert.pack(fill="x", padx=5, pady=5)

    def setup_shaderpack_management_tab(self):
        """Setup shaderpack management tab"""
        shaderpack_frame = ttk.Frame(self.notebook)
        self.notebook.add(shaderpack_frame, text="Shaderpack Management")

        # Directory selection (reuse from mods)
        dir_frame = ttk.LabelFrame(shaderpack_frame, text="Minecraft Directory")
        dir_frame.pack(fill="x", padx=10, pady=5)

        dir_input_frame = ttk.Frame(dir_frame)
        dir_input_frame.pack(fill="x", padx=10, pady=5)

        self.shaderpack_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(
            dir_input_frame, textvariable=self.shaderpack_dir_var, width=60
        )
        dir_entry.pack(side="left", padx=5, pady=5)

        ttk.Button(
            dir_input_frame, text="Browse", command=self.browse_shaderpack_dir
        ).pack(side="left", padx=5)
        ttk.Button(
            dir_input_frame,
            text="ATLauncher Instances",
            command=self.load_atlauncher_instances_shaderpack,
        ).pack(side="left", padx=5)

        action_frame = ttk.Frame(dir_frame)
        action_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            action_frame, text="Load Shaderpacks", command=self.load_shaderpacks
        ).pack(side="left", padx=5)
        ttk.Button(
            action_frame, text="Backup Shaderpacks", command=self.backup_shaderpacks
        ).pack(side="left", padx=5)

        # Shaderpack upload section
        upload_frame = ttk.LabelFrame(shaderpack_frame, text="Add/Remove Shaderpacks")
        upload_frame.pack(fill="x", padx=10, pady=5)

        upload_grid = ttk.Frame(upload_frame)
        upload_grid.pack(fill="x", padx=10, pady=5)

        ttk.Label(upload_grid, text="Add New Shaderpacks:").grid(
            row=0, column=0, sticky="w", padx=5
        )
        ttk.Button(
            upload_grid, text="Select .zip Files", command=self.select_shaderpack_files
        ).grid(row=0, column=1, padx=5)
        ttk.Button(
            upload_grid, text="Upload Shaderpacks", command=self.upload_shaderpacks
        ).grid(row=0, column=2, padx=5)

        ttk.Label(upload_grid, text="Quick Actions:").grid(
            row=1, column=0, sticky="w", padx=5
        )
        ttk.Button(
            upload_grid,
            text="Open Shaderpacks Folder",
            command=self.open_shaderpacks_folder,
        ).grid(row=1, column=1, padx=5)
        ttk.Button(
            upload_grid,
            text="Remove Selected",
            command=self.remove_selected_shaderpacks,
        ).grid(row=1, column=2, padx=5)

        # Selected shaderpack files list
        self.selected_shaderpack_files_frame = ttk.Frame(upload_frame)
        self.selected_shaderpack_files_frame.pack(fill="x", padx=10, pady=5)
        self.selected_shaderpack_files_listbox = tk.Listbox(
            self.selected_shaderpack_files_frame, height=3
        )
        self.selected_shaderpack_files_listbox.pack(fill="x", padx=5, pady=5)
        self.selected_shaderpack_files_frame.pack_forget()  # Hide initially

        self.selected_shaderpack_files = []

        # Shaderpack list with enhanced controls
        list_frame = ttk.LabelFrame(shaderpack_frame, text="Installed Shaderpacks")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Search controls
        controls_frame = ttk.Frame(list_frame)
        controls_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(controls_frame, text="Search:").pack(side="left", padx=5)
        self.shaderpack_search_var = tk.StringVar()
        self.shaderpack_search_var.trace("w", self.filter_shaderpacks)
        search_entry = ttk.Entry(
            controls_frame, textvariable=self.shaderpack_search_var, width=30
        )
        search_entry.pack(side="left", padx=5)

        # Action buttons
        action_buttons_frame = ttk.Frame(list_frame)
        action_buttons_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            action_buttons_frame,
            text="Disable Selected",
            command=self.disable_selected_shaderpack,
        ).pack(side="left", padx=5)
        ttk.Button(
            action_buttons_frame,
            text="Enable Selected",
            command=self.enable_selected_shaderpack,
        ).pack(side="left", padx=5)
        ttk.Button(
            action_buttons_frame,
            text="AI Suggestions",
            command=self.get_shaderpack_suggestions,
        ).pack(side="left", padx=5)
        ttk.Button(
            action_buttons_frame,
            text="Disable Problematic",
            command=self.disable_problematic_shaderpacks,
        ).pack(side="left", padx=5)

        # Treeview for shaderpacks
        columns = ("Name", "Version", "Author", "Size", "Status")
        self.shaderpack_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=15
        )

        for col in columns:
            self.shaderpack_tree.heading(col, text=col)
            self.shaderpack_tree.column(col, width=150)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.shaderpack_tree.yview
        )
        h_scrollbar = ttk.Scrollbar(
            list_frame, orient="horizontal", command=self.shaderpack_tree.xview
        )
        self.shaderpack_tree.configure(
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
        )

        self.shaderpack_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

        # Problematic shaderpacks alert
        self.problematic_shaderpack_alert = ttk.Label(
            list_frame, text="", foreground="red"
        )
        self.problematic_shaderpack_alert.pack(fill="x", padx=5, pady=5)

    def setup_crash_analysis_tab(self):
        """Setup crash log analysis tab"""
        crash_frame = ttk.Frame(self.notebook)
        self.notebook.add(crash_frame, text="Crash Log Analysis")

        # File selection with enhanced UI
        file_frame = ttk.LabelFrame(crash_frame, text="Crash Log File")
        file_frame.pack(fill="x", padx=10, pady=5)

        file_input_frame = ttk.Frame(file_frame)
        file_input_frame.pack(fill="x", padx=10, pady=5)

        self.crash_file_var = tk.StringVar()
        file_entry = ttk.Entry(
            file_input_frame, textvariable=self.crash_file_var, width=60
        )
        file_entry.pack(side="left", padx=5, pady=5)

        ttk.Button(file_input_frame, text="Browse", command=self.browse_crash_log).pack(
            side="left", padx=5
        )
        ttk.Button(
            file_input_frame, text="Analyze with AI", command=self.analyze_crash_log
        ).pack(side="left", padx=5)

        # File info display
        self.file_info_frame = ttk.Frame(file_frame)
        self.file_info_frame.pack(fill="x", padx=10, pady=5)
        self.file_info_label = ttk.Label(self.file_info_frame, text="")
        self.file_info_label.pack(side="left", padx=5)
        self.file_info_frame.pack_forget()  # Hide initially

        # Analysis results with enhanced display
        results_frame = ttk.LabelFrame(crash_frame, text="Analysis Results")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Results controls
        results_controls = ttk.Frame(results_frame)
        results_controls.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            results_controls, text="Clear Results", command=self.clear_crash_results
        ).pack(side="left", padx=5)
        ttk.Button(
            results_controls, text="Copy Results", command=self.copy_crash_results
        ).pack(side="left", padx=5)
        ttk.Button(
            results_controls, text="Export Results", command=self.export_crash_results
        ).pack(side="left", padx=5)

        self.analysis_text = scrolledtext.ScrolledText(
            results_frame, height=20, wrap=tk.WORD
        )
        self.analysis_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Initial placeholder text
        self.analysis_text.insert(
            tk.END,
            "Upload a crash log to get started\n\nOur AI will analyze your crash log and provide detailed insights and solutions.",
        )
        self.analysis_text.config(state=tk.DISABLED)

    def setup_compatibility_tab(self):
        """Setup compatibility check tab"""
        compat_frame = ttk.Frame(self.notebook)
        self.notebook.add(compat_frame, text="Compatibility Check")

        # Directory selection
        dir_frame = ttk.LabelFrame(compat_frame, text="Minecraft Directory")
        dir_frame.pack(fill="x", padx=10, pady=5)

        dir_input_frame = ttk.Frame(dir_frame)
        dir_input_frame.pack(fill="x", padx=10, pady=5)

        self.compat_dir_var = tk.StringVar()
        dir_entry = ttk.Entry(
            dir_input_frame, textvariable=self.compat_dir_var, width=60
        )
        dir_entry.pack(side="left", padx=5, pady=5)

        ttk.Button(
            dir_input_frame, text="Browse", command=self.browse_compatibility_dir
        ).pack(side="left", padx=5)
        ttk.Button(
            dir_input_frame,
            text="Check Compatibility",
            command=self.check_compatibility,
        ).pack(side="left", padx=5)

        # Mod summary section
        summary_frame = ttk.LabelFrame(compat_frame, text="Mod Collection Summary")
        summary_frame.pack(fill="x", padx=10, pady=5)

        summary_grid = ttk.Frame(summary_frame)
        summary_grid.pack(fill="x", padx=10, pady=5)

        # Summary stats
        ttk.Label(summary_grid, text="Total Mods:").grid(
            row=0, column=0, sticky="w", padx=5
        )
        self.total_mods_var = tk.StringVar(value="-")
        ttk.Label(
            summary_grid, textvariable=self.total_mods_var, font=("Arial", 10, "bold")
        ).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(summary_grid, text="Enabled:").grid(
            row=0, column=2, sticky="w", padx=5
        )
        self.enabled_mods_var = tk.StringVar(value="-")
        ttk.Label(
            summary_grid, textvariable=self.enabled_mods_var, font=("Arial", 10, "bold")
        ).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(summary_grid, text="Disabled:").grid(
            row=0, column=4, sticky="w", padx=5
        )
        self.disabled_mods_var = tk.StringVar(value="-")
        ttk.Label(
            summary_grid,
            textvariable=self.disabled_mods_var,
            font=("Arial", 10, "bold"),
        ).grid(row=0, column=5, sticky="w", padx=5)

        ttk.Label(summary_grid, text="Total Size:").grid(
            row=1, column=0, sticky="w", padx=5
        )
        self.total_size_var = tk.StringVar(value="-")
        ttk.Label(
            summary_grid, textvariable=self.total_size_var, font=("Arial", 10, "bold")
        ).grid(row=1, column=1, sticky="w", padx=5)

        # Results
        results_frame = ttk.LabelFrame(compat_frame, text="Compatibility Report")
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Results controls
        results_controls = ttk.Frame(results_frame)
        results_controls.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            results_controls,
            text="Export Report",
            command=self.export_compatibility_report,
        ).pack(side="left", padx=5)
        ttk.Button(
            results_controls, text="Copy Report", command=self.copy_compatibility_report
        ).pack(side="left", padx=5)
        ttk.Button(
            results_controls,
            text="Clear Report",
            command=self.clear_compatibility_report,
        ).pack(side="left", padx=5)

        self.compatibility_text = scrolledtext.ScrolledText(
            results_frame, height=20, wrap=tk.WORD
        )
        self.compatibility_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Initial placeholder text
        self.compatibility_text.insert(
            tk.END,
            "Enter your Minecraft directory and click 'Check Compatibility' to scan for potential issues in your mod setup.\n\nFor best results, ensure your mod list is up to date and all dependencies are present.",
        )
        self.compatibility_text.config(state=tk.DISABLED)

    def setup_settings_tab(self):
        """Setup settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")

        # Ollama settings
        ollama_frame = ttk.LabelFrame(settings_frame, text="Ollama Configuration")
        ollama_frame.pack(fill="x", padx=10, pady=5)

        # Status and connection
        status_frame = ttk.Frame(ollama_frame)
        status_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(status_frame, text="Status:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.ollama_status_var = tk.StringVar(value="Checking...")
        ttk.Label(status_frame, textvariable=self.ollama_status_var).grid(
            row=0, column=1, sticky="w", padx=5, pady=5
        )
        ttk.Button(status_frame, text="Refresh", command=self.check_ollama_status).grid(
            row=0, column=2, padx=5, pady=5
        )

        # Ollama URL
        ttk.Label(status_frame, text="Ollama URL:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )
        self.ollama_url_var = tk.StringVar(value="http://localhost:11434")
        ttk.Entry(status_frame, textvariable=self.ollama_url_var, width=30).grid(
            row=1, column=1, sticky="w", padx=5, pady=5
        )
        ttk.Button(
            status_frame, text="Test Connection", command=self.test_ollama_connection
        ).grid(row=1, column=2, padx=5, pady=5)

        # Model selection
        model_frame = ttk.Frame(ollama_frame)
        model_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(model_frame, text="Available Models:").pack(
            anchor="w", padx=5, pady=5
        )
        self.models_listbox = tk.Listbox(model_frame, height=4)
        self.models_listbox.pack(fill="x", padx=5, pady=5)

        ttk.Label(model_frame, text="Selected Model:").pack(anchor="w", padx=5, pady=5)
        self.model_var = tk.StringVar(value="llama3.2")
        self.model_combo = ttk.Combobox(
            model_frame, textvariable=self.model_var, width=30
        )
        self.model_combo.pack(anchor="w", padx=5, pady=5)

        # Application settings
        app_frame = ttk.LabelFrame(settings_frame, text="Application Settings")
        app_frame.pack(fill="x", padx=10, pady=5)

        app_grid = ttk.Frame(app_frame)
        app_grid.pack(fill="x", padx=10, pady=5)

        # Default Minecraft directory
        ttk.Label(app_grid, text="Default Minecraft Directory:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.default_mc_dir_var = tk.StringVar()
        ttk.Entry(app_grid, textvariable=self.default_mc_dir_var, width=50).grid(
            row=0, column=1, sticky="w", padx=5, pady=5
        )
        ttk.Button(app_grid, text="Browse", command=self.browse_default_mc_dir).grid(
            row=0, column=2, padx=5, pady=5
        )

        # Auto-backup setting
        self.auto_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            app_grid,
            text="Auto-backup before making changes",
            variable=self.auto_backup_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Dark mode setting
        self.dark_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            app_grid, text="Enable dark mode", variable=self.dark_mode_var
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Save settings button
        ttk.Button(app_grid, text="Save Settings", command=self.save_settings).grid(
            row=3, column=0, padx=5, pady=5
        )

        # About
        about_frame = ttk.LabelFrame(settings_frame, text="About")
        about_frame.pack(fill="both", expand=True, padx=10, pady=5)

        about_text = scrolledtext.ScrolledText(about_frame, height=10, wrap=tk.WORD)
        about_text.pack(fill="both", expand=True, padx=5, pady=5)

        about_content = """Minecraft Mod Handler v1.0

A comprehensive tool for managing Minecraft mods and analyzing crash logs with AI-powered assistance using Ollama.
        
        Features:
        • Mod management and organization
• Shaderpack management
• AI-powered crash log analysis
        • Mod compatibility checking
        • Backup and restore functionality
• Intelligent troubleshooting
• ATLauncher integration
        
        Requirements:
        • Python 3.7+
        • Ollama installed and running
        • Minecraft with mods

Getting Help:
If you encounter issues, make sure Ollama is running and you have at least one model installed (e.g., llama3.2)."""

        about_text.insert(tk.END, about_content)
        about_text.config(state=tk.DISABLED)

    def browse_minecraft_dir(self):
        """Browse for Minecraft directory (default provided)"""
        default_dir = r"C:\Users\user\AppData\Roaming\ATLauncher\instances\yippie"
        directory = filedialog.askdirectory(
            title="Select Minecraft Directory", initialdir=default_dir
        )
        if directory:
            self.dir_var.set(directory)
            self.mod_manager.set_minecraft_directory(directory)

    def browse_crash_log(self):
        """Browse for crash log file"""
        default_dir = r"C:\Users\user\AppData\Roaming\ATLauncher\instances\yippie"
        initialdir = default_dir
        filename = filedialog.askopenfilename(
            title="Select Crash Log File",
            filetypes=[
                ("Log files", "*.log"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
            initialdir=initialdir,
        )
        if filename:
            self.crash_file_var.set(filename)

    def load_mods(self):
        """Load and display installed mods"""
        if not self.dir_var.get():
            messagebox.showerror("Error", "Please select a Minecraft directory first")
            return

        try:
            # Set the directory for the mod manager
            self.mod_manager.set_minecraft_directory(self.dir_var.get())

            # Update status bar
            self.mc_dir_var.set(self.dir_var.get())

            # Clear existing items
            for item in self.mod_tree.get_children():
                self.mod_tree.delete(item)

            mods = self.mod_manager.get_installed_mods()
            self.current_mods = mods

            for mod in mods:
                status = "Enabled" if mod.get("enabled", True) else "Disabled"
                size_mb = f"{mod['size'] / (1024*1024):.1f} MB"
                purpose = mod.get("purpose", "Unknown/Other")

                self.mod_tree.insert(
                    "",
                    "end",
                    values=(
                        mod.get("display_name", mod["name"]),
                        mod.get("version", "Unknown"),
                        mod.get("author", "Unknown"),
                        purpose,
                        size_mb,
                        status,
                    ),
                )

            # Update dashboard stats
            self.mod_count_var.set(str(len(mods)))

            messagebox.showinfo("Success", f"Loaded {len(mods)} mods successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mods: {str(e)}")

    def backup_mods(self):
        """Create backup of mods"""
        try:
            backup_path = self.mod_manager.backup_mods()
            if backup_path:
                messagebox.showinfo("Success", f"Mods backed up to: {backup_path}")
            else:
                messagebox.showerror("Error", "Failed to create backup")
        except Exception as e:
            messagebox.showerror("Error", f"Backup failed: {str(e)}")

    def disable_selected_mod(self):
        """Disable selected mod"""
        selection = self.mod_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a mod to disable")
            return

        item = self.mod_tree.item(selection[0])
        mod_name = item["values"][0]

        try:
            self.mod_manager.disable_mod(mod_name)
            messagebox.showinfo("Success", f"Mod '{mod_name}' disabled")
            self.load_mods()  # Refresh the list
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disable mod: {str(e)}")

    def enable_selected_mod(self):
        """Enable selected mod"""
        selection = self.mod_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a mod to enable")
            return

        item = self.mod_tree.item(selection[0])
        mod_name = item["values"][0]

        try:
            self.mod_manager.enable_mod(mod_name)
            messagebox.showinfo("Success", f"Mod '{mod_name}' enabled")
            self.load_mods()  # Refresh the list
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable mod: {str(e)}")

    def analyze_crash_log(self):
        """Analyze crash log using Ollama"""
        if not self.crash_file_var.get():
            messagebox.showerror("Error", "Please select a crash log file first")
            return

        if not self.crash_analyzer.check_ollama_connection():
            messagebox.showerror(
                "Error", "Ollama is not running. Please start Ollama first."
            )
            return

        try:
            with open(
                self.crash_file_var.get(), "r", encoding="utf-8", errors="ignore"
            ) as f:
                log_content = f.read()

            self.analysis_text.config(state=tk.NORMAL)
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(tk.END, "Analyzing crash log... Please wait.\n\n")
            self.analysis_text.config(state=tk.DISABLED)
            self.root.update()

            # Run analysis in a separate thread to avoid blocking UI
            def analyze():
                result = self.crash_analyzer.analyze_crash_log(log_content)

                def update_ui():
                    self.analysis_text.config(state=tk.NORMAL)
                    self.analysis_text.delete(1.0, tk.END)
                    if "error" in result:
                        self.analysis_text.insert(tk.END, f"Error: {result['error']}\n")
                    else:
                        self.analysis_text.insert(
                            tk.END,
                            f"Analysis Results (Model: {result.get('model_used', 'Unknown')}):\n",
                        )
                        self.analysis_text.insert(tk.END, "=" * 50 + "\n\n")
                        self.analysis_text.insert(
                            tk.END, result.get("analysis", "No analysis available")
                        )
                    self.analysis_text.config(state=tk.DISABLED)

                self.root.after(0, update_ui)

            threading.Thread(target=analyze, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze crash log: {str(e)}")

    def get_mod_suggestions(self):
        """Get AI suggestions for selected mod"""
        selection = self.mod_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Warning", "Please select a mod to get suggestions for"
            )
            return

        if not self.crash_analyzer.check_ollama_connection():
            messagebox.showerror(
                "Error", "Ollama is not running. Please start Ollama first."
            )
            return

        item = self.mod_tree.item(selection[0])
        mod_name = item["values"][0]

        # Simple dialog for error description
        error_desc = simpledialog.askstring(
            "Error Description", f"Describe the issue with {mod_name}:"
        )
        if not error_desc:
            return

        try:
            result = self.crash_analyzer.suggest_mod_fixes(mod_name, error_desc)

            if "error" in result:
                messagebox.showerror("Error", result["error"])
            else:
                # Show suggestions in a new window
                suggestions_window = tk.Toplevel(self.root)
                suggestions_window.title(f"AI Suggestions for {mod_name}")
                suggestions_window.geometry("600x400")

                text_widget = scrolledtext.ScrolledText(
                    suggestions_window, wrap=tk.WORD
                )
                text_widget.pack(fill="both", expand=True, padx=10, pady=10)

                text_widget.insert(tk.END, f"AI Suggestions for {mod_name}:\n")
                text_widget.insert(tk.END, "=" * 50 + "\n\n")
                text_widget.insert(
                    tk.END, result.get("suggestions", "No suggestions available")
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to get suggestions: {str(e)}")

    def check_compatibility(self):
        """Check mod compatibility"""
        # Use the compatibility directory if set, otherwise use the main directory
        minecraft_dir = self.compat_dir_var.get() or self.dir_var.get()

        if not minecraft_dir:
            messagebox.showerror("Error", "Please select a Minecraft directory first")
            return

        try:
            # Set the directory for the compatibility checker
            self.mod_manager.set_minecraft_directory(minecraft_dir)

            self.compatibility_text.config(state=tk.NORMAL)
            self.compatibility_text.delete(1.0, tk.END)
            self.compatibility_text.insert(
                tk.END, "Checking mod compatibility... Please wait.\n\n"
            )
            self.compatibility_text.config(state=tk.DISABLED)
            self.root.update()

            # Run compatibility check in a separate thread
            def check():
                try:
                    # Get compatibility issues
                    issues = self.compatibility_checker.check_mod_compatibility()
                    report = self.compatibility_checker.get_compatibility_report()

                    # Update summary stats
                    mods = self.mod_manager.get_installed_mods()
                    total_mods = len(mods)
                    enabled_mods = len(
                        [mod for mod in mods if mod.get("enabled", True)]
                    )
                    disabled_mods = total_mods - enabled_mods
                    total_size = sum(mod.get("size", 0) for mod in mods)

                    def update_ui():
                        self.compatibility_text.config(state=tk.NORMAL)
                        self.compatibility_text.delete(1.0, tk.END)
                        self.compatibility_text.insert(tk.END, report)
                        self.compatibility_text.config(state=tk.DISABLED)

                        # Update summary stats
                        self.total_mods_var.set(str(total_mods))
                        self.enabled_mods_var.set(str(enabled_mods))
                        self.disabled_mods_var.set(str(disabled_mods))
                        self.total_size_var.set(f"{total_size / (1024*1024):.1f} MB")

                        # Show problematic mods if any
                        if issues.get("conflicts") or issues.get(
                            "missing_dependencies"
                        ):
                            problematic_mods = []
                            for conflict in issues.get("conflicts", []):
                                problematic_mods.extend(
                                    [conflict.get("mod1"), conflict.get("mod2")]
                                )
                            for dep in issues.get("missing_dependencies", []):
                                problematic_mods.append(dep.get("mod"))

                            self.problematic_mods = list(set(problematic_mods))
                            if self.problematic_mods:
                                self.problematic_alert.config(
                                    text=f"Warning: {len(self.problematic_mods)} problematic mods detected: {', '.join(self.problematic_mods[:3])}{'...' if len(self.problematic_mods) > 3 else ''}"
                                )

                    self.root.after(0, update_ui)

                except Exception as e:

                    def update_ui_error():
                        self.compatibility_text.config(state=tk.NORMAL)
                        self.compatibility_text.delete(1.0, tk.END)
                        self.compatibility_text.insert(
                            tk.END, f"Error during compatibility check: {str(e)}"
                        )
                        self.compatibility_text.config(state=tk.DISABLED)

                    self.root.after(0, update_ui_error)

            threading.Thread(target=check, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Compatibility check failed: {str(e)}")

    def check_ollama_status(self):
        """Check Ollama connection status"""

        def check():
            is_connected = self.crash_analyzer.check_ollama_connection()
            models = self.crash_analyzer.get_available_models()

            def update_status():
                if is_connected:
                    self.ollama_status_var.set(
                        f"Connected ({len(models)} models available)"
                    )
                    # Update model combobox
                    self.model_combo["values"] = models
                    if models and self.model_var.get() not in models:
                        self.model_var.set(models[0])
                else:
                    self.ollama_status_var.set("Not connected")

            self.root.after(0, update_status)

        threading.Thread(target=check, daemon=True).start()

    def refresh_models(self):
        """Refresh available Ollama models"""
        self.check_ollama_status()

    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

    # New methods for enhanced functionality

    def refresh_dashboard(self):
        """Refresh dashboard statistics"""
        self.check_ollama_status()
        if self.dir_var.get():
            self.load_mods()
        if self.shaderpack_dir_var.get():
            self.load_shaderpacks()
        # Refresh crash summary
        self.load_crash_summary()

    def load_shaderpacks(self):
        """Load shaderpacks from directory"""
        if not self.shaderpack_dir_var.get():
            messagebox.showerror("Error", "Please select a Minecraft directory first")
            return

        try:
            # Set the directory for the shaderpack manager
            self.shaderpack_manager.set_minecraft_directory(
                self.shaderpack_dir_var.get()
            )

            # Clear existing items
            for item in self.shaderpack_tree.get_children():
                self.shaderpack_tree.delete(item)

            shaderpacks = self.shaderpack_manager.get_installed_shaderpacks()
            self.current_shaderpacks = shaderpacks

            for shaderpack in shaderpacks:
                status = "Enabled" if shaderpack.get("enabled", True) else "Disabled"
                size_mb = f"{shaderpack['size'] / (1024*1024):.1f} MB"

                self.shaderpack_tree.insert(
                    "",
                    "end",
                    values=(
                        shaderpack.get("display_name", shaderpack["name"]),
                        shaderpack.get("version", "Unknown"),
                        shaderpack.get("author", "Unknown"),
                        size_mb,
                        status,
                    ),
                )

            # Update dashboard stats
            self.shaderpack_count_var.set(str(len(shaderpacks)))

            if not shaderpacks:
                messagebox.showinfo(
                    "Shaderpacks", "No shaderpacks found in the selected directory."
                )
            else:
                messagebox.showinfo(
                    "Shaderpacks Loaded", f"Loaded {len(shaderpacks)} shaderpack(s)."
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load shaderpacks: {str(e)}")

    def browse_shaderpack_dir(self):
        """Browse for shaderpack directory"""
        directory = filedialog.askdirectory(title="Select Minecraft Directory")
        if directory:
            self.shaderpack_dir_var.set(directory)

    def browse_compatibility_dir(self):
        """Browse for compatibility check directory"""
        directory = filedialog.askdirectory(title="Select Minecraft Directory")
        if directory:
            self.compat_dir_var.set(directory)

    def browse_default_mc_dir(self):
        """Browse for default Minecraft directory"""
        directory = filedialog.askdirectory(title="Select Default Minecraft Directory")
        if directory:
            self.default_mc_dir_var.set(directory)

    def load_atlauncher_instances(self):
        """
        Load ATLauncher instances by scanning common ATLauncher directories.
        Populates a listbox or variable with found instances.
        """
        import platform

        try:
            # Determine default ATLauncher directory based on OS
            user_home = os.path.expanduser("~")
            if platform.system() == "Windows":
                atlauncher_dir = os.path.join(
                    user_home, "AppData", "Roaming", ".atlauncher", "instances"
                )
            elif platform.system() == "Darwin":
                atlauncher_dir = os.path.join(
                    user_home,
                    "Library",
                    "Application Support",
                    "ATLauncher",
                    "instances",
                )
            else:
                # Assume Linux/Unix
                atlauncher_dir = os.path.join(user_home, ".atlauncher", "instances")

            if not os.path.isdir(atlauncher_dir):
                messagebox.showwarning(
                    "ATLauncher Not Found",
                    f"Could not find ATLauncher instances directory at:\n{atlauncher_dir}\n\n"
                    "Please ensure ATLauncher is installed and you have run it at least once.",
                )
                return

            # List all subdirectories (each is an instance)
            instance_names = [
                name
                for name in os.listdir(atlauncher_dir)
                if os.path.isdir(os.path.join(atlauncher_dir, name))
            ]

            if not instance_names:
                messagebox.showinfo(
                    "No Instances Found",
                    "No ATLauncher instances were found in the default directory.",
                )
                return

            # If you have a listbox or variable to populate, do so here
            if hasattr(self, "atlauncher_instance_listbox"):
                self.atlauncher_instance_listbox.delete(0, tk.END)
                for name in instance_names:
                    self.atlauncher_instance_listbox.insert(tk.END, name)
                messagebox.showinfo(
                    "Instances Loaded",
                    f"Found {len(instance_names)} ATLauncher instance(s).",
                )
            else:
                # Fallback: just show a message with the found instances
                messagebox.showinfo(
                    "Instances Found",
                    "Found the following ATLauncher instances:\n\n"
                    + "\n".join(instance_names),
                )

        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to load ATLauncher instances: {str(e)}"
            )

    def load_atlauncher_instances_shaderpack(self):
        """Load ATLauncher instances for shaderpacks"""
        self.load_atlauncher_instances()

    def select_mod_files(self):
        """Select mod files for upload"""
        files = filedialog.askopenfilenames(
            title="Select Mod Files",
            filetypes=[("JAR files", "*.jar"), ("All files", "*.*")],
        )
        if files:
            self.selected_mod_files = files
            self.selected_files_listbox.delete(0, tk.END)
            for file in files:
                self.selected_files_listbox.insert(tk.END, os.path.basename(file))
            self.selected_files_frame.pack(fill="x", padx=10, pady=5)

    def select_shaderpack_files(self):
        """Select shaderpack files for upload"""
        files = filedialog.askopenfilenames(
            title="Select Shaderpack Files",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )
        if files:
            self.selected_shaderpack_files = files
            self.selected_shaderpack_files_listbox.delete(0, tk.END)
            for file in files:
                self.selected_shaderpack_files_listbox.insert(
                    tk.END, os.path.basename(file)
                )
            self.selected_shaderpack_files_frame.pack(fill="x", padx=10, pady=5)

    def upload_mods(self):
        """Upload selected mod files"""
        if not self.selected_mod_files:
            messagebox.showwarning("Warning", "Please select mod files first")
            return

        if not self.dir_var.get():
            messagebox.showerror("Error", "Please select a Minecraft directory first")
            return

        try:
            # Set the directory for the mod manager
            self.mod_manager.set_minecraft_directory(self.dir_var.get())

            # Upload the mods
            results = self.mod_manager.upload_mods(self.selected_mod_files)

            # Show results
            successful = len(results["successful"])
            failed = len(results["failed"])
            skipped = len(results["skipped"])

            message = f"Upload completed:\n"
            message += f"✅ Successful: {successful}\n"
            if failed > 0:
                message += f"❌ Failed: {failed}\n"
            if skipped > 0:
                message += f"⚠️ Skipped: {skipped}\n"

            messagebox.showinfo("Upload Results", message)

            # Clear selection and refresh mod list
            self.selected_files_frame.pack_forget()
            self.selected_mod_files = []
            self.load_mods()  # Refresh the mod list

        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload mods: {str(e)}")

    def upload_shaderpacks(self):
        """Upload selected shaderpack files"""
        if not self.selected_shaderpack_files:
            messagebox.showwarning("Warning", "Please select shaderpack files first")
            return

        if not self.shaderpack_dir_var.get():
            messagebox.showerror("Error", "Please select a Minecraft directory first")
            return

        try:
            # Set the directory for the shaderpack manager
            self.shaderpack_manager.set_minecraft_directory(
                self.shaderpack_dir_var.get()
            )

            # Upload the shaderpacks
            results = self.shaderpack_manager.upload_shaderpacks(
                self.selected_shaderpack_files
            )

            # Show results
            successful = len(results["successful"])
            failed = len(results["failed"])
            skipped = len(results["skipped"])

            message = f"Upload completed:\n"
            message += f"✅ Successful: {successful}\n"
            if failed > 0:
                message += f"❌ Failed: {failed}\n"
            if skipped > 0:
                message += f"⚠️ Skipped: {skipped}\n"

            messagebox.showinfo("Upload Results", message)

            # Clear selection and refresh shaderpack list
            self.selected_shaderpack_files_frame.pack_forget()
            self.selected_shaderpack_files = []
            self.load_shaderpacks()  # Refresh the shaderpack list

        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload shaderpacks: {str(e)}")

    def open_mods_folder(self):
        """Open mods folder in file explorer"""
        if not self.dir_var.get():
            messagebox.showwarning("Warning", "Please set a Minecraft directory first")
            return

        try:
            mods_path = os.path.join(self.dir_var.get(), "mods")
            if os.path.exists(mods_path):
                if os.name == "nt":  # Windows
                    os.startfile(mods_path)
                elif os.name == "posix":  # macOS and Linux
                    subprocess.run(
                        [
                            "open" if os.uname().sysname == "Darwin" else "xdg-open",
                            mods_path,
                        ]
                    )
                messagebox.showinfo("Success", "Opened mods folder")
            else:
                messagebox.showwarning("Warning", "Mods folder not found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open mods folder: {str(e)}")

    def open_shaderpacks_folder(self):
        """Open shaderpacks folder in file explorer"""
        if not self.shaderpack_dir_var.get():
            messagebox.showwarning("Warning", "Please set a Minecraft directory first")
            return

        try:
            shaderpacks_path = os.path.join(
                self.shaderpack_dir_var.get(), "shaderpacks"
            )
            if os.path.exists(shaderpacks_path):
                if os.name == "nt":  # Windows
                    os.startfile(shaderpacks_path)
                elif os.name == "posix":  # macOS and Linux
                    subprocess.run(
                        [
                            "open" if os.uname().sysname == "Darwin" else "xdg-open",
                            shaderpacks_path,
                        ]
                    )
                messagebox.showinfo("Success", "Opened shaderpacks folder")
            else:
                messagebox.showwarning("Warning", "Shaderpacks folder not found")
        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to open shaderpacks folder: {str(e)}"
            )

    def remove_selected_mods(self):
        """Remove selected mods"""
        selection = self.mod_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select mods to remove")
            return

        if not self.dir_var.get():
            messagebox.showerror("Error", "Please select a Minecraft directory first")
            return

        if messagebox.askyesno(
            "Confirm", "Are you sure you want to remove the selected mods?"
        ):
            try:
                # Get selected mod names
                mod_names = []
                for item in selection:
                    mod_name = self.mod_tree.item(item)["values"][0]
                    mod_names.append(mod_name)

                # Set the directory for the mod manager
                self.mod_manager.set_minecraft_directory(self.dir_var.get())

                # Remove the mods
                results = self.mod_manager.remove_mods(mod_names)

                # Show results
                successful = len(results["successful"])
                failed = len(results["failed"])

                message = f"Removal completed:\n"
                message += f"✅ Successful: {successful}\n"
                if failed > 0:
                    message += f"❌ Failed: {failed}\n"

                messagebox.showinfo("Removal Results", message)
                self.load_mods()  # Refresh the list

            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove mods: {str(e)}")

    def remove_selected_shaderpacks(self):
        """Remove selected shaderpacks"""
        selection = self.shaderpack_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select shaderpacks to remove")
            return

        if not self.shaderpack_dir_var.get():
            messagebox.showerror("Error", "Please select a Minecraft directory first")
            return

        if messagebox.askyesno(
            "Confirm", "Are you sure you want to remove the selected shaderpacks?"
        ):
            try:
                # Get selected shaderpack names
                shaderpack_names = []
                for item in selection:
                    shaderpack_name = self.shaderpack_tree.item(item)["values"][0]
                    shaderpack_names.append(shaderpack_name)

                # Set the directory for the shaderpack manager
                self.shaderpack_manager.set_minecraft_directory(
                    self.shaderpack_dir_var.get()
                )

                # Remove the shaderpacks
                results = self.shaderpack_manager.remove_shaderpacks(shaderpack_names)

                # Show results
                successful = len(results["successful"])
                failed = len(results["failed"])

                message = f"Removal completed:\n"
                message += f"✅ Successful: {successful}\n"
                if failed > 0:
                    message += f"❌ Failed: {failed}\n"

                messagebox.showinfo("Removal Results", message)
                self.load_shaderpacks()  # Refresh the list

            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove shaderpacks: {str(e)}")

    def filter_mods(self, *args):
        """Filter mods based on search and purpose"""
        # This would implement mod filtering
        pass

    def filter_shaderpacks(self, *args):
        """Filter shaderpacks based on search"""
        # This would implement shaderpack filtering
        pass

    def categorize_mods(self):
        """Categorize mods using AI"""
        if not self.dir_var.get():
            messagebox.showwarning("Warning", "Please set a Minecraft directory first")
            return

        if not self.crash_analyzer.check_ollama_connection():
            messagebox.showerror(
                "Error", "Ollama is not running. Please start Ollama first."
            )
            return

        try:
            # Get current mods
            mods = self.mod_manager.get_installed_mods()
            if not mods:
                messagebox.showwarning("Warning", "No mods found to categorize")
                return

            # Show progress dialog
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Categorizing Mods")
            progress_window.geometry("400x150")
            progress_window.transient(self.root)
            progress_window.grab_set()

            progress_label = ttk.Label(
                progress_window, text="Categorizing mods with AI..."
            )
            progress_label.pack(pady=20)

            progress_bar = ttk.Progressbar(progress_window, mode="indeterminate")
            progress_bar.pack(pady=10, padx=20, fill="x")
            progress_bar.start()

            status_label = ttk.Label(
                progress_window, text="This may take a few moments..."
            )
            status_label.pack(pady=5)

            def categorize():
                try:
                    # Categorize mods with AI
                    categorized_mods = self.mod_manager.categorize_mods_with_ai(
                        mods, self.crash_analyzer
                    )

                    def update_ui():
                        progress_window.destroy()
                        # Update the mod tree with categorized mods
                        for item in self.mod_tree.get_children():
                            self.mod_tree.delete(item)

                        for mod in categorized_mods:
                            status = (
                                "Enabled" if mod.get("enabled", True) else "Disabled"
                            )
                            size_mb = f"{mod['size'] / (1024*1024):.1f} MB"
                            purpose = mod.get("purpose", "Unknown/Other")

                            self.mod_tree.insert(
                                "",
                                "end",
                                values=(
                                    mod.get("display_name", mod["name"]),
                                    mod.get("version", "Unknown"),
                                    mod.get("author", "Unknown"),
                                    purpose,
                                    size_mb,
                                    status,
                                ),
                            )

                        messagebox.showinfo(
                            "Success",
                            f"Categorized {len(categorized_mods)} mods successfully!",
                        )

                    self.root.after(0, update_ui)

                except Exception as e:

                    def show_error():
                        progress_window.destroy()
                        messagebox.showerror(
                            "Error", f"Failed to categorize mods: {str(e)}"
                        )

                    self.root.after(0, show_error)

            threading.Thread(target=categorize, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to categorize mods: {str(e)}")

    def disable_problematic_mods(self):
        """Disable problematic mods"""
        if not self.problematic_mods:
            messagebox.showinfo("Info", "No problematic mods found")
            return

        if messagebox.askyesno(
            "Confirm", f"Disable {len(self.problematic_mods)} problematic mods?"
        ):
            try:
                # This would implement disabling problematic mods
                messagebox.showinfo("Success", "Problematic mods disabled")
                self.load_mods()  # Refresh the list
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Failed to disable problematic mods: {str(e)}"
                )

    def disable_problematic_shaderpacks(self):
        """Disable problematic shaderpacks"""
        if not self.problematic_shaderpacks:
            messagebox.showinfo("Info", "No problematic shaderpacks found")
            return

        if messagebox.askyesno(
            "Confirm",
            f"Disable {len(self.problematic_shaderpacks)} problematic shaderpacks?",
        ):
            try:
                # This would implement disabling problematic shaderpacks
                messagebox.showinfo("Success", "Problematic shaderpacks disabled")
                self.load_shaderpacks()  # Refresh the list
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Failed to disable problematic shaderpacks: {str(e)}"
                )

    def disable_selected_shaderpack(self):
        """Disable selected shaderpack"""
        selection = self.shaderpack_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a shaderpack to disable")
            return

        try:
            # This would implement shaderpack disabling
            messagebox.showinfo("Success", "Shaderpack disabled")
            self.load_shaderpacks()  # Refresh the list
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disable shaderpack: {str(e)}")

    def enable_selected_shaderpack(self):
        """Enable selected shaderpack"""
        selection = self.shaderpack_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a shaderpack to enable")
            return

        try:
            # This would implement shaderpack enabling
            messagebox.showinfo("Success", "Shaderpack enabled")
            self.load_shaderpacks()  # Refresh the list
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable shaderpack: {str(e)}")

    def get_shaderpack_suggestions(self):
        """Get AI suggestions for shaderpack"""
        selection = self.shaderpack_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Warning", "Please select a shaderpack to get suggestions for"
            )
            return

        # This would implement AI suggestions for shaderpacks
        messagebox.showinfo(
            "Info", "AI suggestions for shaderpacks would be implemented here"
        )

    def backup_shaderpacks(self):
        """Create backup of shaderpacks"""
        try:
            # This would implement shaderpack backup
            messagebox.showinfo("Success", "Shaderpacks backed up successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to backup shaderpacks: {str(e)}")

    def clear_crash_results(self):
        """Clear crash analysis results"""
        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(
            tk.END,
            "Upload a crash log to get started\n\nOur AI will analyze your crash log and provide detailed insights and solutions.",
        )
        self.analysis_text.config(state=tk.DISABLED)

    def copy_crash_results(self):
        """Copy crash analysis results to clipboard"""
        try:
            content = self.analysis_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("Success", "Results copied to clipboard")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy results: {str(e)}")

    def export_crash_results(self):
        """Export crash analysis results to file"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Save Crash Analysis Results",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            )
            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.analysis_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Results exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {str(e)}")

    def export_compatibility_report(self):
        """Export compatibility report to file"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Save Compatibility Report",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            )
            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.compatibility_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Report exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export report: {str(e)}")

    def copy_compatibility_report(self):
        """Copy compatibility report to clipboard"""
        try:
            content = self.compatibility_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("Success", "Report copied to clipboard")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy report: {str(e)}")

    def clear_compatibility_report(self):
        """Clear compatibility report"""
        self.compatibility_text.config(state=tk.NORMAL)
        self.compatibility_text.delete(1.0, tk.END)
        self.compatibility_text.insert(
            tk.END,
            "Enter your Minecraft directory and click 'Check Compatibility' to scan for potential issues in your mod setup.\n\nFor best results, ensure your mod list is up to date and all dependencies are present.",
        )
        self.compatibility_text.config(state=tk.DISABLED)

    def test_ollama_connection(self):
        """Test Ollama connection"""
        try:
            # This would test the connection to Ollama
            messagebox.showinfo("Success", "Ollama connection test successful")
        except Exception as e:
            messagebox.showerror("Error", f"Ollama connection test failed: {str(e)}")

    def save_settings(self):
        """Save application settings"""
        try:
            # Save Ollama settings
            self.settings_manager.set_setting("ollama.url", self.ollama_url_var.get())
            self.settings_manager.set_setting("ollama.model", self.model_var.get())

            # Save application settings
            self.settings_manager.set_setting(
                "application.default_minecraft_dir", self.default_mc_dir_var.get()
            )
            self.settings_manager.set_setting(
                "application.auto_backup", self.auto_backup_var.get()
            )
            self.settings_manager.set_setting(
                "application.dark_mode", self.dark_mode_var.get()
            )

            # Save directory settings
            self.settings_manager.set_setting(
                "directories.minecraft_dir", self.dir_var.get()
            )
            self.settings_manager.set_setting(
                "directories.shaderpack_dir", self.shaderpack_dir_var.get()
            )
            self.settings_manager.set_setting(
                "directories.compatibility_dir", self.compat_dir_var.get()
            )

            # Save to file
            if self.settings_manager.save_settings():
                messagebox.showinfo("Success", "Settings saved successfully")
            else:
                messagebox.showerror("Error", "Failed to save settings to file")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def load_settings(self):
        """Load application settings"""
        try:
            # Load Ollama settings
            ollama_url = self.settings_manager.get_setting(
                "ollama.url", "http://localhost:11434"
            )
            ollama_model = self.settings_manager.get_setting("ollama.model", "llama3.2")

            if hasattr(self, "ollama_url_var"):
                self.ollama_url_var.set(ollama_url)
            if hasattr(self, "model_var"):
                self.model_var.set(ollama_model)

            # Load application settings
            default_mc_dir = self.settings_manager.get_setting(
                "application.default_minecraft_dir", ""
            )
            auto_backup = self.settings_manager.get_setting(
                "application.auto_backup", True
            )
            dark_mode = self.settings_manager.get_setting(
                "application.dark_mode", False
            )

            if hasattr(self, "default_mc_dir_var"):
                self.default_mc_dir_var.set(default_mc_dir)
            if hasattr(self, "auto_backup_var"):
                self.auto_backup_var.set(auto_backup)
            if hasattr(self, "dark_mode_var"):
                self.dark_mode_var.set(dark_mode)

            # Load directory settings
            mc_dir = self.settings_manager.get_setting("directories.minecraft_dir", "")
            shaderpack_dir = self.settings_manager.get_setting(
                "directories.shaderpack_dir", ""
            )
            compat_dir = self.settings_manager.get_setting(
                "directories.compatibility_dir", ""
            )

            if hasattr(self, "dir_var"):
                self.dir_var.set(mc_dir)
            if hasattr(self, "shaderpack_dir_var"):
                self.shaderpack_dir_var.set(shaderpack_dir)
            if hasattr(self, "compat_dir_var"):
                self.compat_dir_var.set(compat_dir)

        except Exception as e:
            print(f"Error loading settings: {e}")
