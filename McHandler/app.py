#!/usr/bin/env python3
"""
Minecraft Mod Handler Web Application - Flask-based web interface
"""

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
import json
import threading
from werkzeug.utils import secure_filename
from pathlib import Path
import tempfile
import shutil
import zipfile
from datetime import datetime

from mod_manager import ModManager
from crash_analyzer import CrashLogAnalyzer
from compatibility_checker import CompatibilityChecker

app = Flask(__name__)
app.secret_key = 'minecraft_mod_handler_secret_key_2024'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'log', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize managers
mod_manager = ModManager()
crash_analyzer = CrashLogAnalyzer()
compatibility_checker = CompatibilityChecker(mod_manager)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/mods')
def mods():
    """Mod management page"""
    return render_template('mods.html')

@app.route('/shaders')
def shaders():
    """Shaderpack management page"""
    return render_template('shaders.html')

@app.route('/api/mods/load', methods=['POST'])
def load_mods():
    """Load mods from specified directory"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir:
            return jsonify({
                'error': 'No Minecraft directory provided',
                'suggestion': 'Please enter a Minecraft directory path. For ATLauncher, use the instance directory (e.g., C:\\Users\\...\\ATLauncher\\instances\\YourInstance). For standard Minecraft, use the .minecraft directory.'
            }), 400
        
        if not os.path.exists(minecraft_dir):
            return jsonify({
                'error': f'Directory does not exist: {minecraft_dir}',
                'suggestion': 'Please check the path and try again. Make sure the directory exists.'
            }), 400
        
        mod_manager.set_minecraft_directory(minecraft_dir)
        mods = mod_manager.get_installed_mods()
        
        # Get the actual mods directory path that was checked
        mods_dir_path = str(mod_manager.mods_dir) if mod_manager.mods_dir else None
        
        # Convert datetime objects to strings for JSON serialization
        for mod in mods:
            if 'modified' in mod:
                mod['modified'] = mod['modified'].isoformat()
        
        # Provide helpful information when 0 mods are found
        response_data = {
            'mods': mods,
            'mods_directory': mods_dir_path,
            'mods_directory_exists': os.path.exists(mods_dir_path) if mods_dir_path else False
        }
        
        if len(mods) == 0:
            # Check if mods directory exists
            if mods_dir_path and os.path.exists(mods_dir_path):
                # Directory exists but is empty
                response_data['warning'] = f'No mods found in: {mods_dir_path}'
                response_data['suggestion'] = 'The mods directory exists but is empty. Make sure you have .jar mod files in this directory.'
            elif mods_dir_path:
                # Directory doesn't exist
                response_data['warning'] = f'Mods directory does not exist: {mods_dir_path}'
                response_data['suggestion'] = f'The mods directory was not found. If you selected the mods folder directly, that should work. If you selected an instance directory, make sure it contains a "mods" subdirectory.'
            else:
                response_data['warning'] = 'Could not determine mods directory'
                response_data['suggestion'] = 'Please check that the directory path is correct.'
        
        return jsonify(response_data)
    except Exception as e:
        return jsonify({
            'error': str(e),
            'suggestion': 'An error occurred while loading mods. Please check the directory path and try again.'
        }), 500

@app.route('/api/mods/backup', methods=['POST'])
def backup_mods():
    """Create backup of mods"""
    try:
        backup_path = mod_manager.backup_mods()
        if backup_path:
            return jsonify({'success': True, 'backup_path': backup_path})
        else:
            return jsonify({'error': 'Failed to create backup'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mods/toggle', methods=['POST'])
def toggle_mod():
    """Enable/disable a mod"""
    try:
        data = request.get_json()
        mod_name = data.get('mod_name')
        action = data.get('action')  # 'enable' or 'disable'
        
        if action == 'disable':
            mod_manager.disable_mod(mod_name)
        elif action == 'enable':
            mod_manager.enable_mod(mod_name)
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/crash-analysis')
def crash_analysis():
    """Crash log analysis page"""
    return render_template('crash_analysis.html')

@app.route('/api/crash/analyze', methods=['POST'])
def analyze_crash():
    """Analyze uploaded crash log"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Save uploaded file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Read file content
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()
            
            # Analyze with AI
            result = crash_analyzer.analyze_crash_log(log_content)
            
            # Clean up uploaded file
            os.remove(filepath)
            
            return jsonify(result)
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crash/analyze_directory', methods=['POST'])
def analyze_crash_directory():
    """Analyze crash logs from a Minecraft directory"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        # Find crash-reports directory
        crash_reports_dir = os.path.join(minecraft_dir, 'crash-reports')
        
        if not os.path.exists(crash_reports_dir) or not os.path.isdir(crash_reports_dir):
            return jsonify({
                'success': False,
                'error': 'No crash-reports directory found',
                'message': 'No crash reports found in the specified directory'
            }), 200  # Return 200 but with success: false to indicate no crashes
        
        # Get all crash log files
        crash_files = []
        try:
            for filename in os.listdir(crash_reports_dir):
                if filename.endswith(('.txt', '.log')):
                    crash_files.append(os.path.join(crash_reports_dir, filename))
        except PermissionError:
            return jsonify({'error': 'Permission denied to access crash-reports directory'}), 403
        
        if not crash_files:
            return jsonify({
                'success': False,
                'error': 'No crash logs found',
                'message': 'No crash reports found in the specified directory'
            }), 200  # Return 200 but with success: false to indicate no crashes
        
        # Sort by modification time (newest first) and get the most recent
        crash_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        latest_crash_file = crash_files[0]
        
        # Read the latest crash log
        try:
            with open(latest_crash_file, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()
        except Exception as e:
            return jsonify({'error': f'Failed to read crash log: {str(e)}'}), 500
        
        # Check if Ollama is available
        if not crash_analyzer.check_ollama_connection():
            return jsonify({'error': 'Ollama is not running. Please start Ollama to use AI features.'}), 503
        
        # Analyze with AI
        result = crash_analyzer.analyze_crash_log(log_content)
        
        if 'error' in result:
            return jsonify(result), 500
        
        # Add success flag and additional info
        result['success'] = True
        result['crash_file'] = os.path.basename(latest_crash_file)
        result['total_crashes'] = len(crash_files)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/compatibility')
def compatibility():
    """Compatibility check page"""
    return render_template('compatibility.html')

@app.route('/api/compatibility/check', methods=['POST'])
def check_compatibility():
    """Check mod compatibility"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        mod_manager.set_minecraft_directory(minecraft_dir)
        issues = compatibility_checker.check_mod_compatibility()
        report = compatibility_checker.get_compatibility_report()
        
        return jsonify({
            'issues': issues,
            'report': report
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ollama/status')
def ollama_status():
    """Check Ollama connection status"""
    try:
        is_connected = crash_analyzer.check_ollama_connection()
        models = crash_analyzer.get_available_models() if is_connected else []
        
        return jsonify({
            'connected': is_connected,
            'models': models
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ollama/suggest', methods=['POST'])
def get_mod_suggestions():
    """Get AI suggestions for mod issues"""
    try:
        data = request.get_json()
        mod_name = data.get('mod_name')
        error_description = data.get('error_description')
        
        if not mod_name or not error_description:
            return jsonify({'error': 'Missing mod name or error description'}), 400
        
        result = crash_analyzer.suggest_mod_fixes(mod_name, error_description)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/atlauncher/instances')
def get_atlauncher_instances():
    """Get list of ATLauncher instances"""
    try:
        atlauncher_path = Path.home() / "AppData" / "Roaming" / "ATLauncher" / "instances"
        instances = []
        
        if atlauncher_path.exists():
            for instance_dir in atlauncher_path.iterdir():
                if instance_dir.is_dir():
                    mods_dir = instance_dir / "mods"
                    if mods_dir.exists():
                        instances.append({
                            'name': instance_dir.name,
                            'path': str(instance_dir),
                            'mod_count': len(list(mods_dir.glob("*.jar")))
                        })
        
        return jsonify({'instances': instances})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mods/upload', methods=['POST'])
def upload_mods():
    """Upload mod files to the mods directory"""
    try:
        minecraft_dir = request.form.get('minecraft_dir')
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        mods_dir = Path(minecraft_dir) / "mods"
        mods_dir.mkdir(exist_ok=True)
        
        uploaded_files = request.files.getlist('mod_files')
        uploaded_count = 0
        
        for file in uploaded_files:
            if file and file.filename.lower().endswith('.jar'):
                # Secure the filename
                filename = secure_filename(file.filename)
                if filename:
                    file_path = mods_dir / filename
                    file.save(str(file_path))
                    uploaded_count += 1
        
        return jsonify({
            'success': True,
            'uploaded_count': uploaded_count,
            'message': f'Successfully uploaded {uploaded_count} mod(s)'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mods/remove', methods=['POST'])
def remove_mods():
    """Remove mod files from the mods directory"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        mod_names = data.get('mod_names', [])
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        mods_dir = Path(minecraft_dir) / "mods"
        removed_count = 0
        
        for mod_name in mod_names:
            mod_path = mods_dir / mod_name
            if mod_path.exists():
                try:
                    mod_path.unlink()
                    removed_count += 1
                except Exception as e:
                    print(f"Error removing {mod_name}: {e}")
        
        return jsonify({
            'success': True,
            'removed_count': removed_count,
            'message': f'Successfully removed {removed_count} mod(s)'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/open_mod_folder', methods=['POST'])
def open_mod_folder():
    """Open the mods folder in the user's file explorer"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        mods_dir = Path(minecraft_dir) / "mods"
        
        # Create mods directory if it doesn't exist
        mods_dir.mkdir(exist_ok=True)
        
        # Try to open the folder in the file explorer
        import platform
        import subprocess
        
        system = platform.system()
        
        try:
            if system == "Windows":
                subprocess.run(['explorer', str(mods_dir)], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(['open', str(mods_dir)], check=True)
            elif system == "Linux":
                subprocess.run(['xdg-open', str(mods_dir)], check=True)
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported operating system: {system}'
                })
            
            return jsonify({
                'success': True,
                'message': 'Opened mods folder in file explorer'
            })
            
        except subprocess.CalledProcessError as e:
            return jsonify({
                'success': False,
                'error': f'Failed to open file explorer: {str(e)}'
            })
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'error': 'File explorer command not found'
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shaderpacks/upload', methods=['POST'])
def upload_shaderpack():
    """Upload mod files to the mods directory"""
    try:
        minecraft_dir = request.form.get('minecraft_dir')
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        mods_dir = Path(minecraft_dir) / "shaderpacks"
        mods_dir.mkdir(exist_ok=True)
        
        uploaded_files = request.files.getlist('shaderpack_files')
        uploaded_count = 0
        
        for file in uploaded_files:
            if file and file.filename.lower().endswith('.zip'):
                # Secure the filename
                filename = secure_filename(file.filename)
                if filename:
                    file_path = mods_dir / filename
                    file.save(str(file_path))
                    uploaded_count += 1
        
        return jsonify({
            'success': True,
            'uploaded_count': uploaded_count,
            'message': f'Successfully uploaded {uploaded_count} shaderpack(s)'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shaderpacks/remove', methods=['POST'])
def remove_shaderpacks():
    """Remove mod files from the mods directory"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        mod_names = data.get('shaderpack_names', [])
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        mods_dir = Path(minecraft_dir) / "shaderpacks"
        removed_count = 0
        
        for mod_name in mod_names:
            mod_path = mods_dir / mod_name
            if mod_path.exists():
                try:
                    mod_path.unlink()
                    removed_count += 1
                except Exception as e:
                    print(f"Error removing {mod_name}: {e}")
        
        return jsonify({
            'success': True,
            'removed_count': removed_count,
            'message': f'Successfully removed {removed_count} shaderpack(s)'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/open_shaderpack_folder', methods=['POST'])
def open_shaderpack_folder():
    """Open the mods folder in the user's file explorer"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        shaderpacks_dir = Path(minecraft_dir) / "shaderpacks"
        
        # Create mods directory if it doesn't exist
        shaderpacks_dir.mkdir(exist_ok=True)
        
        # Try to open the folder in the file explorer
        import platform
        import subprocess
        
        system = platform.system()
        
        try:
            if system == "Windows":
                subprocess.run(['explorer', str(shaderpacks_dir)], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(['open', str(shaderpacks_dir)], check=True)
            elif system == "Linux":
                subprocess.run(['xdg-open', str(shaderpacks_dir)], check=True)
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported operating system: {system}'
                })
            
            return jsonify({
                'success': True,
                'message': 'Opened shaderpacks folder in file explorer'
            })
            
        except subprocess.CalledProcessError as e:
            return jsonify({
                'success': False,
                'error': f'Failed to open shaderpacks folder in file explorer: {str(e)}'
            })
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'error': 'File explorer command not found for shaderpacks folder'
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shaderpacks/load', methods=['POST'])
def load_shaderpacks():
    """Load shaderpacks from specified directory"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        shaderpacks_dir = Path(minecraft_dir) / "shaderpacks"
        
        if not shaderpacks_dir.exists():
            return jsonify({'shaderpacks': []})
        
        shaderpacks = []
        for shaderpack_file in shaderpacks_dir.glob("*.zip"):
            shaderpack_info = {
                'name': shaderpack_file.name,
                'display_name': shaderpack_file.stem,  # Name without extension
                'path': str(shaderpack_file),
                'size': shaderpack_file.stat().st_size,
                'modified': datetime.fromtimestamp(shaderpack_file.stat().st_mtime).isoformat(),
                'enabled': True,  # Shaderpacks are typically enabled by default
                'version': 'Unknown',
                'author': 'Unknown',
                'description': ''
            }
            
            # Try to extract shaderpack info from zip file
            try:
                with zipfile.ZipFile(shaderpack_file, 'r') as zip_ref:
                    # Look for shaderpack info files
                    for file_info in zip_ref.filelist:
                        if file_info.filename.endswith('shaderpack.properties'):
                            try:
                                properties_content = zip_ref.read(file_info).decode('utf-8')
                                # Parse properties file (simple key=value format)
                                for line in properties_content.split('\n'):
                                    if '=' in line and not line.strip().startswith('#'):
                                        key, value = line.split('=', 1)
                                        key = key.strip()
                                        value = value.strip()
                                        if key == 'name':
                                            shaderpack_info['display_name'] = value
                                        elif key == 'version':
                                            shaderpack_info['version'] = value
                                        elif key == 'author':
                                            shaderpack_info['author'] = value
                                        elif key == 'description':
                                            shaderpack_info['description'] = value
                            except:
                                pass  # If we can't parse, use defaults
                            break
            except:
                pass  # If we can't read the zip, use defaults
            
            shaderpacks.append(shaderpack_info)
        
        return jsonify({'shaderpacks': shaderpacks})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shaderpacks/toggle', methods=['POST'])
def toggle_shaderpack():
    """Enable/disable a shaderpack"""
    try:
        data = request.get_json()
        shaderpack_name = data.get('shaderpack_name')
        action = data.get('action')  # 'enable' or 'disable'
        
        if not shaderpack_name or not action:
            return jsonify({'error': 'Missing shaderpack_name or action'}), 400
        
        # For shaderpacks, we'll implement a simple enable/disable by renaming
        # Disabled shaderpacks get a .disabled extension
        minecraft_dir = data.get('minecraft_dir')
        if not minecraft_dir:
            return jsonify({'error': 'Minecraft directory not provided'}), 400
        
        shaderpacks_dir = Path(minecraft_dir) / "shaderpacks"
        shaderpack_path = shaderpacks_dir / shaderpack_name
        
        if not shaderpack_path.exists():
            return jsonify({'error': 'Shaderpack not found'}), 404
        
        if action == 'disable':
            # Rename to .disabled
            if not shaderpack_name.endswith('.disabled'):
                new_path = shaderpack_path.with_suffix('.zip.disabled')
                shaderpack_path.rename(new_path)
        elif action == 'enable':
            # Remove .disabled extension
            if shaderpack_name.endswith('.disabled'):
                new_path = shaderpack_path.with_suffix('')
                shaderpack_path.rename(new_path)
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shaderpacks/backup', methods=['POST'])
def backup_shaderpacks():
    """Create backup of shaderpacks"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        shaderpacks_dir = Path(minecraft_dir) / "shaderpacks"
        backup_dir = Path(minecraft_dir) / "shaderpack_backups"
        backup_dir.mkdir(exist_ok=True)
        
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"shaderpacks_backup_{timestamp}.zip"
        
        if shaderpacks_dir.exists():
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for shaderpack_file in shaderpacks_dir.glob("*.zip"):
                    zipf.write(shaderpack_file, shaderpack_file.name)
        
        return jsonify({
            'success': True, 
            'backup_path': str(backup_path)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/select_directory', methods=['POST'])
def select_directory():
    """Get a list of common directories for selection"""
    try:
        import platform
        system = platform.system()
        
        common_dirs = []
        
        if system == "Windows":
            # Windows common directories
            user_profile = os.path.expanduser("~")
            common_dirs = [
                {"name": "Desktop", "path": os.path.join(user_profile, "Desktop")},
                {"name": "Documents", "path": os.path.join(user_profile, "Documents")},
                {"name": "Downloads", "path": os.path.join(user_profile, "Downloads")},
                {"name": "AppData/Roaming", "path": os.path.join(user_profile, "AppData", "Roaming")},
                {"name": "ATLauncher Instances", "path": os.path.join(user_profile, "AppData", "Roaming", "ATLauncher", "instances")},
                {"name": "Minecraft", "path": os.path.join(user_profile, "AppData", "Roaming", ".minecraft")},
            ]
        elif system == "Darwin":  # macOS
            user_home = os.path.expanduser("~")
            common_dirs = [
                {"name": "Desktop", "path": os.path.join(user_home, "Desktop")},
                {"name": "Documents", "path": os.path.join(user_home, "Documents")},
                {"name": "Downloads", "path": os.path.join(user_home, "Downloads")},
                {"name": "Library/Application Support", "path": os.path.join(user_home, "Library", "Application Support")},
                {"name": "Minecraft", "path": os.path.join(user_home, "Library", "Application Support", "minecraft")},
            ]
        else:  # Linux
            user_home = os.path.expanduser("~")
            common_dirs = [
                {"name": "Desktop", "path": os.path.join(user_home, "Desktop")},
                {"name": "Documents", "path": os.path.join(user_home, "Documents")},
                {"name": "Downloads", "path": os.path.join(user_home, "Downloads")},
                {"name": ".local/share", "path": os.path.join(user_home, ".local", "share")},
                {"name": ".minecraft", "path": os.path.join(user_home, ".minecraft")},
            ]
        
        # Filter to only existing directories
        existing_dirs = []
        for dir_info in common_dirs:
            if os.path.exists(dir_info["path"]) and os.path.isdir(dir_info["path"]):
                existing_dirs.append(dir_info)
        
        return jsonify({
            'success': True,
            'directories': existing_dirs,
            'system': system
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/browse_directory', methods=['POST'])
def browse_directory():
    """Browse contents of a directory"""
    try:
        data = request.get_json()
        directory_path = data.get('path', '')
        
        if not directory_path or not os.path.exists(directory_path):
            return jsonify({'error': 'Invalid directory path'}), 400
        
        if not os.path.isdir(directory_path):
            return jsonify({'error': 'Path is not a directory'}), 400
        
        # Get directory contents
        items = []
        try:
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)
                if os.path.isdir(item_path):
                    items.append({
                        'name': item,
                        'path': item_path,
                        'type': 'directory',
                        'size': None
                    })
                else:
                    size = os.path.getsize(item_path)
                    items.append({
                        'name': item,
                        'path': item_path,
                        'type': 'file',
                        'size': size
                    })
        except PermissionError:
            return jsonify({'error': 'Permission denied to access directory'}), 403
        
        # Sort directories first, then files
        items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        
        return jsonify({
            'success': True,
            'path': directory_path,
            'items': items,
            'parent': os.path.dirname(directory_path) if directory_path != os.path.dirname(directory_path) else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mods/analyze', methods=['POST'])
def analyze_mods():
    """Get AI analysis and summary of mods"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        mod_manager.set_minecraft_directory(minecraft_dir)
        mods = mod_manager.get_installed_mods()
        
        if not mods:
            return jsonify({'error': 'No mods found in the specified directory'}), 400
        
        # Check if Ollama is available
        if not crash_analyzer.check_ollama_connection():
            return jsonify({'error': 'Ollama is not running. Please start Ollama to use AI features.'}), 503
        
        # Prepare mod data for AI analysis
        mod_data = []
        for mod in mods:
            mod_info = {
                'name': mod.get('display_name', mod.get('name', 'Unknown')),
                'version': mod.get('version', 'Unknown'),
                'author': mod.get('author', 'Unknown'),
                'description': mod.get('description', ''),
                'size_mb': round((mod.get('size', 0) / (1024 * 1024)), 2),
                'enabled': mod.get('enabled', True)
            }
            mod_data.append(mod_info)
        
        print(f"DEBUG: Processing {len(mod_data)} mods for AI analysis")
        print(f"DEBUG: Sample mod data: {mod_data[:3] if mod_data else 'No mods'}")
        
        # Create AI prompt for mod analysis
        prompt = f"""
        You are analyzing a Minecraft player's mod collection. Based on the mods below, create a detailed player profile that reveals their playstyle, interests, and modding preferences.

        Mod Collection ({len(mod_data)} mods):
        {json.dumps(mod_data, indent=2)}

        Please provide a comprehensive analysis in this format:

        ## 🎮 Player Profile Analysis

        ### 🎯 Player Archetype
        [Identify the primary player type: Builder, Explorer, Tech Enthusiast, Combat Focused, Aesthetic Player, etc.]

        ### 🎨 Playstyle Description
        [Describe how this player likely approaches Minecraft based on their mod choices]

        ### 📊 Modding Level Assessment
        [Beginner/Intermediate/Advanced - based on mod complexity and quantity]

        ### 🔍 Key Interests & Focus Areas
        [List 3-5 main areas of interest based on mod categories]

        ### ⚡ Performance & Compatibility Notes
        [Any potential performance impacts or compatibility concerns]

        ### 🎯 Recommendations
        [Suggest 2-3 mods that might complement this collection or areas to explore]

        ### 📈 Collection Statistics
        - **Total Mods:** {len(mod_data)}
        - **Total Size:** {sum(mod.get('size_mb', 0) for mod in mod_data):.1f} MB
        - **Enabled Mods:** {sum(1 for mod in mod_data if mod.get('enabled', True))}
        - **Disabled Mods:** {sum(1 for mod in mod_data if not mod.get('enabled', True))}

        Be specific and insightful - avoid generic descriptions. Focus on what makes this player's collection unique.
        """
        
        # Get AI analysis
        result = crash_analyzer.analyze_with_ai(prompt)
        print(f"DEBUG: AI analysis result: {result}")
        
        return jsonify({
            'success': True,
            'analysis': result.get('analysis', 'Analysis failed'),
            'model_used': result.get('model_used', 'Unknown'),
            'timestamp': result.get('timestamp', ''),
            'mod_count': len(mods),
            'total_size_mb': sum(mod.get('size', 0) for mod in mods) / (1024 * 1024)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mods/categorize', methods=['POST'])
def categorize_mods():
    """Get AI categorization of mods by purpose"""
    try:
        data = request.get_json()
        minecraft_dir = data.get('minecraft_dir')
        
        if not minecraft_dir or not os.path.exists(minecraft_dir):
            return jsonify({'error': 'Invalid Minecraft directory'}), 400
        
        mod_manager.set_minecraft_directory(minecraft_dir)
        mods = mod_manager.get_installed_mods()
        
        if not mods:
            return jsonify({'error': 'No mods found in the specified directory'}), 400
        
        # Check if Ollama is available
        if not crash_analyzer.check_ollama_connection():
            return jsonify({'error': 'Ollama is not running. Please start Ollama to use AI features.'}), 503
        
        # Prepare mod data for AI categorization
        mod_data = []
        for mod in mods:
            # Clean up the mod name for better AI recognition
            raw_name = mod.get('display_name', mod.get('name', 'Unknown'))
            # Remove version numbers and file extensions for cleaner names
            clean_name = raw_name.replace('.jar', '').replace('-forge', '').replace('-neoforge', '')
            # Remove version patterns like -1.20.1, -1.20, etc.
            import re
            clean_name = re.sub(r'[-_]\d+\.\d+.*$', '', clean_name)
            # Replace underscores and hyphens with spaces
            clean_name = clean_name.replace('_', ' ').replace('-', ' ')
            # Clean up multiple spaces
            clean_name = ' '.join(clean_name.split())
            
            mod_info = {
                'name': clean_name,
                'original_name': raw_name,  # Keep original for reference
                'version': mod.get('version', 'Unknown'),
                'author': mod.get('author', 'Unknown'),
                'description': mod.get('description', ''),
                'size_mb': round((mod.get('size', 0) / (1024 * 1024)), 2),
                'enabled': mod.get('enabled', True)
            }
            mod_data.append(mod_info)
        
        # Create AI prompt for mod categorization
        prompt = f"""
        IMPORTANT: You must respond with ONLY a valid JSON object. Do not include any other text, explanations, or formatting.

        Categorize each of the following Minecraft mods by their primary purpose. For each mod, assign it to ONE of these EXACT categories:

        - Quality of Life (QOL)
        - Building & Construction  
        - Graphics & Visual
        - Performance & Optimization
        - Adventure & Exploration
        - Combat & Weapons
        - Magic & Technology
        - Food & Agriculture
        - Transportation
        - Storage & Organization
        - Utility & Tools
        - Unknown/Other

        Mod List:
        {json.dumps(mod_data, indent=2)}

        Respond with ONLY this JSON format (no other text):
        {{
            "Mod Name 1": "Quality of Life (QOL)",
            "Mod Name 2": "Building & Construction",
            "Mod Name 3": "Graphics & Visual"
        }}

        Use the EXACT mod names from the list above and the EXACT category names listed. Do not add any explanations or additional text.
        """
        
        # Get AI categorization
        result = crash_analyzer.analyze_with_ai(prompt)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        
        # Try to parse the JSON response
        try:
            import re
            analysis_text = result.get('analysis', '')
            
            # Clean up the response text
            analysis_text = analysis_text.strip()
            
            # Try multiple parsing strategies
            categories = None
            
            # Strategy 1: Look for JSON object in the response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', analysis_text, re.DOTALL)
            if json_match:
                try:
                    categories_json = json_match.group(0)
                    categories = json.loads(categories_json)
                except json.JSONDecodeError:
                    pass
            
            # Strategy 2: Try to parse the entire response as JSON
            if not categories:
                try:
                    categories = json.loads(analysis_text)
                except json.JSONDecodeError:
                    pass
            
            # Strategy 3: Look for key-value pairs and build JSON manually
            if not categories:
                try:
                    categories = {}
                    # Look for patterns like "Mod Name": "Category"
                    pattern = r'"([^"]+)"\s*:\s*"([^"]+)"'
                    matches = re.findall(pattern, analysis_text)
                    for mod_name, category in matches:
                        categories[mod_name] = category
                except:
                    pass
            
            # Strategy 4: Fallback - create basic categorization based on mod names
            if not categories or len(categories) == 0:
                categories = {}
                for mod in mods:
                    mod_name = mod.get('display_name', mod.get('name', 'Unknown'))
                    # Simple keyword-based categorization as fallback
                    category = categorize_by_keywords(mod_name, mod.get('description', ''))
                    categories[mod_name] = category
            
            if categories and len(categories) > 0:
                # Map clean names back to original names
                mapped_categories = {}
                for mod_info in mod_data:
                    clean_name = mod_info['name']
                    original_name = mod_info['original_name']
                    if clean_name in categories:
                        mapped_categories[original_name] = categories[clean_name]
                    else:
                        # Try to find a fuzzy match
                        for category_key, category_value in categories.items():
                            if (clean_name.lower() in category_key.lower() or 
                                category_key.lower() in clean_name.lower()):
                                mapped_categories[original_name] = category_value
                                break
                        else:
                            # Use fallback categorization
                            mapped_categories[original_name] = categorize_by_keywords(original_name, mod_info.get('description', ''))
                
                return jsonify({
                    'success': True,
                    'categories': mapped_categories,
                    'model_used': result.get('model_used', 'Unknown'),
                    'timestamp': result.get('timestamp', ''),
                    'mod_count': len(mods),
                    'debug_info': {
                        'raw_response_length': len(analysis_text),
                        'categories_found': len(categories),
                        'mapped_categories': len(mapped_categories),
                        'parsing_method': 'ai_analysis'
                    }
                })
            else:
                return jsonify({
                    'error': 'No valid categories could be extracted from AI response',
                    'raw_response': analysis_text[:500] + '...' if len(analysis_text) > 500 else analysis_text
                }), 500
            
        except Exception as parse_error:
            # If all parsing fails, return error with debug info
            return jsonify({
                'error': f'Failed to parse AI categorization response: {str(parse_error)}',
                'raw_response': result.get('analysis', '')[:500] + '...' if len(result.get('analysis', '')) > 500 else result.get('analysis', '')
            }), 500
        
    except Exception as e:
        return jsonify({'error': f'Categorization failed: {str(e)}'}), 500

def categorize_by_keywords(mod_name, description):
    """Fallback categorization based on keywords in mod name and description"""
    text = (mod_name + ' ' + description).lower()
    
    # Define keyword mappings
    keywords = {
        'Quality of Life (QOL)': ['inventory', 'jei', 'waila', 'tooltip', 'keybind', 'config', 'settings', 'gui', 'interface', 'hud', 'minimap', 'waypoint', 'bookmark', 'search', 'filter', 'sort', 'organize', 'backpack', 'pouch', 'bag'],
        'Building & Construction': ['building', 'construction', 'architect', 'structure', 'blueprint', 'schematic', 'worldedit', 'build', 'house', 'castle', 'bridge', 'tower', 'wall', 'roof', 'floor', 'decorative', 'furniture', 'chair', 'table', 'bed'],
        'Graphics & Visual': ['shader', 'texture', 'visual', 'graphics', 'render', 'lighting', 'shadow', 'particle', 'effect', 'animation', 'model', 'skin', 'cosmetic', 'beauty', 'enhancement', 'optifine', 'iris', 'sodium', 'canvas'],
        'Performance & Optimization': ['performance', 'optimization', 'fps', 'lag', 'memory', 'cpu', 'gpu', 'optimize', 'boost', 'speed', 'fast', 'efficient', 'lightweight', 'minimal', 'reduced', 'compressed', 'cached'],
        'Adventure & Exploration': ['adventure', 'exploration', 'dungeon', 'cave', 'biome', 'dimension', 'world', 'generation', 'structure', 'ruin', 'temple', 'mansion', 'village', 'city', 'landscape', 'terrain', 'mountain', 'ocean', 'forest'],
        'Combat & Weapons': ['combat', 'weapon', 'sword', 'bow', 'arrow', 'armor', 'shield', 'battle', 'fight', 'war', 'pvp', 'pve', 'mob', 'enemy', 'boss', 'dungeon', 'loot', 'treasure', 'magic', 'spell'],
        'Magic & Technology': ['magic', 'tech', 'technology', 'machine', 'automation', 'redstone', 'energy', 'power', 'electric', 'mechanical', 'industrial', 'factory', 'processing', 'crafting', 'smelting', 'furnace', 'generator', 'cable', 'wire'],
        'Food & Agriculture': ['food', 'agriculture', 'farming', 'crop', 'seed', 'plant', 'tree', 'fruit', 'vegetable', 'animal', 'livestock', 'cow', 'pig', 'chicken', 'sheep', 'breed', 'harvest', 'cook', 'recipe', 'kitchen'],
        'Transportation': ['transport', 'vehicle', 'car', 'boat', 'ship', 'plane', 'helicopter', 'train', 'rail', 'track', 'road', 'path', 'teleport', 'portal', 'flight', 'fly', 'speed', 'travel', 'journey', 'explore'],
        'Storage & Organization': ['storage', 'chest', 'barrel', 'container', 'inventory', 'item', 'organize', 'sort', 'filter', 'search', 'catalog', 'database', 'library', 'archive', 'warehouse', 'depot', 'vault', 'safe', 'locker'],
        'Utility & Tools': ['utility', 'tool', 'pickaxe', 'axe', 'shovel', 'hoe', 'hammer', 'wrench', 'screwdriver', 'multitool', 'gadget', 'device', 'apparatus', 'instrument', 'equipment', 'gear', 'kit', 'set', 'collection']
    }
    
    # Score each category based on keyword matches
    scores = {}
    for category, words in keywords.items():
        score = sum(1 for word in words if word in text)
        if score > 0:
            scores[category] = score
    
    # Return the category with the highest score, or Unknown/Other if no matches
    if scores:
        return max(scores, key=scores.get)
    else:
        return 'Unknown/Other'

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

if __name__ == '__main__':
    print("Starting Minecraft Mod Handler Web Application...")
    print("Make sure Ollama is running for AI features!")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
