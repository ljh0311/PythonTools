"""
Mod Manager - Core functionality for managing Minecraft mods
"""

import os
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class ModManager:
    """Core mod management functionality"""
    
    def __init__(self):
        self.mods_dir = None
        self.backup_dir = None
        
    def set_minecraft_directory(self, path: str):
        """Set the Minecraft directory path"""
        path_obj = Path(path)
        
        # Check if the path is already a mods folder
        # Check if the last directory name is "mods" (case-insensitive)
        is_mods_folder = (
            path_obj.name.lower() == "mods" or
            str(path_obj).lower().endswith(os.sep + "mods") or
            str(path_obj).lower().endswith("/mods") or
            str(path_obj).lower().endswith("\\mods")
        )
        
        if is_mods_folder:
            # Path is already pointing to a mods folder, use it directly
            self.mods_dir = path_obj
            # Set backup directory to parent/mod_backups
            self.backup_dir = path_obj.parent / "mod_backups"
        elif "ATLauncher" in path and "instances" in path:
            # ATLauncher: path points to instance directory
            self.mods_dir = path_obj / "mods"
            self.backup_dir = path_obj / "mod_backups"
        else:
            # Standard Minecraft installation
            self.mods_dir = path_obj / "mods"
            self.backup_dir = path_obj / "mod_backups"
        
        self.backup_dir.mkdir(exist_ok=True)
        
    def get_installed_mods(self) -> List[Dict]:
        """Get list of installed mods with metadata"""
        if not self.mods_dir or not self.mods_dir.exists():
            return []
            
        mods = []
        for mod_file in self.mods_dir.glob("*.jar"):
            mod_info = {
                'name': mod_file.name,
                'path': str(mod_file),
                'size': mod_file.stat().st_size,
                'modified': datetime.fromtimestamp(mod_file.stat().st_mtime),
                'enabled': True
            }
            
            # Try to extract mod info from jar
            try:
                with zipfile.ZipFile(mod_file, 'r') as jar:
                    # Look for mod metadata files
                    for info_file in ['mcmod.info', 'mods.toml', 'fabric.mod.json']:
                        if info_file in jar.namelist():
                            with jar.open(info_file) as f:
                                content = f.read().decode('utf-8', errors='ignore')
                                mod_info.update(self._parse_mod_info(content, info_file))
                                break
            except Exception as e:
                mod_info['error'] = str(e)
                
            mods.append(mod_info)
            
        return sorted(mods, key=lambda x: x['name'])
    
    def _parse_mod_info(self, content: str, file_type: str) -> Dict:
        """Parse mod information from various metadata files"""
        info = {}
        
        if file_type == 'mcmod.info':
            # Legacy Forge format
            try:
                data = json.loads(content)
                if isinstance(data, list) and len(data) > 0:
                    mod_data = data[0]
                    info['display_name'] = self._clean_template_vars(mod_data.get('name', 'Unknown'))
                    info['version'] = self._clean_template_vars(mod_data.get('version', 'Unknown'))
                    info['description'] = self._clean_template_vars(mod_data.get('description', ''))
                    info['author'] = self._clean_template_vars(mod_data.get('author', 'Unknown'))
            except:
                pass
                
        elif file_type == 'fabric.mod.json':
            # Fabric format
            try:
                data = json.loads(content)
                info['display_name'] = self._clean_template_vars(data.get('name', 'Unknown'))
                info['version'] = self._clean_template_vars(data.get('version', 'Unknown'))
                info['description'] = self._clean_template_vars(data.get('description', ''))
                info['author'] = ', '.join(data.get('authors', ['Unknown']))
            except:
                pass
                
        elif file_type == 'mods.toml':
            # Modern Forge format (TOML)
            try:
                import toml
                data = toml.loads(content)
                if 'mods' in data and len(data['mods']) > 0:
                    mod_data = data['mods'][0]
                    info['display_name'] = self._clean_template_vars(mod_data.get('displayName', 'Unknown'))
                    info['version'] = self._clean_template_vars(mod_data.get('version', 'Unknown'))
                    info['description'] = self._clean_template_vars(mod_data.get('description', ''))
                    info['author'] = self._clean_template_vars(mod_data.get('authors', 'Unknown'))
            except ImportError:
                # Fallback parsing without toml library
                info = self._parse_toml_fallback(content)
            except:
                pass
                
        return info
    
    def _clean_template_vars(self, text: str) -> str:
        """Clean template variables like ${version} from text"""
        if not isinstance(text, str):
            return str(text)
        
        # Common template variables and their fallbacks
        template_vars = {
            '${version}': 'Unknown',
            '${file.jarVersion}': 'Unknown',
            '${mod_version}': 'Unknown',
            '${minecraft_version}': 'Unknown',
            '${loader_version}': 'Unknown',
            '${forge_version}': 'Unknown',
            '${fabric_version}': 'Unknown',
            '@VERSION@': 'Unknown',
            '@MOD_VERSION@': 'Unknown',
            '@MC_VERSION@': 'Unknown'
        }
        
        cleaned_text = text
        for template_var, fallback in template_vars.items():
            cleaned_text = cleaned_text.replace(template_var, fallback)
        
        # Remove any remaining template variables
        import re
        cleaned_text = re.sub(r'\$\{[^}]+\}', 'Unknown', cleaned_text)
        cleaned_text = re.sub(r'@[^@]+@', 'Unknown', cleaned_text)
        
        return cleaned_text.strip()
    
    def _parse_toml_fallback(self, content: str) -> Dict:
        """Fallback TOML parsing without toml library"""
        info = {}
        lines = content.split('\n')
        
        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
            elif '=' in line and current_section == 'mods':
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                if key == 'displayName':
                    info['display_name'] = self._clean_template_vars(value)
                elif key == 'version':
                    info['version'] = self._clean_template_vars(value)
                elif key == 'description':
                    info['description'] = self._clean_template_vars(value)
                elif key == 'authors':
                    info['author'] = self._clean_template_vars(value)
        
        return info
    
    def backup_mods(self) -> str:
        """Create a backup of all mods"""
        if not self.mods_dir or not self.mods_dir.exists():
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"mods_backup_{timestamp}"
        
        shutil.copytree(self.mods_dir, backup_path)
        return str(backup_path)
    
    def restore_mods(self, backup_path: str):
        """Restore mods from backup"""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_path}")
            
        if self.mods_dir.exists():
            shutil.rmtree(self.mods_dir)
            
        shutil.copytree(backup_path, self.mods_dir)
    
    def disable_mod(self, mod_name: str):
        """Disable a mod by renaming it"""
        mod_path = self.mods_dir / mod_name
        if mod_path.exists():
            disabled_path = mod_path.with_suffix('.jar.disabled')
            mod_path.rename(disabled_path)
    
    def enable_mod(self, mod_name: str):
        """Enable a disabled mod"""
        disabled_path = self.mods_dir / f"{mod_name}.disabled"
        if disabled_path.exists():
            mod_path = disabled_path.with_suffix('.jar')
            disabled_path.rename(mod_path)
    
    def upload_mods(self, mod_files: List[str]) -> Dict:
        """Upload mod files to the mods directory"""
        if not self.mods_dir:
            raise ValueError("Minecraft directory not set")
        
        results = {
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        for mod_file in mod_files:
            try:
                source_path = Path(mod_file)
                dest_path = self.mods_dir / source_path.name
                
                # Check if mod already exists
                if dest_path.exists():
                    results['skipped'].append({
                        'file': source_path.name,
                        'reason': 'Mod already exists'
                    })
                    continue
                
                # Copy the mod file
                shutil.copy2(source_path, dest_path)
                results['successful'].append(source_path.name)
                
            except Exception as e:
                results['failed'].append({
                    'file': source_path.name,
                    'error': str(e)
                })
        
        return results
    
    def remove_mods(self, mod_names: List[str]) -> Dict:
        """Remove mod files"""
        if not self.mods_dir:
            raise ValueError("Minecraft directory not set")
        
        results = {
            'successful': [],
            'failed': []
        }
        
        for mod_name in mod_names:
            try:
                mod_path = self.mods_dir / mod_name
                if mod_path.exists():
                    mod_path.unlink()
                    results['successful'].append(mod_name)
                else:
                    results['failed'].append({
                        'mod': mod_name,
                        'error': 'File not found'
                    })
            except Exception as e:
                results['failed'].append({
                    'mod': mod_name,
                    'error': str(e)
                })
        
        return results
    
    def get_backup_list(self) -> List[Dict]:
        """Get list of available backups"""
        if not self.backup_dir or not self.backup_dir.exists():
            return []
        
        backups = []
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir() and backup_path.name.startswith('mods_backup_'):
                backup_info = {
                    'name': backup_path.name,
                    'path': str(backup_path),
                    'created': datetime.fromtimestamp(backup_path.stat().st_mtime),
                    'size': sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
                }
                backups.append(backup_info)
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def categorize_mods_with_ai(self, mods: List[Dict], ai_analyzer) -> List[Dict]:
        """Categorize mods using AI analysis"""
        if not ai_analyzer.check_ollama_connection():
            raise ValueError("Ollama is not running")
        
        categorized_mods = []
        
        for mod in mods:
            try:
                # Create a prompt for AI categorization
                prompt = f"""
                Categorize this Minecraft mod based on its name and description:
                
                Mod Name: {mod.get('display_name', mod['name'])}
                Description: {mod.get('description', 'No description available')}
                
                Please categorize it into one of these categories:
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
                
                Respond with only the category name.
                """
                
                result = ai_analyzer.analyze_with_ai(prompt)
                if 'error' not in result:
                    mod['purpose'] = result.get('analysis', 'Unknown/Other').strip()
                else:
                    mod['purpose'] = 'Unknown/Other'
                    
            except Exception as e:
                mod['purpose'] = 'Unknown/Other'
                mod['categorization_error'] = str(e)
            
            categorized_mods.append(mod)
        
        return categorized_mods