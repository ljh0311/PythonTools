import psutil
import time
from datetime import datetime, timedelta
import os
from collections import defaultdict
import gc
import ctypes
import sys
import json

def cleanup_memory():
    try:
        # Force garbage collection
        gc.collect()
        
        # Clear memory cache on Windows
        if os.name == 'nt':
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
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Get process info without CPU calculation first
                pinfo = proc.info
                
                # Only check CPU for processes that might be significant
                # Skip system processes that are unlikely to be high usage
                skip_processes = {'System Idle Process', 'System', 'Registry', 'svchost.exe', 'csrss.exe', 'winlogon.exe'}
                if pinfo['name'] in skip_processes:
                    continue
                
                # Get CPU usage with minimal interval
                cpu_percent = proc.cpu_percent(interval=0.01)
                # Normalize CPU usage to percentage across all cores
                normalized_cpu = cpu_percent / cpu_count
                
                # Only get memory if CPU usage is significant
                if normalized_cpu > 0.5:
                    memory_percent = proc.memory_percent()
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'cpu_percent': normalized_cpu,
                        'memory_percent': memory_percent
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        # If no processes found, return a message
        if not processes:
            return [{'name': 'No significant processes found', 'cpu_percent': 0, 'memory_percent': 0}]
            
        return processes[:5]  # Return top 5 processes
    except Exception as e:
        print(f"Error in get_process_power_usage: {str(e)}")
        return [{'name': 'Error getting process info', 'cpu_percent': 0, 'memory_percent': 0}]

def get_battery_info():
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return {
                "percentage": "N/A",
                "power_plugged": False,
                "time_left": "No battery found"
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
            "time_left": time_left
        }
    except Exception as e:
        return {
            "percentage": "Error",
            "power_plugged": False,
            "time_left": f"Error: {str(e)}"
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
        log_entry += f"  Power Status: {'Plugged' if info['power_plugged'] else 'Unplugged'}\n"
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
            active_processes = [p for p in top_processes if p['name'] != 'System Idle Process']
            active_processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            # CPU-intensive processes
            log_entry += "  CPU-Intensive (Top 3):\n"
            for proc in active_processes[:3]:
                pid = proc['pid']
                if pid in process_history:
                    cpu_values = [v for _, v in process_history[pid]['cpu_history']]
                    memory_values = [v for _, v in process_history[pid]['memory_history']]
                    avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                    avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
                    log_entry += f"    - {proc['name']}:\n"
                    log_entry += f"      Current: CPU {proc['cpu_percent']:.1f}%, Memory {proc['memory_percent']:.1f}%\n"
                    log_entry += f"      Average: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%\n"
            
            # Memory-intensive processes
            log_entry += "  Memory-Intensive (Top 3):\n"
            memory_processes = sorted(active_processes, key=lambda x: x['memory_percent'], reverse=True)
            for proc in memory_processes[:3]:
                pid = proc['pid']
                if pid in process_history:
                    cpu_values = [v for _, v in process_history[pid]['cpu_history']]
                    memory_values = [v for _, v in process_history[pid]['memory_history']]
                    avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                    avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
                    log_entry += f"    - {proc['name']}:\n"
                    log_entry += f"      Current: CPU {proc['cpu_percent']:.1f}%, Memory {proc['memory_percent']:.1f}%\n"
                    log_entry += f"      Average: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%\n"
            
            # System Idle Process
            idle_processes = [p for p in top_processes if p['name'] == 'System Idle Process']
            if idle_processes:
                current_proc = idle_processes[0]
                pid = current_proc['pid']
                if pid in process_history:
                    cpu_values = [v for _, v in process_history[pid]['cpu_history']]
                    memory_values = [v for _, v in process_history[pid]['memory_history']]
                    avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
                    avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
                    log_entry += f"  System Idle:\n"
                    log_entry += f"    Current: CPU {current_proc['cpu_percent']:.1f}%, Memory {current_proc['memory_percent']:.1f}%\n"
                    log_entry += f"    Average: CPU {avg_cpu:.1f}%, Memory {avg_memory:.1f}%\n"
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
        if os.path.exists('charge_cycles.json'):
            with open('charge_cycles.json', 'r') as f:
                return json.load(f)
        return {
            'charge_cycles': [],
            'discharge_cycles': [],
            'charge_thresholds': {
                '80': {'times': [], 'average': 0},
                '85': {'times': [], 'average': 0},
                '90': {'times': [], 'average': 0},
                '95': {'times': [], 'average': 0},
                '100': {'times': [], 'average': 0}
            },
            'discharge_thresholds': {
                '20': {'times': [], 'average': 0},
                '15': {'times': [], 'average': 0},
                '10': {'times': [], 'average': 0},
                '5': {'times': [], 'average': 0},
                '0': {'times': [], 'average': 0}
            }
        }
    except Exception as e:
        print(f"Error loading charge cycles: {str(e)}")
        return {
            'charge_cycles': [],
            'discharge_cycles': [],
            'charge_thresholds': {
                '80': {'times': [], 'average': 0},
                '85': {'times': [], 'average': 0},
                '90': {'times': [], 'average': 0},
                '95': {'times': [], 'average': 0},
                '100': {'times': [], 'average': 0}
            },
            'discharge_thresholds': {
                '20': {'times': [], 'average': 0},
                '15': {'times': [], 'average': 0},
                '10': {'times': [], 'average': 0},
                '5': {'times': [], 'average': 0},
                '0': {'times': [], 'average': 0}
            }
        }

def save_charge_cycles(data):
    try:
        with open('charge_cycles.json', 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving charge cycles: {str(e)}")

def update_threshold_data(data, cycle_type, threshold, time_to_threshold):
    try:
        threshold_key = f"{cycle_type}_thresholds"
        threshold_str = str(threshold)
        
        if threshold_str in data[threshold_key]:
            data[threshold_key][threshold_str]['times'].append(time_to_threshold)
            # Keep only last 10 times
            if len(data[threshold_key][threshold_str]['times']) > 10:
                data[threshold_key][threshold_str]['times'] = data[threshold_key][threshold_str]['times'][-10:]
            # Calculate new average
            data[threshold_key][threshold_str]['average'] = sum(data[threshold_key][threshold_str]['times']) / len(data[threshold_key][threshold_str]['times'])
            
            save_charge_cycles(data)
    except Exception as e:
        print(f"Error updating threshold data: {str(e)}")

def analyze_existing_cycles(data):
    """Analyze existing cycles to populate threshold data"""
    try:
        # Analyze charge cycles
        for cycle in data['charge_cycles']:
            start_time = datetime.fromisoformat(cycle['start'])
            end_time = datetime.fromisoformat(cycle['end'])
            start_percent = cycle.get('start_percent', 0)
            end_percent = cycle['percent']
            
            # Calculate time to reach each threshold
            thresholds = [80, 85, 90, 95, 100]
            for threshold in thresholds:
                if start_percent < threshold <= end_percent:
                    # Estimate time to reach this threshold
                    total_duration = cycle['duration']
                    percent_range = end_percent - start_percent
                    if percent_range > 0:
                        threshold_progress = (threshold - start_percent) / percent_range
                        time_to_threshold = total_duration * threshold_progress
                        update_threshold_data(data, 'charge', threshold, time_to_threshold)
        
        # Analyze discharge cycles
        for cycle in data['discharge_cycles']:
            start_time = datetime.fromisoformat(cycle['start'])
            end_time = datetime.fromisoformat(cycle['end'])
            start_percent = cycle.get('start_percent', 100)
            end_percent = cycle['percent']
            
            # Calculate time to reach each threshold
            thresholds = [20, 15, 10, 5, 0]
            for threshold in thresholds:
                if start_percent > threshold >= end_percent:
                    # Estimate time to reach this threshold
                    total_duration = cycle['duration']
                    percent_range = start_percent - end_percent
                    if percent_range > 0:
                        threshold_progress = (start_percent - threshold) / percent_range
                        time_to_threshold = total_duration * threshold_progress
                        update_threshold_data(data, 'discharge', threshold, time_to_threshold)
        
        save_charge_cycles(data)
        print("Existing cycles analyzed and threshold data populated.")
    except Exception as e:
        print(f"Error analyzing existing cycles: {str(e)}")

def update_cycle(data, cycle_type, start_time, end_time, current_percent, start_percent=None):
    try:
        duration = (end_time - start_time).total_seconds() / 60  # Convert to minutes
        
        # Create cycle entry
        cycle_entry = {
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'duration': duration,
            'percent': current_percent
        }
        if start_percent is not None:
            cycle_entry['start_percent'] = start_percent
            cycle_entry['percent_change'] = current_percent - start_percent
            cycle_entry['rate_per_hour'] = (cycle_entry['percent_change'] / duration) * 60  # percent per hour
        
        # Add to appropriate cycle list
        cycle_list = f"{cycle_type}_cycles"
        data[cycle_list].append(cycle_entry)
        
        # Keep only last 10 cycles
        if len(data[cycle_list]) > 10:
            data[cycle_list] = data[cycle_list][-10:]
        
        save_charge_cycles(data)
        return data
    except Exception as e:
        print(f"Error updating {cycle_type} cycle: {str(e)}")
        return None

def main():
    print("Battery Monitor Started...")
    print("Press Ctrl+C to stop monitoring")
    logging = 0
    
    # Load and analyze existing data
    charge_data = load_charge_cycles()
    analyze_existing_cycles(charge_data)

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
    BATTERY_STABLE_THRESHOLD = 3   # ±3% threshold
    battery_stable_state = False
    last_stable_percent = None

    # --- Process usage history tracking ---
    process_history = {}  # Dictionary to store process usage history
    PROCESS_HISTORY_DURATION = 300  # 5 minutes in seconds
    idle_proc_count = 0

    try:
        while True:
            battery_info = get_battery_info()
            top_processes = get_process_power_usage()
            now = time.time()
            
            # Update process history
            for proc in top_processes:
                pid = proc['pid']
                if pid not in process_history:
                    process_history[pid] = {
                        'name': proc['name'],
                        'cpu_history': [],
                        'memory_history': []
                    }
                
                # Add current readings
                process_history[pid]['cpu_history'].append((now, proc['cpu_percent']))
                process_history[pid]['memory_history'].append((now, proc['memory_percent']))
                
                # Clean up old readings
                cutoff_time = now - PROCESS_HISTORY_DURATION
                process_history[pid]['cpu_history'] = [(t, v) for t, v in process_history[pid]['cpu_history'] if t > cutoff_time]
                process_history[pid]['memory_history'] = [(t, v) for t, v in process_history[pid]['memory_history'] if t > cutoff_time]
            
            # Clean up processes that are no longer running
            current_pids = {p['pid'] for p in top_processes}
            process_history = {pid: data for pid, data in process_history.items() if pid in current_pids}
            
            # Track charge/discharge cycles
            current_charge_state = battery_info['power_plugged']
            current_percent = battery_info['percentage']
            
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
                    cycle_type = 'charge' if last_charge_state else 'discharge'
                    update_cycle(load_charge_cycles(), cycle_type, cycle_start_time, datetime.now(), last_percent, cycle_start_percent)
                
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
                thresholds = [80, 85, 90, 95, 100]
                for threshold in thresholds:
                    if (threshold not in reached_charge_thresholds and 
                        current_percent >= threshold and 
                        (last_percent is None or last_percent < threshold)):
                        reached_charge_thresholds.add(threshold)
                        # Calculate time to reach this threshold
                        time_to_threshold = (datetime.now() - cycle_start_time).total_seconds() / 60
                        update_threshold_data(load_charge_cycles(), 'charge', threshold, time_to_threshold)
                        print(f"\nReached {threshold}% charge in {time_to_threshold:.1f} minutes")
            
            # Track discharging progress
            else:
                thresholds = [20, 15, 10, 5, 0]
                for threshold in thresholds:
                    if (threshold not in reached_discharge_thresholds and 
                        current_percent <= threshold and 
                        (last_percent is None or last_percent > threshold)):
                        reached_discharge_thresholds.add(threshold)
                        # Calculate time to reach this threshold
                        time_to_threshold = (datetime.now() - cycle_start_time).total_seconds() / 60
                        update_threshold_data(load_charge_cycles(), 'discharge', threshold, time_to_threshold)
                        print(f"\nReached {threshold}% discharge in {time_to_threshold:.1f} minutes")
            
            last_charge_state = current_charge_state
            last_percent = current_percent

            # Get system memory usage
            memory_usage = psutil.virtual_memory().percent
            
            # Check if memory cleanup is needed
            current_time = time.time()
            if memory_usage > MEMORY_THRESHOLD and (current_time - last_cleanup_time) > CLEANUP_COOLDOWN:
                print("\n=== High Memory Usage Detected ===")
                print(f"Memory Usage: {memory_usage}%")
                print("Initiating memory cleanup...")
                
                if cleanup_memory():
                    print("Memory cleanup completed successfully")
                    last_cleanup_time = current_time
                else:
                    print("Memory cleanup failed")
            
            # Clear screen for better visibility
            os.system('cls' if os.name == 'nt' else 'clear')
            current_time = datetime.now()
            print(f"\nCurrent Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("\n=== Battery Status ===")
            print(f"Battery Percentage: {battery_info['percentage']}%")
            print(f"Power Status: {'Plugged' if battery_info['power_plugged'] else 'Unplugged'}")
            
            # Display cycle information
            charge_data = load_charge_cycles()
            
            # Display charging information
            if battery_info['power_plugged']:
                if battery_info['percentage'] < 100:
                    try:
                        current_percent = battery_info['percentage']
                        remaining_percent = 100 - current_percent
                        
                        # Initialize first state if not set
                        if first_state_change_time is None or first_state_percent is None:
                            first_state_change_time = current_time
                            first_state_percent = current_percent
                        
                        # Calculate estimated time based on historical data
                        if charge_data['charge_cycles']:
                            avg_rate = sum(cycle['rate_per_hour'] for cycle in charge_data['charge_cycles']) / len(charge_data['charge_cycles'])
                            estimated_charge_time = (remaining_percent / avg_rate) * 60 if avg_rate > 0 else remaining_percent
                            print(f"Average Charge Rate: {avg_rate:.1f}%/hour")
                        else:
                            # Calculate rate based on current charging session
                            time_diff = (current_time - first_state_change_time).total_seconds() / 60  # in minutes
                            if time_diff > 0:
                                percent_diff = current_percent - first_state_percent
                                current_rate = (percent_diff / time_diff) * 60  # convert to per hour
                                if current_rate > 0:
                                    estimated_charge_time = (remaining_percent / current_rate) * 60
                                    print(f"Current Charge Rate: {current_rate:.1f}%/hour")
                                else:
                                    estimated_charge_time = remaining_percent
                                    print("Calculating charge rate...")
                            else:
                                estimated_charge_time = remaining_percent
                                print("Calculating charge rate...")
                        
                        charge_end_time = current_time + timedelta(minutes=estimated_charge_time)
                        if current_percent == last_percent and (datetime.now() - last_percent_change_time).total_seconds() >= 90:
                            print("Charging paused or possible full charge")
                        else:
                            # Format time display based on duration
                            if estimated_charge_time >= 60:
                                hours = int(estimated_charge_time // 60)
                                minutes = int(estimated_charge_time % 60)
                                time_str = f"{hours}h {minutes}m"
                            else:
                                time_str = f"{estimated_charge_time:.1f} minutes"
                            
                            print(f"Time to Full Charge: {time_str} (Until {charge_end_time.strftime('%I:%M %p')})")
                            
                            # Show system's estimated time to full charge
                            if battery_info['time_left'] == 'Charging':
                                print("System Status: Currently Charging")
                            else:
                                print(f"System Estimated Time to Full: {battery_info['time_left']}")
                            
                            # Show estimated times to reach different thresholds
                            print("\nEstimated Times to Thresholds:")
                            thresholds = [80, 85, 90, 95, 100]
                            for threshold in thresholds:
                                if threshold > current_percent:
                                    remaining_to_threshold = threshold - current_percent
                                    if 'current_rate' in locals() and current_rate > 0:
                                        time_to_threshold = (remaining_to_threshold / current_rate) * 60
                                        if time_to_threshold >= 60:
                                            hours = int(time_to_threshold // 60)
                                            minutes = int(time_to_threshold % 60)
                                            time_str = f"{hours}h {minutes}m"
                                        else:
                                            time_str = f"{time_to_threshold:.1f} minutes"
                                        threshold_time = current_time + timedelta(minutes=time_to_threshold)
                                        print(f"  {threshold}%: {time_str} (Until {threshold_time.strftime('%I:%M %p')})")
                    except Exception as e:
                        print(f"Unable to calculate charging time: {str(e)}")
                else:
                    print("Battery fully charged")
            else:
                if battery_info['time_left'] != 'N/A':
                    try:
                        if 'h' in battery_info['time_left'] or 'm' in battery_info['time_left']:
                            hours = 0
                            minutes = 0
                            parts = battery_info['time_left'].split()
                            for part in parts:
                                if 'h' in part:
                                    hours = int(part.replace('h', ''))
                                elif 'm' in part:
                                    minutes = int(part.replace('m', ''))
                            time_left_minutes = hours * 60 + minutes
                        else:
                            hours, minutes = map(int, battery_info['time_left'].split(':'))
                            time_left_minutes = hours * 60 + minutes
                        
                        # Calculate estimated time based on historical data
                        if charge_data['discharge_cycles']:
                            avg_rate = sum(cycle['rate_per_hour'] for cycle in charge_data['discharge_cycles']) / len(charge_data['discharge_cycles'])
                            if avg_rate < 0:  # Discharge rate is negative
                                estimated_time = (current_percent / abs(avg_rate)) * 60
                                time_left_minutes = min(time_left_minutes, estimated_time)
                        
                        estimated_end_time = current_time + timedelta(minutes=time_left_minutes)
                        print(f"Time Left: {battery_info['time_left']} (Until {estimated_end_time.strftime('%I:%M %p')})")
                        
                        # --- Show current discharge rate ---
                        time_diff = (current_time - last_percent_change_time).total_seconds() / 60  # in minutes
                        percent_diff = last_percent - current_percent  # should be positive if discharging
                        if time_diff > 0 and percent_diff > 0:
                            current_discharge_rate = (percent_diff / time_diff) * 60  # % per hour
                            print(f"Current Discharge Rate: {current_discharge_rate:.2f}%/hour")
                        else:
                            print("Calculating discharge rate...")
                    except ValueError:
                        print(f"Time Left: {battery_info['time_left']} (Unable to parse time format)")
                else:
                    print(f"Time Left: {battery_info['time_left']}")
                    # --- Show current discharge rate even if time left is N/A ---
                    time_diff = (current_time - last_percent_change_time).total_seconds() / 60  # in minutes
                    percent_diff = last_percent - current_percent  # should be positive if discharging
                    if time_diff > 0 and percent_diff > 0:
                        current_discharge_rate = (percent_diff / time_diff) * 60  # % per hour
                        print(f"Current Discharge Rate: {current_discharge_rate:.2f}%/hour")
                    else:
                        print("Calculating discharge rate...")
            
            # Display average cycle durations
            charge_thresholds_with_data = [t for t in charge_data['charge_thresholds'] if charge_data['charge_thresholds'][t]['times']]
            if charge_thresholds_with_data:
                print("\nAverage Charging Times:")
                for threshold in ['80', '85', '90', '95', '100']:
                    if threshold in charge_data['charge_thresholds'] and charge_data['charge_thresholds'][threshold]['times']:
                        avg_time = charge_data['charge_thresholds'][threshold]['average']
                        count = len(charge_data['charge_thresholds'][threshold]['times'])
                        print(f"  To {threshold}%: {avg_time:.1f} minutes ({count} samples)")
            
            # Display average discharge times
            discharge_thresholds_with_data = [t for t in charge_data['discharge_thresholds'] if charge_data['discharge_thresholds'][t]['times']]
            if discharge_thresholds_with_data:
                print("\nAverage Discharge Times:")
                for threshold in ['20', '15', '10', '5', '0']:
                    if threshold in charge_data['discharge_thresholds'] and charge_data['discharge_thresholds'][threshold]['times']:
                        avg_time = charge_data['discharge_thresholds'][threshold]['average']
                        count = len(charge_data['discharge_thresholds'][threshold]['times'])
                        print(f"  To {threshold}%: {avg_time:.1f} minutes ({count} samples)")
            # Display recent cycle information
            if charge_data['charge_cycles'] or charge_data['discharge_cycles']:
                print("\nRecent Battery Cycles:")
                for cycle_type in ['charge', 'discharge']:
                    cycles = charge_data[f'{cycle_type}_cycles']
                    if cycles:
                        latest = cycles[-1]
                        print(f"\nLast {cycle_type.title()} Cycle:")
                        print(f"  Start: {datetime.fromisoformat(latest['start']).strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  End: {datetime.fromisoformat(latest['end']).strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  Duration: {latest['duration']:.1f} minutes")
                        if 'start_percent' in latest:
                            print(f"  Percentage Change: {latest['percent_change']}%")
                            print(f"  Rate: {latest['rate_per_hour']:.1f}%/hour")
                            # Show estimated time to full charge or full discharge, depending on cycle type and rate direction
                            rate = latest.get('rate_per_hour')
                            if rate and rate != 0:
                                if cycle_type == 'charge' and rate > 0:
                                    time_to_full = 100 / rate * 60  # in minutes
                                    if time_to_full > 60:
                                        hours = int(time_to_full // 60)
                                        minutes = int(time_to_full % 60)
                                        print(f"  Estimated time to full charge: {hours} hours {minutes} minutes")
                                    else:
                                        print(f"  Estimated time to full charge: {time_to_full:.1f} minutes")
                                elif cycle_type == 'discharge' and rate < 0:
                                    time_to_empty = 100 / abs(rate) * 60  # in minutes
                                    if time_to_empty > 60:
                                        hours = int(time_to_empty // 60)
                                        minutes = int(time_to_empty % 60)
                                        print(f"  Estimated time to full discharge: {hours} hours {minutes} minutes")
                                    else:
                                        print(f"  Estimated time to full discharge: {time_to_empty:.1f} minutes")
                                else:
                                    print("  Estimated time to next charge/discharge: N/A")
                            else:
                                print("  Estimated time to next charge/discharge: N/A")

            # Display average cycle durations
            charge_thresholds_with_data = [t for t in charge_data['charge_thresholds'] if charge_data['charge_thresholds'][t]['times']]
            if charge_thresholds_with_data:
                print("\nAverage Charging Times:")
                for threshold in ['80', '85', '90', '95', '100']:
                    if threshold in charge_data['charge_thresholds'] and charge_data['charge_thresholds'][threshold]['times']:
                        avg_time = charge_data['charge_thresholds'][threshold]['average']
            print("\n=== Top Power-Consuming Processes ===")
            if top_processes:
                active_processes = [p for p in top_processes if p['name'] != 'System Idle Process']
                
                print("Top 5 CPU/Memory-Intensive Processes:")
                # Get top 5 by CPU and top 5 by Memory, then combine and deduplicate while preserving order
                top_cpu = sorted(active_processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
                top_mem = sorted(active_processes, key=lambda x: x['memory_percent'], reverse=True)[:5]
                seen = set()
                combined = []
                for proc in top_cpu + top_mem:
                    key = proc['name']
                    if key not in seen:
                        combined.append(proc)
                        seen.add(key)
                for proc in combined:
                    print(f"  {proc['name']}: CPU {proc['cpu_percent']:.1f}%, Memory {proc['memory_percent']:.1f}%")
                # Print System Idle Process separately at the end with average usage
                idle_processes = [p for p in top_processes if p['name'] == 'System Idle Process']
                idle_proc_count += 1
                if idle_processes:
                    avg_cpu_sys_proc = sum(p['cpu_percent'] for p in idle_processes) / idle_proc_count
                    avg_memory_sys_proc = sum(p['memory_percent'] for p in idle_processes) / idle_proc_count
                    current_proc = idle_processes[0]
                    print(f"\nSystem Idle: CPU {current_proc['cpu_percent']:.1f}% (Avg: {avg_cpu_sys_proc:.1f}%), Memory {current_proc['memory_percent']:.1f}% (Avg: {avg_memory_sys_proc:.1f}%)")
            else:
                print("No processes found")

            # Print system resource usage with better formatting
            print("\n=== System Resource Usage (Average) ===")
            # Maintain running totals and counts for averages
            if 'cpu_usage_total' not in locals():
                cpu_usage_total = 0.0
                memory_usage_total = 0.0
                disk_usage_total = 0.0
                usage_count = 0

            current_cpu = psutil.cpu_percent()
            current_mem = psutil.virtual_memory().percent
            current_disk = psutil.disk_usage('/').percent

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
                save_battery_log(battery_info, top_processes, process_history)
            
            time.sleep(2)  # Update every 2 seconds
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    main() 