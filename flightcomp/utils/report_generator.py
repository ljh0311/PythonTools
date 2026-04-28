"""
Report Generator for Pilot Training
Generates training reports and performance summaries
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from models.training_record import TrainingSession, PilotProgress
from utils.progress_tracker import ProgressTracker
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generates training reports"""
    
    def __init__(self, progress_tracker: ProgressTracker):
        """
        Initialize report generator
        
        Args:
            progress_tracker: ProgressTracker instance
        """
        self.progress_tracker = progress_tracker
    
    def generate_session_report(self, session_id: str) -> Dict[str, Any]:
        """Generate a report for a specific session"""
        session = self.progress_tracker.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        report = {
            "session_id": session.session_id,
            "pilot_id": session.pilot_id,
            "scenario_id": session.scenario_id,
            "airport": session.airport_icao,
            "difficulty": session.difficulty,
            "date": datetime.fromtimestamp(session.start_time).isoformat(),
            "duration_minutes": round(session.get_duration() / 60, 1),
            "status": session.status.value,
            "overall_score": round(session.overall_score, 1),
            "skill_scores": {k: round(v, 1) for k, v in session.skill_scores.items()},
            "communications_count": session.get_communication_count(),
            "communications": [
                {
                    "instruction": comm.instruction,
                    "readback": comm.readback,
                    "score": round(comm.score, 1),
                    "response_time": round(comm.response_time, 2) if comm.response_time else None,
                    "error_count": len(comm.errors)
                }
                for comm in session.communications
            ],
            "summary": {
                "average_score": round(session.get_average_score(), 1),
                "total_errors": sum(len(comm.errors) for comm in session.communications),
                "average_response_time": self._calculate_avg_response_time(session)
            }
        }
        
        return report
    
    def generate_pilot_progress_report(self, pilot_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate a progress report for a pilot"""
        progress = self.progress_tracker.get_pilot_progress(pilot_id)
        if not progress:
            return {"error": "Pilot not found"}
        
        metrics = self.progress_tracker.get_performance_metrics(pilot_id, days)
        skill_breakdown = self.progress_tracker.get_skill_breakdown(pilot_id)
        
        report = {
            "pilot_id": pilot_id,
            "report_period_days": days,
            "generated_date": datetime.now().isoformat(),
            "overview": {
                "total_sessions": progress.total_sessions,
                "total_communications": progress.total_communications,
                "overall_average_score": round(progress.overall_average_score, 1),
                "last_training_date": datetime.fromtimestamp(progress.last_training_date).isoformat() 
                    if progress.last_training_date else None
            },
            "recent_performance": {
                "sessions_count": metrics.get("sessions_count", 0),
                "average_score": round(metrics.get("average_score", 0.0), 1),
                "total_communications": metrics.get("total_communications", 0),
                "improvement_trend": round(metrics.get("improvement_trend", 0.0), 1),
                "best_score": round(metrics.get("best_score", 0.0), 1),
                "worst_score": round(metrics.get("worst_score", 0.0), 1)
            },
            "skill_breakdown": {
                skill_name: {
                    "level": skill_data["level"],
                    "average_score": round(skill_data["average_score"], 1),
                    "sessions": skill_data["sessions"],
                    "trend": [round(s, 1) for s in skill_data["trend"]],
                    "weak_areas": skill_data["weak_areas"],
                    "strong_areas": skill_data["strong_areas"]
                }
                for skill_name, skill_data in skill_breakdown.items()
            },
            "certifications": progress.certifications
        }
        
        return report
    
    def export_session_report_json(self, session_id: str, output_path: str) -> bool:
        """Export session report as JSON"""
        try:
            report = self.generate_session_report(session_id)
            if "error" in report:
                return False
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.warning("Error exporting session report: %s", e)
            return False
    
    def export_pilot_report_json(self, pilot_id: str, output_path: str, days: int = 30) -> bool:
        """Export pilot progress report as JSON"""
        try:
            report = self.generate_pilot_progress_report(pilot_id, days)
            if "error" in report:
                return False
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.warning("Error exporting pilot report: %s", e)
            return False
    
    def generate_text_summary(self, report: Dict[str, Any]) -> str:
        """Generate a text summary from a report"""
        if "error" in report:
            return f"Error: {report['error']}"
        
        if "session_id" in report:
            # Session report
            summary = f"""
Training Session Report
======================
Session ID: {report['session_id']}
Date: {report['date']}
Airport: {report['airport']}
Difficulty: {report['difficulty']}
Duration: {report['duration_minutes']} minutes

Performance Summary:
- Overall Score: {report['overall_score']}/100
- Communications: {report['communications_count']}
- Average Score: {report['summary']['average_score']}/100
- Total Errors: {report['summary']['total_errors']}
- Average Response Time: {report['summary']['average_response_time']:.2f}s

Skill Scores:
"""
            for skill, score in report['skill_scores'].items():
                summary += f"- {skill}: {score}/100\n"
        else:
            # Pilot progress report
            summary = f"""
Pilot Progress Report
=====================
Pilot ID: {report['pilot_id']}
Report Period: Last {report['report_period_days']} days
Generated: {report['generated_date']}

Overview:
- Total Sessions: {report['overview']['total_sessions']}
- Total Communications: {report['overview']['total_communications']}
- Overall Average Score: {report['overview']['overall_average_score']}/100

Recent Performance (Last {report['report_period_days']} days):
- Sessions: {report['recent_performance']['sessions_count']}
- Average Score: {report['recent_performance']['average_score']}/100
- Improvement Trend: {report['recent_performance']['improvement_trend']:+.1f}
- Best Score: {report['recent_performance']['best_score']}/100
- Worst Score: {report['recent_performance']['worst_score']}/100

Skill Breakdown:
"""
            for skill_name, skill_data in report['skill_breakdown'].items():
                summary += f"\n{skill_name}:\n"
                summary += f"  Level: {skill_data['level']}\n"
                summary += f"  Average Score: {skill_data['average_score']}/100\n"
                summary += f"  Sessions: {skill_data['sessions']}\n"
                if skill_data['weak_areas']:
                    summary += f"  Weak Areas: {', '.join(skill_data['weak_areas'])}\n"
                if skill_data['strong_areas']:
                    summary += f"  Strong Areas: {', '.join(skill_data['strong_areas'])}\n"
        
        return summary
    
    def _calculate_avg_response_time(self, session: TrainingSession) -> float:
        """Calculate average response time for a session"""
        response_times = [
            comm.response_time for comm in session.communications
            if comm.response_time is not None
        ]
        if response_times:
            return sum(response_times) / len(response_times)
        return 0.0

    def export_debrief_text(self, debrief_text: str, output_path: str) -> bool:
        """Export debrief text to a file path."""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(debrief_text)
            return True
        except Exception as e:
            logger.warning("Error exporting debrief text: %s", e)
            return False

    def generate_trainee_debrief(
        self,
        role: str,
        session_report: Dict[str, Any],
        progress_report: Optional[Dict[str, Any]] = None,
        extra_metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a practical debrief with comments, insights, comparisons and analysis."""
        if "error" in session_report:
            return f"Debrief unavailable: {session_report['error']}"

        extra_metrics = extra_metrics or {}
        role_title = role.upper()
        score = float(session_report.get("overall_score", 0.0))
        avg_score = float(session_report.get("summary", {}).get("average_score", score))
        communications = int(session_report.get("communications_count", 0))
        duration = float(session_report.get("duration_minutes", 0.0))
        avg_response = float(session_report.get("summary", {}).get("average_response_time", 0.0))
        errors = int(session_report.get("summary", {}).get("total_errors", 0))

        benchmark_score = 80.0
        benchmark_response = 8.0
        score_delta = score - benchmark_score
        response_delta = benchmark_response - avg_response

        trend_text = "Trend unavailable (insufficient history)."
        baseline_text = "Baseline comparison unavailable."
        if progress_report and "error" not in progress_report:
            recent = progress_report.get("recent_performance", {})
            trend = float(recent.get("improvement_trend", 0.0))
            trend_text = (
                f"Recent trend: improving by {trend:.1f} points."
                if trend > 0
                else f"Recent trend: declining by {abs(trend):.1f} points."
                if trend < 0
                else "Recent trend: stable."
            )
            baseline_avg = float(recent.get("average_score", 0.0))
            baseline_text = f"Compared with last-period average ({baseline_avg:.1f}), this session is {score - baseline_avg:+.1f} points."

        comments = []
        if score >= 90:
            comments.append("Strong operational control and phraseology discipline.")
        elif score >= 75:
            comments.append("Solid performance with moderate risk points to refine.")
        else:
            comments.append("Performance below training target; prioritize standardization.")

        if avg_response > 0:
            if avg_response <= 6:
                comments.append("Response timing supports smooth traffic flow.")
            elif avg_response <= 12:
                comments.append("Response timing acceptable but can be tightened under load.")
            else:
                comments.append("Response timing is slow for busy periods; practice concise decisions.")

        if errors == 0:
            comments.append("No recorded communication errors in this session.")
        elif errors <= 3:
            comments.append("Low error count; focus on preventing repeat patterns.")
        else:
            comments.append("Error count is high; target deliberate readback/hearback loops.")

        role_focus = extra_metrics.get("focus_area", "Maintain concise, standard phraseology.")
        role_insight = extra_metrics.get("insight", "")

        analysis = [
            f"{role_title} Debrief",
            "=" * (len(role_title) + 8),
            f"Session score: {score:.1f}/100 (avg comm score: {avg_score:.1f})",
            f"Work sample: {communications} communications over {duration:.1f} minutes",
            f"Error load: {errors} total | Avg response time: {avg_response:.2f}s",
            "",
            "Comments:",
            *[f"- {line}" for line in comments],
            "",
            "Insights:",
            f"- Benchmark score comparison (80 target): {score_delta:+.1f} points",
            f"- Benchmark response comparison (8s target): {response_delta:+.2f}s better-than-target" if avg_response > 0 else "- Response-time benchmark unavailable",
            f"- {trend_text}",
            f"- {baseline_text}",
            "",
            "Focus and Next Actions:",
            f"- Priority focus: {role_focus}",
            "- Next session target: keep score >= 85 with fewer than 3 communication errors.",
        ]
        if role_insight:
            analysis.insert(-2, f"- Operational insight: {role_insight}")

        return "\n".join(analysis)

