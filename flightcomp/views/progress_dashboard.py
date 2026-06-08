"""
Progress Dashboard for Pilot Training
Displays training progress, performance metrics, and skill progression
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Dict, Any
from datetime import datetime
from utils.progress_tracker import ProgressTracker
from utils.report_generator import ReportGenerator
from utils.logging_config import get_logger
from models.training_record import PilotProgress, TrainingSession

logger = get_logger(__name__)


class ProgressDashboard:
    """Progress dashboard for displaying training metrics"""
    
    def __init__(self, parent, progress_tracker: ProgressTracker, pilot_id: str):
        """
        Initialize progress dashboard
        
        Args:
            parent: Parent widget
            progress_tracker: ProgressTracker instance
            pilot_id: Pilot ID to display progress for
        """
        self.parent = parent
        self.progress_tracker = progress_tracker
        self.pilot_id = pilot_id
        self.report_generator = ReportGenerator(progress_tracker)
        
        self.setup_ui()
        self.refresh_data()
    
    def setup_ui(self):
        """Set up the dashboard UI"""
        # Main container
        main_frame = ttk.Frame(self.parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame,
            text="Training Progress Dashboard",
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        refresh_btn = ttk.Button(
            header_frame,
            text="Refresh",
            command=self.refresh_data
        )
        refresh_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Overview tab
        self.overview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_tab, text="Overview")
        self.setup_overview_tab()
        
        # Skills tab
        self.skills_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.skills_tab, text="Skills")
        self.setup_skills_tab()
        
        # Sessions tab
        self.sessions_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.sessions_tab, text="Sessions")
        self.setup_sessions_tab()
        
        # Reports tab
        self.reports_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reports_tab, text="Reports")
        self.setup_reports_tab()
    
    def setup_overview_tab(self):
        """Set up overview tab"""
        overview_frame = ttk.Frame(self.overview_tab, padding=10)
        overview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Summary frame
        summary_frame = ttk.LabelFrame(overview_frame, text="Summary", padding=10)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.summary_text = scrolledtext.ScrolledText(
            summary_frame,
            height=8,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        
        # Performance metrics frame
        metrics_frame = ttk.LabelFrame(overview_frame, text="Performance Metrics", padding=10)
        metrics_frame.pack(fill=tk.BOTH, expand=True)
        
        self.metrics_text = scrolledtext.ScrolledText(
            metrics_frame,
            height=10,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.metrics_text.pack(fill=tk.BOTH, expand=True)
    
    def setup_skills_tab(self):
        """Set up skills tab"""
        skills_frame = ttk.Frame(self.skills_tab, padding=10)
        skills_frame.pack(fill=tk.BOTH, expand=True)
        
        self.skills_text = scrolledtext.ScrolledText(
            skills_frame,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.skills_text.pack(fill=tk.BOTH, expand=True)
    
    def setup_sessions_tab(self):
        """Set up sessions tab"""
        sessions_frame = ttk.Frame(self.sessions_tab, padding=10)
        sessions_frame.pack(fill=tk.BOTH, expand=True)
        
        # Session list
        list_frame = ttk.Frame(sessions_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview for sessions
        columns = ("Date", "Scenario", "Score", "Duration", "Communications")
        self.sessions_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.sessions_tree.heading(col, text=col)
            self.sessions_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.sessions_tree.yview)
        self.sessions_tree.configure(yscrollcommand=scrollbar.set)
        
        self.sessions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Session details
        details_frame = ttk.LabelFrame(sessions_frame, text="Session Details", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        self.session_details_text = scrolledtext.ScrolledText(
            details_frame,
            height=8,
            wrap=tk.WORD,
            font=("Arial", 9)
        )
        self.session_details_text.pack(fill=tk.BOTH, expand=True)
        
        # Bind selection event
        self.sessions_tree.bind("<<TreeviewSelect>>", self.on_session_select)
    
    def setup_reports_tab(self):
        """Set up reports tab"""
        reports_frame = ttk.Frame(self.reports_tab, padding=10)
        reports_frame.pack(fill=tk.BOTH, expand=True)
        
        # Report options
        options_frame = ttk.Frame(reports_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(options_frame, text="Report Period:").pack(side=tk.LEFT, padx=(0, 5))
        self.period_var = tk.StringVar(value="30")
        period_combo = ttk.Combobox(
            options_frame,
            textvariable=self.period_var,
            values=["7", "30", "60", "90", "All"],
            state="readonly",
            width=10
        )
        period_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        generate_btn = ttk.Button(
            options_frame,
            text="Generate Report",
            command=self.generate_report
        )
        generate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_btn = ttk.Button(
            options_frame,
            text="Export to File",
            command=self.export_report
        )
        export_btn.pack(side=tk.LEFT)
        
        # Report display
        self.report_text = scrolledtext.ScrolledText(
            reports_frame,
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.report_text.pack(fill=tk.BOTH, expand=True)
    
    def refresh_data(self):
        """Refresh dashboard data"""
        progress = self.progress_tracker.get_pilot_progress(self.pilot_id)
        if not progress:
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.insert(tk.END, "No progress data available for this pilot.")
            return
        
        # Update summary
        self.update_summary(progress)
        
        # Update metrics
        self.update_metrics()
        
        # Update skills
        self.update_skills(progress)
        
        # Update sessions
        self.update_sessions()
    
    def update_summary(self, progress: PilotProgress):
        """Update summary display"""
        self.summary_text.delete(1.0, tk.END)
        
        summary = f"""Pilot ID: {progress.pilot_id}

Training Summary:
- Total Sessions: {progress.total_sessions}
- Total Communications: {progress.total_communications}
- Overall Average Score: {progress.overall_average_score:.1f}/100

Last Training: {datetime.fromtimestamp(progress.last_training_date).strftime('%Y-%m-%d %H:%M') if progress.last_training_date else 'Never'}

Certifications: {', '.join(progress.certifications) if progress.certifications else 'None'}
"""
        self.summary_text.insert(tk.END, summary)
    
    def update_metrics(self):
        """Update performance metrics"""
        metrics = self.progress_tracker.get_performance_metrics(self.pilot_id, days=30)
        
        self.metrics_text.delete(1.0, tk.END)
        
        if not metrics:
            self.metrics_text.insert(tk.END, "No metrics available for the selected period.")
            return
        
        metrics_text = f"""Performance Metrics (Last 30 Days):

Sessions: {metrics.get('sessions_count', 0)}
Average Score: {metrics.get('average_score', 0.0):.1f}/100
Total Communications: {metrics.get('total_communications', 0)}
Improvement Trend: {metrics.get('improvement_trend', 0.0):+.1f} points
Best Score: {metrics.get('best_score', 0.0):.1f}/100
Worst Score: {metrics.get('worst_score', 0.0):.1f}/100
"""
        self.metrics_text.insert(tk.END, metrics_text)
    
    def update_skills(self, progress: PilotProgress):
        """Update skills display"""
        skill_breakdown = self.progress_tracker.get_skill_breakdown(self.pilot_id)
        
        self.skills_text.delete(1.0, tk.END)
        
        if not skill_breakdown:
            self.skills_text.insert(tk.END, "No skill data available.")
            return
        
        skills_text = "Skill Breakdown:\n\n"
        for skill_name, skill_data in skill_breakdown.items():
            skills_text += f"{skill_name}:\n"
            skills_text += f"  Level: {skill_data['level']}\n"
            skills_text += f"  Average Score: {skill_data['average_score']:.1f}/100\n"
            skills_text += f"  Sessions: {skill_data['sessions']}\n"
            if skill_data['trend']:
                recent_scores = skill_data['trend'][-5:]
                skills_text += f"  Recent Scores: {', '.join(f'{s:.1f}' for s in recent_scores)}\n"
            if skill_data['weak_areas']:
                skills_text += f"  Weak Areas: {', '.join(skill_data['weak_areas'])}\n"
            if skill_data['strong_areas']:
                skills_text += f"  Strong Areas: {', '.join(skill_data['strong_areas'])}\n"
            skills_text += "\n"
        
        self.skills_text.insert(tk.END, skills_text)
    
    def update_sessions(self):
        """Update sessions list"""
        # Clear existing items
        for item in self.sessions_tree.get_children():
            self.sessions_tree.delete(item)
        
        sessions = self.progress_tracker.get_pilot_sessions(self.pilot_id, limit=50)
        
        for session in sessions:
            date_str = datetime.fromtimestamp(session.start_time).strftime('%Y-%m-%d %H:%M')
            duration_min = int(session.get_duration() / 60)
            
            self.sessions_tree.insert(
                "",
                tk.END,
                values=(
                    date_str,
                    session.scenario_id or "N/A",
                    f"{session.overall_score:.1f}",
                    f"{duration_min} min",
                    session.get_communication_count()
                ),
                tags=(session.session_id,)
            )
    
    def on_session_select(self, event):
        """Handle session selection"""
        selection = self.sessions_tree.selection()
        if not selection:
            return
        
        item = self.sessions_tree.item(selection[0])
        session_id = item['tags'][0] if item['tags'] else None
        
        if session_id:
            session = self.progress_tracker.get_session(session_id)
            if session:
                self.display_session_details(session)
    
    def display_session_details(self, session: TrainingSession):
        """Display session details"""
        self.session_details_text.delete(1.0, tk.END)
        
        details = f"""Session ID: {session.session_id}
Date: {datetime.fromtimestamp(session.start_time).strftime('%Y-%m-%d %H:%M:%S')}
Duration: {int(session.get_duration() / 60)} minutes
Status: {session.status.value}
Overall Score: {session.overall_score:.1f}/100

Skill Scores:
"""
        for skill, score in session.skill_scores.items():
            details += f"  {skill}: {score:.1f}/100\n"
        
        details += f"\nCommunications: {session.get_communication_count()}\n"
        
        self.session_details_text.insert(tk.END, details)
    
    def generate_report(self):
        """Generate progress report"""
        period = self.period_var.get()
        days = int(period) if period != "All" else 365
        
        report = self.report_generator.generate_pilot_progress_report(self.pilot_id, days)
        
        self.report_text.delete(1.0, tk.END)
        
        if "error" in report:
            self.report_text.insert(tk.END, f"Error: {report['error']}")
        else:
            report_text = self.report_generator.generate_text_summary(report)
            self.report_text.insert(tk.END, report_text)
    
    def export_report(self):
        """Export report to file"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            period = self.period_var.get()
            days = int(period) if period != "All" else 365
            
            if filename.endswith('.json'):
                success = self.report_generator.export_pilot_report_json(self.pilot_id, filename, days)
            else:
                # Export as text
                report = self.report_generator.generate_pilot_progress_report(self.pilot_id, days)
                report_text = self.report_generator.generate_text_summary(report)
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(report_text)
                    success = True
                except Exception as e:
                    logger.warning("Error exporting report: %s", e)
                    success = False
            
            if success:
                from tkinter import messagebox
                messagebox.showinfo("Export", f"Report exported successfully to {filename}")

