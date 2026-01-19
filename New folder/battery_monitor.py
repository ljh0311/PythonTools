import psutil
import time
from datetime import datetime, timedelta
import os
from collections import defaultdict
import gc
import ctypes
import sys
import json
import ollama
import mpl

def check_ollama_available():
    """
    Check if Ollama is running and the required model is available.
    Returns (is_available, error_message)
    """
    model_name = "llama3.1:8b"
    try:
        # Try a simple chat request to check if Ollama is running and model is available
        test_response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": "test"}]
        )
        return True, None
    except Exception as e:
        error_str = str(e).lower()
        if "connection" in error_str or "refused" in error_str or "connect" in error_str:
            return False, "Ollama is not running. Please start Ollama first."
        elif "not found" in error_str or "pull" in error_str or "model" in error_str:
            return False, f"Model '{model_name}' not found.\n\nPlease run this command in a separate terminal:\n  ollama pull llama3.1:8b\n\nThis will download the model (about 4.7GB). It may take several minutes."
        else:
            return False, f"Ollama error: {str(e)}\n\nMake sure Ollama is running and the {model_name} model is installed."


def send_prompt(user_question, battery_data_context):
    """
    Send a question to Ollama with battery data context.
    """
    system_message = """You are a battery analysis assistant. 
You have access to real-time battery status and historical charging data.
Provide helpful, accurate answers about battery health, charging times, and usage patterns.
Use the provided data to give specific estimates and recommendations."""
    
    try:
        response = ollama.chat(
            model="llama3.1:8b",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Battery Data:\n{battery_data_context}\n\nQuestion: {user_question}"}
            ]
        )
        return response["message"]["content"]
    except Exception as e:
        raise Exception(f"Error communicating with Ollama: {str(e)}")


def format_timestamp(iso_string):
    """Convert ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime('%Y-%m-%d %I:%M %p')
    except:
        return iso_string


def format_battery_data_for_ai():
    """
    Gather current battery status and historical data,
    format it as a readable string for AI analysis.
    """
    try:
        # Get current battery status
        current_status = get_battery_info()
        
        # Load historical data
        history = load_charge_cycles()
        
        # Format as readable text
        data_summary = "=== CURRENT BATTERY STATUS ===\n"
        data_summary += f"Percentage: {current_status['percentage']}%\n"
        data_summary += f"Plugged In: {current_status['power_plugged']}\n"
        data_summary += f"Time Left: {current_status['time_left']}\n\n"
        
        data_summary += "=== HISTORICAL DATA SUMMARY ===\n"
        
        # Charge cycles summary
        if history['charge_cycles']:
            avg_charge_rate = sum(c['rate_per_hour'] for c in history['charge_cycles']) / len(history['charge_cycles'])
            data_summary += f"Charge Cycles Recorded: {len(history['charge_cycles'])}\n"
            data_summary += f"Average Charge Rate: {avg_charge_rate:.1f}%/hour\n"
        
        # Discharge cycles summary
        if history['discharge_cycles']:
            avg_discharge_rate = sum(abs(c['rate_per_hour']) for c in history['discharge_cycles']) / len(history['discharge_cycles'])
            data_summary += f"Discharge Cycles Recorded: {len(history['discharge_cycles'])}\n"
            data_summary += f"Average Discharge Rate: {avg_discharge_rate:.1f}%/hour\n"
        
        # Recent charge cycles (last 5)
        if history['charge_cycles']:
            data_summary += "\n=== RECENT CHARGE CYCLES (Last 5) ===\n"
            recent_charges = history['charge_cycles'][-5:]
            for i, cycle in enumerate(reversed(recent_charges), 1):
                data_summary += f"\nCycle {i}:\n"
                data_summary += f"  Started: {format_timestamp(cycle.get('start', 'N/A'))}\n"
                data_summary += f"  Ended: {format_timestamp(cycle.get('end', 'N/A'))}\n"
                data_summary += f"  Duration: {cycle.get('duration', 0):.1f} minutes\n"
                if 'start_percent' in cycle:
                    data_summary += f"  Range: {cycle['start_percent']}% -> {cycle['percent']}%\n"
                    data_summary += f"  Gained: {cycle.get('percent_change', 0)}%\n"
                    data_summary += f"  Rate: {cycle.get('rate_per_hour', 0):.1f}%/hour\n"
        
        # Recent discharge cycles (last 5)
        if history['discharge_cycles']:
            data_summary += "\n=== RECENT DISCHARGE CYCLES (Last 5) ===\n"
            recent_discharges = history['discharge_cycles'][-5:]
            for i, cycle in enumerate(reversed(recent_discharges), 1):
                data_summary += f"\nCycle {i}:\n"
                data_summary += f"  Started: {format_timestamp(cycle.get('start', 'N/A'))}\n"
                data_summary += f"  Ended: {format_timestamp(cycle.get('end', 'N/A'))}\n"
                data_summary += f"  Duration: {cycle.get('duration', 0):.1f} minutes\n"
                if 'start_percent' in cycle:
                    data_summary += f"  Range: {cycle['start_percent']}% -> {cycle['percent']}%\n"
                    data_summary += f"  Lost: {abs(cycle.get('percent_change', 0))}%\n"
                    data_summary += f"  Rate: {abs(cycle.get('rate_per_hour', 0)):.1f}%/hour\n"
        
        # Range statistics
        if 'charge_range_stats' in history:
            data_summary += "\n=== CHARGING BY BATTERY RANGE ===\n"
            for range_key in ['0-49', '50-79', '80-100']:
                range_data = history['charge_range_stats'].get(range_key, {})
                if range_data.get('cycles'):
                    data_summary += f"{range_key}%: "
                    data_summary += f"{range_data['avg_rate']:.1f}%/hour, "
                    data_summary += f"{range_data['avg_time']:.1f} min avg\n"
        
        # Charging threshold averages
        if 'charge_thresholds' in history and any(history['charge_thresholds'][t]['times'] for t in history['charge_thresholds']):
            data_summary += "\n=== AVERAGE TIME TO CHARGE THRESHOLDS ===\n"
            for threshold in ['80', '85', '90', '95', '100']:
                threshold_data = history['charge_thresholds'].get(threshold, {})
                if threshold_data.get('times'):
                    avg = threshold_data['average']
                    count = len(threshold_data['times'])
                    if avg >= 60:
                        hours = int(avg // 60)
                        mins = int(avg % 60)
                        data_summary += f"  To {threshold}%: {hours}h {mins}m (from {count} samples)\n"
                    else:
                        data_summary += f"  To {threshold}%: {avg:.1f} minutes (from {count} samples)\n"
        
        # Usage pattern insights
        if history['charge_cycles'] and history['discharge_cycles']:
            data_summary += "\n=== USAGE PATTERNS ===\n"
            
            # Average session lengths
            avg_charge_duration = sum(c['duration'] for c in history['charge_cycles']) / len(history['charge_cycles'])
            avg_discharge_duration = sum(c['duration'] for c in history['discharge_cycles']) / len(history['discharge_cycles'])
            
            data_summary += f"Average Charging Session: {avg_charge_duration:.1f} minutes\n"
            data_summary += f"Average Usage Session: {avg_discharge_duration:.1f} minutes\n"
            
            # Total cycles
            data_summary += f"Total Charge/Discharge Cycles: {len(history['charge_cycles'])}\n"
        
        return data_summary
    except Exception as e:
        return f"Error gathering battery data: {str(e)}"


def cleanup_memory():
    try:
        # Force garbage collection
        gc.collect()

        # Clear memory cache on Windows
        if os.name == "nt":
            ctypes.windll.psapi.EmptyWorkingSet(ctypes.c_int(-1))

        return True
    except Exception as e:
        print(f"Error during memory cleanup: {str(e)}")
        return False


def get_process_power_usage():
    try:
        # Get number of CPU cores
        cpu_count = psutil.cpu_count()

        # Get all processes with minimal overhead
        processes = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                # Get process info without CPU calculation first
                pinfo = proc.info

                # Only check CPU for processes that might be significant
                # Skip system processes that are unlikely to be high usage
                skip_processes = {
                    "System Idle Process",
                    "System",
                    "Registry",
                    "svchost.exe",
                    "csrss.exe",
                    "winlogon.exe",
                }
                if pinfo["name"] in skip_processes:
                    continue

                # Get CPU usage with minimal interval
                cpu_percent = proc.cpu_percent(interval=0.01)
                # Normalize CPU usage to percentage across all cores
                normalized_cpu = cpu_percent / cpu_count

                # Only get memory if CPU usage is significant
                if normalized_cpu > 0.5:
                    memory_percent = proc.memory_percent()
                    processes.append(
                        {
                            "pid": pinfo["pid"],
                            "name": pinfo["name"],
                            "cpu_percent": normalized_cpu,
                            "memory_percent": memory_percent,
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                continue

        # Sort by CPU usage
        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)

        # If no processes found, return a message
        if not processes:
            return [
                {
                    "name": "No significant processes found",
                    "cpu_percent": 0,
                    "memory_percent": 0,
                }
            ]

        return processes[:5]  # Return top 5 processes
    except Exception as e:
        print(f"Error in get_process_power_usage: {str(e)}")
        return [
            {
                "name": "Error getting process info",
                "cpu_percent": 0,
                "memory_percent": 0,
            }
        ]


def get_battery_info():
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return {
                "percentage": "N/A",
                "power_plugged": False,
                "time_left": "No battery found",
            }

        percent = battery.percent
        power_plugged = battery.power_plugged
        time_left = battery.secsleft

        # Handle different time_left scenarios
        if time_left == -2:  # Battery is charging
            time_left = "Charging"
        elif time_left == -1:  # Windows can't determine time
            time_left = "Calculating..."
        else:
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            time_left = f"{hours}h {minutes}m"

        return {
            "percentage": percent,
            "power_plugged": power_plugged,
            "time_left": time_left,
        }
    except Exception as e:
        return {
            "percentage": "Error",
            "power_plugged": False,
            "time_left": f"Error: {str(e)}",
        }


def save_battery_log(info, top_processes, process_history):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create a detailed log entry with sections
        log_entry = f"\n{'='*50}\n"
        log_entry += f"TIMESTAMP: {timestamp}\n"
        log_entry += f"{'-'*50}\n"

        # Battery Status Section
        log_entry += "BATTERY STATUS:\n"
        log_entry += f"  Percentage: {info['percentage']}%\n"
        log_entry += (
            f"  Power Status: {'Plugged' if info['power_plugged'] else 'Unplugged'}\n"
        )
        log_entry += f"  Time Left: {info['time_left']}\n"

        # System Resources Section
        log_entry += f"\nSYSTEM RESOURCES:\n"
        log_entry += f"  CPU Usage: {psutil.cpu_percent():.1f}%\n"
        log_entry += f"  Memory Usage: {psutil.virtual_memory().percent:.1f}%\n"
        log_entry += f"  Disk Usage: {psutil.disk_usage('/').percent:.1f}%\n"

        # Top Processes Section
        log_entry += f"\nTOP POWER-CONSUMING PROCESSES:\n"
        if top_processes:
            # Sort by CPU usage (excluding System Idle Process)
            active_processes = [
                p for p in top_processes if p["name"] != "System Idle Process"
            ]
            active_processes.sort(key=lambda x: x["cpu_percent"], reverse=True)

            # CPU-intensive processes
            log_entry += "  CPU-Intensive (Top 3):\n"
            for proc in active_processes[:3]:
                pid = proc["pid"]
                if pid in process_history:
                    cpu_values = [v for _, v in process_history[pid]["cpu_history"]]
                    memory_values = [
                        v for _, v in process_history[pid]["memory_history"]
                    ]
                    avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                    avg_memory = (
                        sum(memory_values) / len(memory_values) if memory_values else 0
                    )
                    log_entry += f"    - {proc['name']}:\n"
                    log_entry += f"      Current: CPU {proc['cpu_percent']:.1f}%, Memory {proc['memory_percent']:.1f}%\n"
                    log_entry += (
                        f"      Average: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%\n"
                    )

            # Memory-intensive processes
            log_entry += "  Memory-Intensive (Top 3):\n"
            memory_processes = sorted(
                active_processes, key=lambda x: x["memory_percent"], reverse=True
            )
            for proc in memory_processes[:3]:
                pid = proc["pid"]
                if pid in process_history:
                    cpu_values = [v for _, v in process_history[pid]["cpu_history"]]
                    memory_values = [
                        v for _, v in process_history[pid]["memory_history"]
                    ]
                    avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                    avg_memory = (
                        sum(memory_values) / len(memory_values) if memory_values else 0
                    )
                    log_entry += f"    - {proc['name']}:\n"
                    log_entry += f"      Current: CPU {proc['cpu_percent']:.1f}%, Memory {proc['memory_percent']:.1f}%\n"
                    log_entry += (
                        f"      Average: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%\n"
                    )

            # System Idle Process
            idle_processes = [
                p for p in top_processes if p["name"] == "System Idle Process"
            ]
            if idle_processes:
                current_proc = idle_processes[0]
                pid = current_proc["pid"]
                if pid in process_history:
                    cpu_values = [v for _, v in process_history[pid]["cpu_history"]]
                    memory_values = [
                        v for _, v in process_history[pid]["memory_history"]
                    ]
                    avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                    avg_memory = (
                        sum(memory_values) / len(memory_values) if memory_values else 0
                    )
                    log_entry += f"  System Idle:\n"
                    log_entry += f"    Current: CPU {current_proc['cpu_percent']:.1f}%, Memory {current_proc['memory_percent']:.1f}%\n"
                    log_entry += (
                        f"    Average: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%\n"
                    )
        else:
            log_entry += "  No significant processes found\n"

        # Add a separator at the end
        log_entry += f"{'='*50}\n"

        # Append to log file
        with open("battery_log.txt", "a") as f:
            f.write(log_entry)

    except Exception as e:
        print(f"Error saving log: {str(e)}")


def load_charge_cycles():
    try:
        if os.path.exists("charge_cycles.json"):
            with open("charge_cycles.json", "r") as f:
                data = json.load(f)
                # Ensure charge_range_stats exists for backward compatibility
                if "charge_range_stats" not in data:
                    data["charge_range_stats"] = {
                        "0-49": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                        "50-79": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                        "80-100": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                    }
                return data
        return {
            "charge_cycles": [],
            "discharge_cycles": [],
            "charge_thresholds": {
                "80": {"times": [], "average": 0},
                "85": {"times": [], "average": 0},
                "90": {"times": [], "average": 0},
                "95": {"times": [], "average": 0},
                "100": {"times": [], "average": 0},
            },
            "discharge_thresholds": {
                "20": {"times": [], "average": 0},
                "15": {"times": [], "average": 0},
                "10": {"times": [], "average": 0},
                "5": {"times": [], "average": 0},
                "0": {"times": [], "average": 0},
            },
            "charge_range_stats": {
                "0-49": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "50-79": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "80-100": {"cycles": [], "avg_rate": 0, "avg_time": 0},
            },
        }
    except Exception as e:
        print(f"Error loading charge cycles: {str(e)}")
        return {
            "charge_cycles": [],
            "discharge_cycles": [],
            "charge_thresholds": {
                "80": {"times": [], "average": 0},
                "85": {"times": [], "average": 0},
                "90": {"times": [], "average": 0},
                "95": {"times": [], "average": 0},
                "100": {"times": [], "average": 0},
            },
            "discharge_thresholds": {
                "20": {"times": [], "average": 0},
                "15": {"times": [], "average": 0},
                "10": {"times": [], "average": 0},
                "5": {"times": [], "average": 0},
                "0": {"times": [], "average": 0},
            },
            "charge_range_stats": {
                "0-49": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "50-79": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "80-100": {"cycles": [], "avg_rate": 0, "avg_time": 0},
            },
        }


def save_charge_cycles(data):
    try:
        with open("charge_cycles.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving charge cycles: {str(e)}")


def update_threshold_data(data, cycle_type, threshold, time_to_threshold):
    try:
        threshold_key = f"{cycle_type}_thresholds"
        threshold_str = str(threshold)

        if threshold_str in data[threshold_key]:
            data[threshold_key][threshold_str]["times"].append(time_to_threshold)
            # Keep only last 10 times
            if len(data[threshold_key][threshold_str]["times"]) > 10:
                data[threshold_key][threshold_str]["times"] = data[threshold_key][
                    threshold_str
                ]["times"][-10:]
            # Calculate new average
            data[threshold_key][threshold_str]["average"] = sum(
                data[threshold_key][threshold_str]["times"]
            ) / len(data[threshold_key][threshold_str]["times"])

            save_charge_cycles(data)
    except Exception as e:
        print(f"Error updating threshold data: {str(e)}")


def calculate_range_for_cycle(start_percent, end_percent):
    """
    Determine which range(s) a cycle belongs to and calculate proportions.
    Returns a list of tuples: (range_key, percent_in_range, proportion)
    """
    ranges = []
    range_definitions = [
        ("0-49", 0, 49),
        ("50-79", 50, 79),
        ("80-100", 80, 100),
    ]
    
    total_percent_change = abs(end_percent - start_percent)
    if total_percent_change == 0:
        return ranges
    
    for range_key, range_start, range_end in range_definitions:
        # Calculate overlap between cycle and range
        overlap_start = max(start_percent, range_start)
        overlap_end = min(end_percent, range_end)
        
        if overlap_start < overlap_end:
            percent_in_range = overlap_end - overlap_start
            proportion = percent_in_range / total_percent_change
            ranges.append((range_key, percent_in_range, proportion))
    
    return ranges


def update_range_statistics(data, range_key, cycle_data):
    """
    Update range statistics with a new cycle entry.
    """
    try:
        if "charge_range_stats" not in data:
            data["charge_range_stats"] = {
                "0-49": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "50-79": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "80-100": {"cycles": [], "avg_rate": 0, "avg_time": 0},
            }
        
        if range_key in data["charge_range_stats"]:
            data["charge_range_stats"][range_key]["cycles"].append(cycle_data)
            
            # Keep only last 20 cycles per range
            if len(data["charge_range_stats"][range_key]["cycles"]) > 20:
                data["charge_range_stats"][range_key]["cycles"] = \
                    data["charge_range_stats"][range_key]["cycles"][-20:]
            
            # Recalculate averages
            cycles = data["charge_range_stats"][range_key]["cycles"]
            if cycles:
                data["charge_range_stats"][range_key]["avg_rate"] = \
                    sum(c["rate_per_hour"] for c in cycles) / len(cycles)
                data["charge_range_stats"][range_key]["avg_time"] = \
                    sum(c["duration"] for c in cycles) / len(cycles)
        
        save_charge_cycles(data)
    except Exception as e:
        print(f"Error updating range statistics: {str(e)}")


def analyze_range_statistics(data):
    """
    Analyze existing charge cycles to populate range statistics.
    """
    try:
        # Initialize range stats if not present
        if "charge_range_stats" not in data:
            data["charge_range_stats"] = {
                "0-49": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "50-79": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "80-100": {"cycles": [], "avg_rate": 0, "avg_time": 0},
            }
        
        # Clear existing range stats to rebuild from scratch
        for range_key in data["charge_range_stats"]:
            data["charge_range_stats"][range_key]["cycles"] = []
        
        # Analyze each charge cycle
        for cycle in data["charge_cycles"]:
            start_percent = cycle.get("start_percent", 0)
            end_percent = cycle.get("percent", 0)
            duration = cycle.get("duration", 0)
            rate_per_hour = cycle.get("rate_per_hour", 0)
            
            # Only process cycles with valid data
            if start_percent < end_percent and duration > 0:
                ranges = calculate_range_for_cycle(start_percent, end_percent)
                
                for range_key, percent_in_range, proportion in ranges:
                    # Create a proportional cycle entry for this range
                    range_cycle = {
                        "start_percent": max(start_percent, 
                                           0 if range_key == "0-49" else 
                                           50 if range_key == "50-79" else 80),
                        "end_percent": min(end_percent,
                                         49 if range_key == "0-49" else
                                         79 if range_key == "50-79" else 100),
                        "duration": duration * proportion,
                        "rate_per_hour": rate_per_hour,  # Rate remains the same
                    }
                    
                    data["charge_range_stats"][range_key]["cycles"].append(range_cycle)
        
        # Calculate averages for each range
        for range_key in data["charge_range_stats"]:
            cycles = data["charge_range_stats"][range_key]["cycles"]
            if cycles:
                # Keep only last 20 cycles
                if len(cycles) > 20:
                    data["charge_range_stats"][range_key]["cycles"] = cycles[-20:]
                    cycles = data["charge_range_stats"][range_key]["cycles"]
                
                data["charge_range_stats"][range_key]["avg_rate"] = \
                    sum(c["rate_per_hour"] for c in cycles) / len(cycles)
                data["charge_range_stats"][range_key]["avg_time"] = \
                    sum(c["duration"] for c in cycles) / len(cycles)
        
        save_charge_cycles(data)
        print("Range statistics analyzed and populated from existing cycles.")
    except Exception as e:
        print(f"Error analyzing range statistics: {str(e)}")


def analyze_existing_cycles(data):
    """Analyze existing cycles to populate threshold data"""
    try:
        # Analyze charge cycles
        for cycle in data["charge_cycles"]:
            start_time = datetime.fromisoformat(cycle["start"])
            end_time = datetime.fromisoformat(cycle["end"])
            start_percent = cycle.get("start_percent", 0)
            end_percent = cycle["percent"]

            # Calculate time to reach each threshold
            thresholds = [80, 85, 90, 95, 100]
            for threshold in thresholds:
                if start_percent < threshold <= end_percent:
                    # Estimate time to reach this threshold
                    total_duration = cycle["duration"]
                    percent_range = end_percent - start_percent
                    if percent_range > 0:
                        threshold_progress = (threshold - start_percent) / percent_range
                        time_to_threshold = total_duration * threshold_progress
                        update_threshold_data(
                            data, "charge", threshold, time_to_threshold
                        )

        # Analyze discharge cycles
        for cycle in data["discharge_cycles"]:
            start_time = datetime.fromisoformat(cycle["start"])
            end_time = datetime.fromisoformat(cycle["end"])
            start_percent = cycle.get("start_percent", 100)
            end_percent = cycle["percent"]

            # Calculate time to reach each threshold
            thresholds = [20, 15, 10, 5, 0]
            for threshold in thresholds:
                if start_percent > threshold >= end_percent:
                    # Estimate time to reach this threshold
                    total_duration = cycle["duration"]
                    percent_range = start_percent - end_percent
                    if percent_range > 0:
                        threshold_progress = (start_percent - threshold) / percent_range
                        time_to_threshold = total_duration * threshold_progress
                        update_threshold_data(
                            data, "discharge", threshold, time_to_threshold
                        )

        save_charge_cycles(data)
        print("Existing cycles analyzed and threshold data populated.")
    except Exception as e:
        print(f"Error analyzing existing cycles: {str(e)}")


def update_cycle(
    data, cycle_type, start_time, end_time, current_percent, start_percent=None
):
    try:
        duration = (end_time - start_time).total_seconds() / 60  # Convert to minutes

        # Create cycle entry
        cycle_entry = {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "duration": duration,
            "percent": current_percent,
        }
        if start_percent is not None:
            cycle_entry["start_percent"] = start_percent
            cycle_entry["percent_change"] = current_percent - start_percent
            cycle_entry["rate_per_hour"] = (
                cycle_entry["percent_change"] / duration
            ) * 60  # percent per hour

        # Add to appropriate cycle list
        cycle_list = f"{cycle_type}_cycles"
        data[cycle_list].append(cycle_entry)

        # Keep only last 20 cycles (increased from 10 for better statistics)
        if len(data[cycle_list]) > 20:
            data[cycle_list] = data[cycle_list][-20:]

        # Update range statistics for charge cycles
        if cycle_type == "charge" and start_percent is not None and start_percent < current_percent:
            ranges = calculate_range_for_cycle(start_percent, current_percent)
            for range_key, percent_in_range, proportion in ranges:
                range_cycle = {
                    "start_percent": max(start_percent, 
                                       0 if range_key == "0-49" else 
                                       50 if range_key == "50-79" else 80),
                    "end_percent": min(current_percent,
                                     49 if range_key == "0-49" else
                                     79 if range_key == "50-79" else 100),
                    "duration": duration * proportion,
                    "rate_per_hour": cycle_entry["rate_per_hour"],
                }
                update_range_statistics(data, range_key, range_cycle)

        save_charge_cycles(data)
        return data
    except Exception as e:
        print(f"Error updating {cycle_type} cycle: {str(e)}")
        return None


def estimate_charge_time_segmented(charge_data, current_percent):
    """
    Estimate time to 100% using segmented charging rates for different battery ranges.
    Returns estimated minutes to 100% and a breakdown by segment.
    """
    try:
        total_time = 0
        segments = []

        # Define charging segments with their typical ranges
        segment_ranges = [
            (current_percent, min(90, 100), "start to 90%"),
            (max(current_percent, 90), min(95, 100), "90% to 95%"),
            (max(current_percent, 95), 100, "95% to 100%"),
        ]

        for start, end, label in segment_ranges:
            if start >= end:
                continue

            percent_to_charge = end - start

            # Find relevant cycles for this range
            relevant_cycles = [
                c
                for c in charge_data["charge_cycles"]
                if c.get("start_percent", 0) <= start < c.get("percent", 0)
                or (c.get("start_percent", 0) >= start and c.get("percent", 0) <= end)
            ]

            if relevant_cycles:
                avg_rate = sum(abs(c["rate_per_hour"]) for c in relevant_cycles) / len(
                    relevant_cycles
                )
                segment_time = (
                    (percent_to_charge / avg_rate) * 60 if avg_rate > 0 else 0
                )
            else:
                # Use a conservative estimate if no data available
                # Higher percentages charge slower
                if start >= 95:
                    estimated_rate = 5  # Very slow near 100%
                elif start >= 90:
                    estimated_rate = 10  # Slower at 90-95%
                else:
                    estimated_rate = 20  # Faster below 90%
                segment_time = (
                    (percent_to_charge / estimated_rate) * 60
                    if estimated_rate > 0
                    else 0
                )

            total_time += segment_time
            if segment_time > 0:
                segments.append(
                    {"range": label, "percent": percent_to_charge, "time": segment_time}
                )

        return total_time, segments
    except Exception as e:
        print(f"Error in segmented charge estimation: {str(e)}")
        return 0, []


def interactive_battery_assistant():
    """
    Interactive AI assistant for battery analysis.
    """
    print("\n" + "="*60)
    print("BATTERY AI ASSISTANT (Mode 2)")
    print("="*60)
    print("Ask questions about your battery health, charging patterns,")
    print("and get AI-powered predictions and recommendations.")
    print("\nType 'exit' or 'quit' to return to main menu.")
    print("="*60 + "\n")
    
    # Check if Ollama is available
    print("Checking Ollama connection...")
    is_available, error_msg = check_ollama_available()
    if not is_available:
        print(f"\n❌ ERROR: {error_msg}")
        print("\nTo use Mode 2, you need:")
        print("  1. Install Ollama from https://ollama.ai")
        print("  2. Run: ollama pull llama3.1:8b")
        print("  3. Make sure Ollama is running")
        return
    print("✓ Ollama connected successfully\n")
    
    # Prepare battery data once
    print("Loading battery data...")
    try:
        battery_data = format_battery_data_for_ai()
        print("Data loaded. Ready for questions!\n")
    except Exception as e:
        print(f"Error loading battery data: {str(e)}")
        return
    
    # Conversation history for context
    conversation_history = []
    
    while True:
        try:
            user_input = input("\nYour Question: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Exiting AI assistant...")
                break
            
            if not user_input:
                continue
            
            print("\nThinking...")
            
            # Build context with conversation history
            context = battery_data
            if conversation_history:
                context += "\n\n=== PREVIOUS CONVERSATION ===\n"
                for q, a in conversation_history[-3:]:  # Last 3 exchanges
                    context += f"Q: {q}\nA: {a}\n\n"
            
            response = send_prompt(user_input, context)
            print(f"\nAssistant: {response}\n")
            
            # Store in conversation history
            conversation_history.append((user_input, response))
            
        except KeyboardInterrupt:
            print("\n\nExiting AI assistant...")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Make sure Ollama is running with: ollama run llama3.1:8b")


def main():
    print("Battery Monitor Started...")
    print("Press Ctrl+C to stop monitoring")
    print("\n" + "=" * 60)
    print("IMPROVED CHARGE TRACKING:")
    print("- Now records charge cycles at 90%, 95%, and 100% thresholds")
    print("- Uses range-specific rates for accurate time estimates")
    print("- Accounts for slower charging at higher percentages")
    print("=" * 60 + "\n")
    logging = 0

    # Load and analyze existing data
    charge_data = load_charge_cycles()
    analyze_existing_cycles(charge_data)
    analyze_range_statistics(charge_data)

    # Display current data status
    print(f"Current Data Status:")
    print(f"  - Charge Cycles: {len(charge_data['charge_cycles'])} recorded")
    print(f"  - Discharge Cycles: {len(charge_data['discharge_cycles'])} recorded")
    if len(charge_data["charge_cycles"]) == 0:
        print("  ✓ Starting fresh - ready to collect accurate charging data!")
    print()

    # Memory cleanup thresholds
    MEMORY_THRESHOLD = 80  # Percentage
    last_cleanup_time = 0
    CLEANUP_COOLDOWN = 300  # 5 minutes in seconds

    # Charge/discharge cycle tracking
    last_charge_state = None
    cycle_start_time = None
    cycle_start_percent = None
    first_state_change_time = None
    first_state_percent = None
    last_percent = None
    last_percent_change_time = datetime.now()
    reached_charge_thresholds = set()
    reached_discharge_thresholds = set()

    # --- Battery stability tracking ---
    battery_percent_history = []  # List of (timestamp, percent)
    BATTERY_STABLE_DURATION = 300  # 5 minutes in seconds
    BATTERY_STABLE_THRESHOLD = 3  # ±3% threshold
    battery_stable_state = False
    last_stable_percent = None

    # --- Process usage history tracking ---
    process_history = {}  # Dictionary to store process usage history
    PROCESS_HISTORY_DURATION = 300  # 5 minutes in seconds
    idle_proc_count = 0

    # --- Periodic save tracking ---
    last_save_time = datetime.now()
    SAVE_INTERVAL = 60  # Save every 60 seconds to prevent data loss

    try:
        while True:
            battery_info = get_battery_info()
            # top_processes = get_process_power_usage()  # Temporarily disabled
            now = time.time()

            # --- Temporarily disable process history update ---
            # for proc in top_processes:
            #     pid = proc['pid']
            #     if pid not in process_history:
            #         process_history[pid] = {
            #             'name': proc['name'],
            #             'cpu_history': [],
            #             'memory_history': []
            #         }
            #
            #     # Add current readings
            #     process_history[pid]['cpu_history'].append((now, proc['cpu_percent']))
            #     process_history[pid]['memory_history'].append((now, proc['memory_percent']))
            #
            #     # Clean up old readings
            #     cutoff_time = now - PROCESS_HISTORY_DURATION
            #     process_history[pid]['cpu_history'] = [(t, v) for t, v in process_history[pid]['cpu_history'] if t > cutoff_time]
            #     process_history[pid]['memory_history'] = [(t, v) for t, v in process_history[pid]['memory_history'] if t > cutoff_time]
            #
            # # Clean up processes that are no longer running
            # current_pids = {p['pid'] for p in top_processes}
            # process_history = {pid: data for pid, data in process_history.items() if pid in current_pids}

            # Track charge/discharge cycles
            current_charge_state = battery_info["power_plugged"]
            current_percent = battery_info["percentage"]

            if last_charge_state is None:
                last_charge_state = current_charge_state
                last_percent = current_percent
                last_percent_change_time = datetime.now()
                cycle_start_time = datetime.now()
                cycle_start_percent = current_percent
            elif current_percent != last_percent:
                last_percent_change_time = datetime.now()
                last_percent = current_percent

            # Detect state changes (charging to discharging or vice versa)
            if last_charge_state != current_charge_state:
                if cycle_start_time is not None:
                    # Record the completed cycle
                    cycle_type = "charge" if last_charge_state else "discharge"
                    update_cycle(
                        load_charge_cycles(),
                        cycle_type,
                        cycle_start_time,
                        datetime.now(),
                        last_percent,
                        cycle_start_percent,
                    )

                # Start new cycle
                cycle_start_time = datetime.now()
                cycle_start_percent = current_percent
                first_state_change_time = datetime.now()
                first_state_percent = current_percent
                if current_charge_state:
                    reached_charge_thresholds.clear()
                else:
                    reached_discharge_thresholds.clear()

            # Track charging progress
            if current_charge_state:
                thresholds = [49, 79, 80, 85, 90, 95, 100]
                for threshold in thresholds:
                    if (
                        threshold not in reached_charge_thresholds
                        and current_percent >= threshold
                        and (last_percent is None or last_percent < threshold)
                    ):
                        reached_charge_thresholds.add(threshold)
                        # Calculate time to reach this threshold
                        time_to_threshold = (
                            datetime.now() - cycle_start_time
                        ).total_seconds() / 60
                        
                        # Only update threshold data for the original thresholds
                        if threshold in [80, 85, 90, 95, 100]:
                            update_threshold_data(
                                load_charge_cycles(), "charge", threshold, time_to_threshold
                            )
                        
                        print(
                            f"\nReached {threshold}% charge in {time_to_threshold:.1f} minutes"
                        )

                        # Record charge cycle segments at major thresholds (49%, 79%, 90%, 95%, 100%)
                        if threshold in [49, 79, 90, 95, 100] and cycle_start_time is not None:
                            update_cycle(
                                load_charge_cycles(),
                                "charge",
                                cycle_start_time,
                                datetime.now(),
                                current_percent,
                                cycle_start_percent,
                            )
                            print(
                                f"Charge cycle recorded: {cycle_start_percent}% → {threshold}% in {time_to_threshold:.1f} minutes"
                            )
                            # Reset cycle tracking for next segment
                            if threshold < 100:  # Don't reset if we've reached 100%
                                cycle_start_time = datetime.now()
                                cycle_start_percent = current_percent

            # Track discharging progress
            else:
                thresholds = [20, 15, 10, 5, 0]
                for threshold in thresholds:
                    if (
                        threshold not in reached_discharge_thresholds
                        and current_percent <= threshold
                        and (last_percent is None or last_percent > threshold)
                    ):
                        reached_discharge_thresholds.add(threshold)
                        # Calculate time to reach this threshold
                        time_to_threshold = (
                            datetime.now() - cycle_start_time
                        ).total_seconds() / 60
                        update_threshold_data(
                            load_charge_cycles(),
                            "discharge",
                            threshold,
                            time_to_threshold,
                        )
                        print(
                            f"\nReached {threshold}% discharge in {time_to_threshold:.1f} minutes"
                        )

                        # Record discharge cycle segments at major thresholds (20%, 10%, 5%)
                        if threshold in [20, 10, 5] and cycle_start_time is not None:
                            update_cycle(
                                load_charge_cycles(),
                                "discharge",
                                cycle_start_time,
                                datetime.now(),
                                current_percent,
                                cycle_start_percent,
                            )
                            print(
                                f"Discharge cycle recorded: {cycle_start_percent}% → {threshold}% in {time_to_threshold:.1f} minutes"
                            )
                            # Reset cycle tracking for next segment
                            if threshold > 5:  # Don't reset if we're at 5% or below
                                cycle_start_time = datetime.now()
                                cycle_start_percent = current_percent

            last_charge_state = current_charge_state
            last_percent = current_percent

            # Periodic save to prevent data loss (every 60 seconds)
            if (datetime.now() - last_save_time).total_seconds() >= SAVE_INTERVAL:
                charge_data = load_charge_cycles()
                save_charge_cycles(charge_data)
                last_save_time = datetime.now()

            # Get system memory usage
            memory_usage = psutil.virtual_memory().percent

            # Check if memory cleanup is needed
            current_time = time.time()
            if (
                memory_usage > MEMORY_THRESHOLD
                and (current_time - last_cleanup_time) > CLEANUP_COOLDOWN
            ):
                print("\n=== High Memory Usage Detected ===")
                print(f"Memory Usage: {memory_usage}%")
                print("Initiating memory cleanup...")

                if cleanup_memory():
                    print("Memory cleanup completed successfully")
                    last_cleanup_time = current_time
                else:
                    print("Memory cleanup failed")

            # Clear screen for better visibility
            os.system("cls" if os.name == "nt" else "clear")
            current_time = datetime.now()
            print(f"\nCurrent Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("\n=== Battery Status ===")
            print(f"Battery Percentage: {battery_info['percentage']}%")
            print(
                f"Power Status: {'Plugged' if battery_info['power_plugged'] else 'Unplugged'}"
            )

            # Display cycle information
            charge_data = load_charge_cycles()

            # Display charging information
            if battery_info["power_plugged"]:
                if battery_info["percentage"] < 100:
                    try:
                        current_percent = battery_info["percentage"]
                        remaining_percent = 100 - current_percent

                        # Initialize first state if not set
                        if (
                            first_state_change_time is None
                            or first_state_percent is None
                        ):
                            first_state_change_time = current_time
                            first_state_percent = current_percent

                        # Calculate estimated time based on historical data with range-specific rates
                        if charge_data["charge_cycles"]:
                            # Filter cycles based on current battery range for more accurate estimates
                            relevant_cycles = []

                            # For 80-89%: use cycles starting between 70-89%
                            # For 90-94%: use cycles starting between 80-94%
                            # For 95-99%: use cycles starting between 90-99%
                            if current_percent < 90:
                                relevant_cycles = [
                                    c
                                    for c in charge_data["charge_cycles"]
                                    if c.get("start_percent", 0) < 90
                                ]
                            elif current_percent < 95:
                                relevant_cycles = [
                                    c
                                    for c in charge_data["charge_cycles"]
                                    if 80 <= c.get("start_percent", 0) < 95
                                ]
                            else:
                                relevant_cycles = [
                                    c
                                    for c in charge_data["charge_cycles"]
                                    if c.get("start_percent", 0) >= 90
                                ]

                            # Use relevant cycles if available, otherwise fall back to all cycles
                            if relevant_cycles:
                                avg_rate = sum(
                                    cycle["rate_per_hour"] for cycle in relevant_cycles
                                ) / len(relevant_cycles)
                                print(
                                    f"Average Charge Rate ({len(relevant_cycles)} relevant cycles): {avg_rate:.1f}%/hour"
                                )
                            else:
                                avg_rate = sum(
                                    cycle["rate_per_hour"]
                                    for cycle in charge_data["charge_cycles"]
                                ) / len(charge_data["charge_cycles"])
                                print(
                                    f"Average Charge Rate (all {len(charge_data['charge_cycles'])} cycles): {avg_rate:.1f}%/hour"
                                )

                            estimated_charge_time = (
                                (remaining_percent / avg_rate) * 60
                                if avg_rate > 0
                                else remaining_percent
                            )

                            # Also show segmented estimate if we have enough data
                            if len(charge_data["charge_cycles"]) >= 3:
                                seg_time, segments = estimate_charge_time_segmented(
                                    charge_data, current_percent
                                )
                                if (
                                    seg_time > 0
                                    and abs(seg_time - estimated_charge_time) > 5
                                ):  # Show if significantly different
                                    print(f"Segmented Estimate: {seg_time:.1f} minutes")
                                    estimated_charge_time = seg_time  # Use the more accurate segmented estimate
                        else:
                            # Calculate rate based on current charging session
                            time_diff = (
                                current_time - first_state_change_time
                            ).total_seconds() / 60  # in minutes
                            percent_diff = current_percent - first_state_percent
                            
                            # Require minimum time (1 min) and percent change (1%) for accurate calculation
                            if time_diff >= 1.0 and percent_diff >= 1:
                                current_rate = (
                                    percent_diff / time_diff
                                ) * 60  # convert to per hour
                                estimated_charge_time = (
                                    remaining_percent / current_rate
                                ) * 60
                                print(
                                    f"Current Charge Rate: {current_rate:.1f}%/hour"
                                )
                                print(
                                    f"(Based on {percent_diff}% gain in {time_diff:.1f} minutes - need more data for better accuracy)"
                                )
                            else:
                                # Not enough data yet, use conservative estimate
                                estimated_charge_time = remaining_percent * 3  # Assume ~20%/hour (conservative)
                                if percent_diff < 1:
                                    seconds_elapsed = (current_time - first_state_change_time).total_seconds()
                                    print(f"Monitoring charge... ({seconds_elapsed:.0f}s elapsed, waiting for battery to increase from {first_state_percent}%)")
                                elif time_diff < 1.0:
                                    wait_seconds = (1.0 - time_diff) * 60
                                    print(f"Monitoring charge rate... (wait {max(1, wait_seconds):.0f} more seconds for accurate rate)")
                                else:
                                    print("Calculating charge rate...")

                        charge_end_time = current_time + timedelta(
                            minutes=estimated_charge_time
                        )
                        if (
                            current_percent == last_percent
                            and (
                                datetime.now() - last_percent_change_time
                            ).total_seconds()
                            >= 90
                        ):
                            print("Charging paused or possible full charge")
                        else:
                            # Format time display based on duration
                            if estimated_charge_time >= 60:
                                hours = int(estimated_charge_time // 60)
                                minutes = int(estimated_charge_time % 60)
                                time_str = f"{hours}h {minutes}m"
                            else:
                                time_str = f"{estimated_charge_time:.1f} minutes"

                            print(
                                f"Time to Full Charge: {time_str} (Until {charge_end_time.strftime('%I:%M %p')})"
                            )

                            # Show system's estimated time to full charge
                            if battery_info["time_left"] == "Charging":
                                print("System Status: Currently Charging")
                            else:
                                print(
                                    f"System Estimated Time to Full: {battery_info['time_left']}"
                                )

                            # Show charging rate breakdown by segment
                            if len(charge_data["charge_cycles"]) >= 2:
                                print("\nCharging Rate by Range:")
                                for range_label, start_range, end_range in [
                                    ("Below 90%", 0, 89),
                                    ("90-94%", 90, 94),
                                    ("95-100%", 95, 100),
                                ]:
                                    range_cycles = [
                                        c
                                        for c in charge_data["charge_cycles"]
                                        if start_range
                                        <= c.get("start_percent", 0)
                                        <= end_range
                                    ]
                                    if range_cycles:
                                        avg_rate_range = sum(
                                            abs(c["rate_per_hour"])
                                            for c in range_cycles
                                        ) / len(range_cycles)
                                        print(
                                            f"  {range_label}: {avg_rate_range:.1f}%/hour ({len(range_cycles)} samples)"
                                        )
                            
                            # Show charging statistics by battery range (0-49%, 50-79%, 80-100%)
                            if "charge_range_stats" in charge_data:
                                print("\nCharging Statistics by Battery Range:")
                                for range_key in ["0-49", "50-79", "80-100"]:
                                    range_data = charge_data["charge_range_stats"].get(range_key, {})
                                    cycles = range_data.get("cycles", [])
                                    if cycles:
                                        avg_rate = range_data.get("avg_rate", 0)
                                        avg_time = range_data.get("avg_time", 0)
                                        print(f"  {range_key}%:")
                                        print(f"    - Average Rate: {avg_rate:.1f}%/hour")
                                        if avg_time >= 60:
                                            hours = int(avg_time // 60)
                                            minutes = int(avg_time % 60)
                                            print(f"    - Average Time: {hours}h {minutes}m")
                                        else:
                                            print(f"    - Average Time: {avg_time:.1f} minutes")
                                        print(f"    - Samples: {len(cycles)} cycles")

                            # Show estimated times to reach different thresholds
                            print("\nEstimated Times to Thresholds:")
                            thresholds = [80, 85, 90, 95, 100]
                            for threshold in thresholds:
                                if threshold > current_percent:
                                    remaining_to_threshold = threshold - current_percent
                                    if "current_rate" in locals() and current_rate > 0:
                                        time_to_threshold = (
                                            remaining_to_threshold / current_rate
                                        ) * 60
                                        if time_to_threshold >= 60:
                                            hours = int(time_to_threshold // 60)
                                            minutes = int(time_to_threshold % 60)
                                            time_str = f"{hours}h {minutes}m"
                                        else:
                                            time_str = (
                                                f"{time_to_threshold:.1f} minutes"
                                            )
                                        threshold_time = current_time + timedelta(
                                            minutes=time_to_threshold
                                        )
                                        print(
                                            f"  {threshold}%: {time_str} (Until {threshold_time.strftime('%I:%M %p')})"
                                        )
                    except Exception as e:
                        print(f"Unable to calculate charging time: {str(e)}")
                else:
                    print("Battery fully charged")
            else:
                if battery_info["time_left"] != "N/A":
                    try:
                        if (
                            "h" in battery_info["time_left"]
                            or "m" in battery_info["time_left"]
                        ):
                            hours = 0
                            minutes = 0
                            parts = battery_info["time_left"].split()
                            for part in parts:
                                if "h" in part:
                                    hours = int(part.replace("h", ""))
                                elif "m" in part:
                                    minutes = int(part.replace("m", ""))
                            time_left_minutes = hours * 60 + minutes
                        else:
                            hours, minutes = map(
                                int, battery_info["time_left"].split(":")
                            )
                            time_left_minutes = hours * 60 + minutes

                        # Calculate estimated time based on historical data
                        if charge_data["discharge_cycles"]:
                            avg_rate = sum(
                                cycle["rate_per_hour"]
                                for cycle in charge_data["discharge_cycles"]
                            ) / len(charge_data["discharge_cycles"])
                            if avg_rate < 0:  # Discharge rate is negative
                                estimated_time = (current_percent / abs(avg_rate)) * 60
                                time_left_minutes = min(
                                    time_left_minutes, estimated_time
                                )

                        estimated_end_time = current_time + timedelta(
                            minutes=time_left_minutes
                        )
                        print(
                            f"Time Left: {battery_info['time_left']} (Until {estimated_end_time.strftime('%I:%M %p')})"
                        )

                        # --- Show current discharge rate ---
                        time_diff = (
                            current_time - last_percent_change_time
                        ).total_seconds() / 60  # in minutes
                        percent_diff = (
                            last_percent - current_percent
                        )  # should be positive if discharging
                        
                        # Require minimum time (1 min) and percent change (1%) for accurate calculation
                        if time_diff >= 1.0 and percent_diff >= 1:
                            current_discharge_rate = (
                                percent_diff / time_diff
                            ) * 60  # % per hour
                            print(
                                f"Current Discharge Rate: {current_discharge_rate:.2f}%/hour"
                            )
                            print(
                                f"(Based on {percent_diff}% loss in {time_diff:.1f} minutes)"
                            )
                        else:
                            # Not enough data yet
                            if percent_diff < 1:
                                seconds_elapsed = (current_time - last_percent_change_time).total_seconds()
                                print(f"Monitoring discharge... ({seconds_elapsed:.0f}s since last change, waiting for battery to drop from {last_percent}%)")
                            elif time_diff < 1.0:
                                wait_seconds = (1.0 - time_diff) * 60
                                print(f"Monitoring discharge rate... (wait {max(1, wait_seconds):.0f} more seconds for accurate rate)")
                            else:
                                print("Calculating discharge rate...")
                    except ValueError:
                        print(
                            f"Time Left: {battery_info['time_left']} (Unable to parse time format)"
                        )
                else:
                    print(f"Time Left: {battery_info['time_left']}")
                    # --- Show current discharge rate even if time left is N/A ---
                    time_diff = (
                        current_time - last_percent_change_time
                    ).total_seconds() / 60  # in minutes
                    percent_diff = (
                        last_percent - current_percent
                    )  # should be positive if discharging
                    
                    # Require minimum time (1 min) and percent change (1%) for accurate calculation
                    if time_diff >= 1.0 and percent_diff >= 1:
                        current_discharge_rate = (
                            percent_diff / time_diff
                        ) * 60  # % per hour
                        print(
                            f"Current Discharge Rate: {current_discharge_rate:.2f}%/hour"
                        )
                        print(
                            f"(Based on {percent_diff}% loss in {time_diff:.1f} minutes)"
                        )
                    else:
                        # Not enough data yet
                        if percent_diff < 1:
                            seconds_elapsed = (current_time - last_percent_change_time).total_seconds()
                            print(f"Monitoring discharge... ({seconds_elapsed:.0f}s since last change, waiting for battery to drop from {last_percent}%)")
                        elif time_diff < 1.0:
                            wait_seconds = (1.0 - time_diff) * 60
                            print(f"Monitoring discharge rate... (wait {max(1, wait_seconds):.0f} more seconds for accurate rate)")
                        else:
                            print("Calculating discharge rate...")
                
                # Display discharge statistics and estimates
                if charge_data["discharge_cycles"]:
                    print("\n=== Discharge Statistics ===")
                    
                    # Calculate average discharge rate
                    avg_discharge_rate = sum(
                        abs(cycle["rate_per_hour"])
                        for cycle in charge_data["discharge_cycles"]
                    ) / len(charge_data["discharge_cycles"])
                    print(f"Average Discharge Rate: {avg_discharge_rate:.2f}%/hour")
                    print(f"(Based on {len(charge_data['discharge_cycles'])} recorded cycles)")
                    
                    # Show discharge rate by battery range
                    if len(charge_data["discharge_cycles"]) >= 2:
                        print("\nDischarge Rate by Battery Range:")
                        for range_label, start_range, end_range in [
                            ("High (80-100%)", 80, 100),
                            ("Medium (50-79%)", 50, 79),
                            ("Low (20-49%)", 20, 49),
                            ("Critical (<20%)", 0, 19),
                        ]:
                            range_cycles = [
                                c
                                for c in charge_data["discharge_cycles"]
                                if start_range <= c.get("start_percent", 0) <= end_range
                            ]
                            if range_cycles:
                                avg_rate_range = sum(
                                    abs(c["rate_per_hour"]) for c in range_cycles
                                ) / len(range_cycles)
                                print(
                                    f"  {range_label}: {avg_rate_range:.2f}%/hour ({len(range_cycles)} samples)"
                                )
                    
                    # Estimate time to critical thresholds
                    print("\nEstimated Time to Critical Levels:")
                    thresholds = [20, 15, 10, 5]
                    for threshold in thresholds:
                        if current_percent > threshold:
                            percent_to_threshold = current_percent - threshold
                            time_to_threshold = (percent_to_threshold / avg_discharge_rate) * 60
                            
                            if time_to_threshold >= 60:
                                hours = int(time_to_threshold // 60)
                                minutes = int(time_to_threshold % 60)
                                time_str = f"{hours}h {minutes}m"
                            else:
                                time_str = f"{time_to_threshold:.1f} minutes"
                            
                            threshold_time = current_time + timedelta(minutes=time_to_threshold)
                            print(
                                f"  To {threshold}%: {time_str} (Around {threshold_time.strftime('%I:%M %p')})"
                            )
                    
                    # Estimated total battery life
                    if avg_discharge_rate > 0:
                        total_life_minutes = (current_percent / avg_discharge_rate) * 60
                        if total_life_minutes >= 60:
                            hours = int(total_life_minutes // 60)
                            minutes = int(total_life_minutes % 60)
                            print(f"\nEstimated Time Until 0%: {hours}h {minutes}m")
                        else:
                            print(f"\nEstimated Time Until 0%: {total_life_minutes:.1f} minutes")
                        
                        empty_time = current_time + timedelta(minutes=total_life_minutes)
                        print(f"(Battery may reach 0% around {empty_time.strftime('%I:%M %p')})")

            # Display average cycle durations
            charge_thresholds_with_data = [
                t
                for t in charge_data["charge_thresholds"]
                if charge_data["charge_thresholds"][t]["times"]
            ]
            if charge_thresholds_with_data:
                print("\nAverage Charging Times:")
                for threshold in ["80", "85", "90", "95", "100"]:
                    if (
                        threshold in charge_data["charge_thresholds"]
                        and charge_data["charge_thresholds"][threshold]["times"]
                    ):
                        avg_time = charge_data["charge_thresholds"][threshold][
                            "average"
                        ]
                        count = len(
                            charge_data["charge_thresholds"][threshold]["times"]
                        )
                        print(
                            f"  To {threshold}%: {avg_time:.1f} minutes ({count} samples)"
                        )

            # Display average discharge times
            discharge_thresholds_with_data = [
                t
                for t in charge_data["discharge_thresholds"]
                if charge_data["discharge_thresholds"][t]["times"]
            ]
            if discharge_thresholds_with_data:
                print("\nAverage Discharge Times:")
                for threshold in ["20", "15", "10", "5", "0"]:
                    if (
                        threshold in charge_data["discharge_thresholds"]
                        and charge_data["discharge_thresholds"][threshold]["times"]
                    ):
                        avg_time = charge_data["discharge_thresholds"][threshold][
                            "average"
                        ]
                        count = len(
                            charge_data["discharge_thresholds"][threshold]["times"]
                        )
                        print(
                            f"  To {threshold}%: {avg_time:.1f} minutes ({count} samples)"
                        )
            # Display recent cycle information
            if charge_data["charge_cycles"] or charge_data["discharge_cycles"]:
                print("\nRecent Battery Cycles:")
                for cycle_type in ["charge", "discharge"]:
                    cycles = charge_data[f"{cycle_type}_cycles"]
                    if cycles:
                        latest = cycles[-1]
                        print(f"\nLast {cycle_type.title()} Cycle:")
                        print(
                            f"  Start: {datetime.fromisoformat(latest['start']).strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        print(
                            f"  End: {datetime.fromisoformat(latest['end']).strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        print(f"  Duration: {latest['duration']:.1f} minutes")
                        if "start_percent" in latest:
                            print(f"  Percentage Change: {latest['percent_change']}%")
                            print(f"  Rate: {latest['rate_per_hour']:.1f}%/hour")
                            # Show estimated time to full charge or full discharge, depending on cycle type and rate direction
                            rate = latest.get("rate_per_hour")
                            if rate and rate != 0:
                                if cycle_type == "charge" and rate > 0:
                                    time_to_full = 100 / rate * 60  # in minutes
                                    if time_to_full > 60:
                                        hours = int(time_to_full // 60)
                                        minutes = int(time_to_full % 60)
                                        print(
                                            f"  Estimated time to full charge: {hours} hours {minutes} minutes"
                                        )
                                    else:
                                        print(
                                            f"  Estimated time to full charge: {time_to_full:.1f} minutes"
                                        )
                                elif cycle_type == "discharge" and rate < 0:
                                    time_to_empty = 100 / abs(rate) * 60  # in minutes
                                    if time_to_empty > 60:
                                        hours = int(time_to_empty // 60)
                                        minutes = int(time_to_empty % 60)
                                        print(
                                            f"  Estimated time to full discharge: {hours} hours {minutes} minutes"
                                        )
                                    else:
                                        print(
                                            f"  Estimated time to full discharge: {time_to_empty:.1f} minutes"
                                        )
                                else:
                                    print(
                                        "  Estimated time to next charge/discharge: N/A"
                                    )
                            else:
                                print("  Estimated time to next charge/discharge: N/A")

            # Display average cycle durations
            charge_thresholds_with_data = [
                t
                for t in charge_data["charge_thresholds"]
                if charge_data["charge_thresholds"][t]["times"]
            ]
            if charge_thresholds_with_data:
                print("\nAverage Charging Times:")
                for threshold in ["80", "85", "90", "95", "100"]:
                    if (
                        threshold in charge_data["charge_thresholds"]
                        and charge_data["charge_thresholds"][threshold]["times"]
                    ):
                        avg_time = charge_data["charge_thresholds"][threshold][
                            "average"
                        ]
            print("\n=== Top Power-Consuming Processes ===")
            # --- Temporarily disable process display ---
            # if top_processes:
            #     active_processes = [p for p in top_processes if p['name'] != 'System Idle Process']
            #
            #     print("Top 5 CPU/Memory-Intensive Processes:")
            #     # Get top 5 by CPU and top 5 by Memory, then combine and deduplicate while preserving order
            #     top_cpu = sorted(active_processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
            #     top_mem = sorted(active_processes, key=lambda x: x['memory_percent'], reverse=True)[:5]
            #     seen = set()
            #     combined = []
            #     for proc in top_cpu + top_mem:
            #         key = proc['name']
            #         if key not in seen:
            #             combined.append(proc)
            #             seen.add(key)
            #     for proc in combined:
            #         print(f"  {proc['name']}: CPU {proc['cpu_percent']:.1f}%, Memory {proc['memory_percent']:.1f}%")
            #     # Print System Idle Process separately at the end with average usage
            #     idle_processes = [p for p in top_processes if p['name'] == 'System Idle Process']
            #     idle_proc_count += 1
            #     if idle_processes:
            #         avg_cpu_sys_proc = sum(p['cpu_percent'] for p in idle_processes) / idle_proc_count
            #         avg_memory_sys_proc = sum(p['memory_percent'] for p in idle_processes) / idle_proc_count
            #         current_proc = idle_processes[0]
            #         print(f"\nSystem Idle: CPU {current_proc['cpu_percent']:.1f}% (Avg: {avg_cpu_sys_proc:.1f}%), Memory {current_proc['memory_percent']:.1f}% (Avg: {avg_memory_sys_proc:.1f}%)")
            # else:
            #     print("No processes found")
            print("Process monitoring temporarily disabled.")

            # Print system resource usage with better formatting
            print("\n=== System Resource Usage (Average) ===")
            # Maintain running totals and counts for averages
            if "cpu_usage_total" not in locals():
                cpu_usage_total = 0.0
                memory_usage_total = 0.0
                disk_usage_total = 0.0
                usage_count = 0

            current_cpu = psutil.cpu_percent()
            current_mem = psutil.virtual_memory().percent
            current_disk = psutil.disk_usage("/").percent

            cpu_usage_total += current_cpu
            memory_usage_total += current_mem
            disk_usage_total += current_disk
            usage_count += 1

            avg_cpu = cpu_usage_total / usage_count
            avg_mem = memory_usage_total / usage_count
            avg_disk = disk_usage_total / usage_count

            print(f"CPU Usage (Avg):    {avg_cpu:>6.1f}%")
            print(f"Memory Usage (Avg): {avg_mem:>6.1f}%")
            print(f"Disk Usage (Avg):   {avg_disk:>6.1f}%")

            if logging == 1:
                print("\nLogging to battery_log.txt...")
                # save_battery_log(battery_info, top_processes, process_history)
                save_battery_log(
                    battery_info, None, process_history
                )  # top_processes temporarily disabled

            time.sleep(5)  # Update every 5 seconds
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("BATTERY MONITOR TOOL")
    print("="*60)
    print("Mode 1: Real-time Battery Monitoring")
    print("Mode 2: AI Battery Assistant (requires Ollama)")
    print("="*60)
    
    mode = input("\nEnter mode (1 or 2): ").strip()
    
    if mode == "1":
        print("\n[Mode 1] Battery Monitor")
        main()
    elif mode == "2":
        print("\n[Mode 2] AI Battery Assistant")
        
        # Check Ollama availability first
        print("\nChecking Ollama connection...")
        is_available, error_msg = check_ollama_available()
        if not is_available:
            print(f"\n❌ ERROR: {error_msg}")
            print("\nTo use Mode 2, you need:")
            print("  1. Install Ollama from https://ollama.ai")
            print("  2. Run: ollama pull llama3.1:8b")
            print("  3. Make sure Ollama is running")
        else:
            print("✓ Ollama connected successfully\n")
            print("\nOptions:")
            print("  1 - Interactive mode (ask multiple questions)")
            print("  2 - Quick question (ask once and exit)")
            
            sub_choice = input("\nChoose option (1 or 2): ").strip()
            
            if sub_choice == "1":
                interactive_battery_assistant()
            elif sub_choice == "2":
                try:
                    battery_data = format_battery_data_for_ai()
                    question = input("\nYour question: ").strip()
                    if question:
                        print("\nThinking...")
                        response = send_prompt(question, battery_data)
                        print(f"\nAssistant: {response}\n")
                    else:
                        print("No question provided.")
                except Exception as e:
                    print(f"\nError: {str(e)}")
            else:
                print("Invalid option")
    else:
        print("Invalid mode")
        exit()