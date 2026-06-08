"""
Help Dialog Component for the Clinic Data Visualizer application.

This module provides a comprehensive help system that explains:
- What each graph type does
- How to understand the terminology
- How to interpret the visualizations
- Best practices for data analysis
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any
import webbrowser

from app.utils.logger import get_logger
from app.core.dependency_injection import injectable


@injectable
class HelpDialog:
    """
    Comprehensive help dialog for the clinic data visualizer.
    
    Provides detailed explanations of all visualization types,
    terminology, and interpretation guidance.
    """
    
    def __init__(self, parent: tk.Tk):
        """
        Initialize the help dialog.
        
        Args:
            parent: Parent window
        """
        self.parent = parent
        self.logger = get_logger(__name__)
        
        # Help content organized by categories
        self.help_content = self._create_help_content()
        
        # Dialog window
        self.dialog = None
        self.notebook = None
        self.text_widgets = {}
        
    def _create_help_content(self) -> Dict[str, Dict[str, str]]:
        """Create comprehensive help content."""
        return {
            "📊 Dashboard Visualizations": {
                "Clinic Summary Dashboard": """
🏥 **What it shows:**
A comprehensive overview of your clinic's daily operations and key metrics.

📈 **Key Components:**
• Patient Volume: Total number of patients seen
• Service Distribution: Breakdown of different services provided
• Peak Hours: When the clinic is busiest
• Average Wait Times: How long patients typically wait
• Service Efficiency: How quickly services are completed

💡 **How to interpret:**
- Higher patient volume during certain hours indicates peak periods
- Uneven service distribution may suggest resource allocation issues
- Long wait times could indicate bottlenecks or staffing needs
- High efficiency scores suggest good operational flow

🔍 **What to look for:**
- Patterns in patient arrival times
- Services that are most/least popular
- Times when wait times spike
- Overall clinic performance trends
""",
                
                "KPI Dashboard": """
📊 **What it shows:**
Key Performance Indicators (KPIs) that measure clinic effectiveness and efficiency.

📈 **Key Metrics:**
• Patient Throughput: How many patients are processed per hour
• Service Completion Rate: Percentage of services completed successfully
• Average Service Duration: How long each service takes
• Resource Utilization: How efficiently staff and equipment are used
• Patient Satisfaction Indicators: Wait times, service quality

💡 **How to interpret:**
- Higher throughput = more patients served efficiently
- High completion rates = good service quality
- Optimal service duration = balanced speed and quality
- High utilization = efficient resource use
- Low wait times = good patient experience

🔍 **What to look for:**
- KPIs that are below targets
- Trends over time (improving or declining)
- Correlations between different metrics
- Areas for improvement opportunities
""",
                
                "Enhanced Service Types": """
🔧 **What it shows:**
Detailed analysis of different service types and their performance characteristics.

📈 **Key Components:**
• Service Distribution: How different services are used
• Service Performance: Efficiency and quality metrics per service
• Service Trends: How service usage changes over time
• Service Comparisons: Relative performance between services

💡 **How to interpret:**
- Popular services may need more resources
- High-performing services can serve as models
- Declining services may need attention
- Service mix affects overall clinic efficiency

🔍 **What to look for:**
- Services with high demand but low efficiency
- Underutilized services that could be promoted
- Services that consistently perform well
- Opportunities for service optimization
"""
            },
            
            "🛤️ Flow Analysis": {
                "Patient Journey Analysis": """
🛤️ **What it shows:**
The complete path patients take through your clinic, from arrival to departure.

📈 **Key Components:**
• Journey Stages: Registration → Consultation → Treatment → Payment
• Time at Each Stage: How long patients spend at each step
• Journey Variations: Different paths patients can take
• Bottlenecks: Where patients get delayed
• Journey Efficiency: How smoothly the process flows

💡 **How to interpret:**
- Longer times at stages indicate potential bottlenecks
- Multiple journey variations suggest flexible service delivery
- Smooth flows show good operational design
- Gaps in journeys may indicate missing data or process issues

🔍 **What to look for:**
- Stages where patients spend the most time
- Unusual journey patterns that might indicate problems
- Opportunities to streamline the patient experience
- Areas where additional resources might help
""",
                
                "Service Transitions": """
🔄 **What it shows:**
How patients move between different services and the patterns in these transitions.

📈 **Key Components:**
• Transition Matrix: Which services follow which others
• Transition Frequency: How often each transition occurs
• Transition Patterns: Common sequences of services
• Transition Efficiency: How smoothly transitions happen

💡 **How to interpret:**
- High-frequency transitions are normal clinic flow
- Low-frequency transitions may be unusual cases
- Smooth transitions indicate good coordination
- Delays in transitions suggest operational issues

🔍 **What to look for:**
- Transitions that happen frequently (normal flow)
- Rare transitions that might need attention
- Transitions with long delays
- Opportunities to optimize service sequences
""",
                
                "Patient Flow Analysis": """
📊 **What it shows:**
Comprehensive analysis of patient movement patterns and process efficiency.

📈 **Key Components:**
• Process Sequences: Typical patient service sequences
• Process Variations: Different ways patients move through services
• Process Efficiency: How well the overall process works
• Bottlenecks: Where the process slows down
• Optimization Recommendations: How to improve the process

💡 **How to interpret:**
- Typical sequences show normal clinic operations
- Variations may indicate patient needs or service flexibility
- Low efficiency scores suggest improvement opportunities
- Bottlenecks identify where resources are needed

🔍 **What to look for:**
- Common process patterns that work well
- Unusual patterns that might indicate problems
- Areas where the process could be streamlined
- Resource allocation opportunities
"""
            },
            
            "📈 Time & Distribution Analysis": {
                "Time Series Analysis": """
⏰ **What it shows:**
How clinic activity changes over time - hourly, daily, and seasonal patterns.

📈 **Key Components:**
• Hourly Patterns: Activity levels throughout the day
• Daily Patterns: How activity varies by day of week
• Seasonal Trends: Long-term patterns and changes
• Peak Periods: When the clinic is busiest
• Quiet Periods: When activity is low

💡 **How to interpret:**
- Peak hours show when demand is highest
- Quiet periods may indicate scheduling opportunities
- Consistent patterns suggest predictable demand
- Unusual spikes may indicate special events or issues

🔍 **What to look for:**
- Times when you need more staff
- Opportunities to schedule non-urgent services
- Patterns that could inform scheduling decisions
- Unusual activity that might need investigation
""",
                
                "Distribution Analysis": """
📊 **What it shows:**
How different factors (services, patient types, etc.) are distributed across your clinic.

📈 **Key Components:**
• Service Distribution: How different services are used
• Patient Distribution: Types of patients and their characteristics
• Geographic Distribution: Where patients come from
• Temporal Distribution: When different types of activity occur

💡 **How to interpret:**
- Even distributions suggest balanced service provision
- Skewed distributions may indicate specialization or bias
- Geographic patterns can inform outreach efforts
- Temporal patterns help with resource planning

🔍 **What to look for:**
- Services that are over or under-utilized
- Patient groups that might need special attention
- Geographic areas that could benefit from outreach
- Time periods that need different resource allocation
"""
            },
            
            "🔧 Specialized Analysis": {
                "RTMS Analysis": """
🧠 **What it shows:**
Specialized analysis for RTMS (Repetitive Transcranial Magnetic Stimulation) treatments.

📈 **Key Components:**
• Treatment Volume: Number of RTMS sessions
• Treatment Patterns: How RTMS treatments are scheduled
• Room Utilization: How RTMS rooms are used
• Patient Response: Treatment effectiveness indicators
• Resource Requirements: Staff and equipment needs

💡 **How to interpret:**
- High treatment volume may indicate growing demand
- Treatment patterns show optimal scheduling approaches
- Room utilization indicates equipment efficiency
- Patient response data shows treatment effectiveness

🔍 **What to look for:**
- Peak times for RTMS treatments
- Room utilization efficiency
- Patient response patterns
- Resource allocation needs
""",
                
                "Call Analysis": """
📞 **What it shows:**
Analysis of patient calling patterns and communication effectiveness.

📈 **Key Components:**
• Call Volume: Number of calls received
• Call Types: Different types of calls (appointments, inquiries, etc.)
• Call Timing: When calls are most frequent
• Call Outcomes: Results of calls (scheduled, rescheduled, etc.)
• Communication Efficiency: How well calls are handled

💡 **How to interpret:**
- High call volume may indicate high patient engagement
- Call type distribution shows patient needs
- Call timing helps with staffing decisions
- Call outcomes indicate communication effectiveness

🔍 **What to look for:**
- Peak calling times for staffing
- Types of calls that need special attention
- Communication bottlenecks
- Opportunities to improve call handling
"""
            },
            
            "📋 Data Quality & Terminology": {
                "Data Quality Assessment": """
🔍 **What it shows:**
Assessment of the quality and reliability of your clinic data.

📈 **Key Components:**
• Data Completeness: How much data is missing
• Data Accuracy: How correct the data is
• Data Consistency: How uniform the data is
• Data Timeliness: How current the data is
• Data Validity: How well data meets expected formats

💡 **How to interpret:**
- High completeness means most data is available
- High accuracy means data is reliable
- High consistency means data is uniform
- High timeliness means data is current
- High validity means data meets standards

🔍 **What to look for:**
- Missing data that needs to be collected
- Inconsistent data that needs standardization
- Outdated data that needs updating
- Invalid data that needs correction
""",
                
                "Key Terminology": """
📚 **Important Terms:**

**Patient Journey:** The complete path a patient takes through your clinic, from arrival to departure.

**Service Type:** The specific type of service provided (e.g., consultation, treatment, payment).

**Action:** A specific activity or event in the patient's journey (e.g., "Call", "Registration", "End").

**Timestamp:** The exact time when an action occurred.

**Duration:** How long a specific action or service took to complete.

**Wait Time:** The time a patient waited before receiving a service.

**Transition:** The movement from one service or action to another.

**Bottleneck:** A point in the process where patients get delayed or backed up.

**Throughput:** The number of patients processed in a given time period.

**Utilization:** How efficiently resources (staff, rooms, equipment) are being used.

**KPI (Key Performance Indicator):** A measurable value that shows how effectively the clinic is achieving key objectives.

**Process Efficiency:** How well the overall patient journey flows without delays or problems.

**Service Distribution:** How different services are used relative to each other.

**Peak Hours:** Times when the clinic experiences the highest patient volume.

**Resource Allocation:** How staff, rooms, and equipment are assigned to different services.
"""
            },
            
            "💡 Best Practices": {
                "Interpreting Visualizations": """
🎯 **Best Practices for Understanding Your Data:**

**1. Start with the Big Picture:**
- Begin with dashboard overviews to understand overall performance
- Look for trends and patterns rather than individual data points
- Compare current performance to historical data when available

**2. Focus on Key Metrics:**
- Patient volume and throughput for operational efficiency
- Wait times and service duration for quality of care
- Service distribution for resource allocation
- Journey patterns for process optimization

**3. Look for Patterns:**
- Time-based patterns (hourly, daily, seasonal)
- Service-based patterns (which services are used together)
- Patient-based patterns (different patient types and needs)
- Process-based patterns (how patients move through services)

**4. Identify Opportunities:**
- Bottlenecks that need resource allocation
- Underutilized services that could be promoted
- Peak times that need additional staffing
- Process inefficiencies that could be streamlined

**5. Consider Context:**
- External factors that might affect patterns (weather, events, etc.)
- Internal changes that might explain variations (new services, staff changes)
- Patient demographics and needs
- Clinic policies and procedures

**6. Take Action:**
- Use insights to inform scheduling decisions
- Allocate resources based on demand patterns
- Optimize processes based on journey analysis
- Monitor changes to see if improvements work
""",
                
                "Common Pitfalls": """
⚠️ **Things to Avoid:**

**1. Over-interpreting Small Changes:**
- Small variations in data may be normal fluctuations
- Look for consistent patterns rather than one-time events
- Consider the context before making changes

**2. Ignoring Data Quality:**
- Poor quality data leads to poor decisions
- Always check data completeness and accuracy
- Address data quality issues before analysis

**3. Focusing Only on Problems:**
- Also look for what's working well
- Learn from successful patterns and processes
- Celebrate and reinforce good performance

**4. Making Changes Without Testing:**
- Test improvements on a small scale first
- Monitor the impact of changes
- Be prepared to adjust based on results

**5. Ignoring Patient Experience:**
- Efficiency is important, but so is patient satisfaction
- Consider how changes affect patient experience
- Balance operational needs with patient needs

**6. Not Sharing Insights:**
- Share findings with relevant staff
- Use data to inform team decisions
- Create a data-driven culture
"""
            }
        }
    
    def show(self):
        """Show the help dialog."""
        try:
            # Create dialog window
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("📚 Clinic Data Visualizer - Help & Guide")
            self.dialog.geometry("900x700")
            self.dialog.resizable(True, True)
            
            # Center the dialog
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # Create main frame
            main_frame = ttk.Frame(self.dialog, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Configure grid weights
            self.dialog.columnconfigure(0, weight=1)
            self.dialog.rowconfigure(0, weight=1)
            main_frame.columnconfigure(1, weight=1)
            main_frame.rowconfigure(1, weight=1)
            
            # Create header
            header_frame = ttk.Frame(main_frame)
            header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            
            title_label = ttk.Label(header_frame, 
                                   text="📚 Clinic Data Visualizer - Help & Guide", 
                                   font=("Arial", 16, "bold"))
            title_label.pack()
            
            subtitle_label = ttk.Label(header_frame, 
                                      text="Learn how to understand and interpret your clinic data visualizations", 
                                      font=("Arial", 10))
            subtitle_label.pack()
            
            # Create notebook for tabbed interface
            self.notebook = ttk.Notebook(main_frame)
            self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Create tabs for each category
            for category_name, category_content in self.help_content.items():
                self._create_category_tab(category_name, category_content)
            
            # Create footer with close button
            footer_frame = ttk.Frame(main_frame)
            footer_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
            
            close_button = ttk.Button(footer_frame, text="Close", command=self._close_dialog)
            close_button.pack(side=tk.RIGHT)
            
            # Add keyboard shortcut
            self.dialog.bind("<Escape>", lambda e: self._close_dialog())
            
            # Focus on the dialog
            self.dialog.focus_set()
            
            self.logger.info("Help dialog opened successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating help dialog: {e}")
            messagebox.showerror("Error", f"Failed to open help dialog: {str(e)}")
    
    def _create_category_tab(self, category_name: str, category_content: Dict[str, str]):
        """Create a tab for a help category."""
        # Create frame for the tab
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=category_name)
        
        # Create scrollable text widget
        text_frame = ttk.Frame(tab_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create text widget with scrollbar
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10), 
                             bg="white", fg="black", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert content
        self._insert_formatted_content(text_widget, category_content)
        
        # Store reference
        self.text_widgets[category_name] = text_widget
        
        # Make text widget read-only
        text_widget.config(state=tk.DISABLED)
    
    def _insert_formatted_content(self, text_widget: tk.Text, content: Dict[str, str]):
        """Insert formatted content into text widget."""
        for topic, explanation in content.items():
            # Insert topic title
            text_widget.insert(tk.END, f"{topic}\n", "title")
            text_widget.insert(tk.END, "=" * len(topic) + "\n\n", "title")
            
            # Insert explanation
            text_widget.insert(tk.END, explanation + "\n\n", "normal")
        
        # Configure tags for formatting
        text_widget.tag_configure("title", font=("Arial", 12, "bold"), foreground="navy")
        text_widget.tag_configure("normal", font=("Arial", 10))
    
    def _close_dialog(self):
        """Close the help dialog."""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
            self.logger.info("Help dialog closed")
    
    def is_open(self) -> bool:
        """Check if the help dialog is currently open."""
        return self.dialog is not None and self.dialog.winfo_exists() 