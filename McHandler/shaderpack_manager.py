"""
Shaderpack Manager - Core functionality for managing Minecraft shaderpacks
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class ShaderpackManager:
    """Core shaderpack management functionality"""
    
    def __init__(self):
        self.shaderpacks_dir = None
        self.backup_dir = None
        
    def set_minecraft_directory(self, path: str):
        """Set the Minecraft directory path"""
        # Handle ATLauncher structure
        if "ATLauncher" in path and "instances" in path:
            # ATLauncher: path points to instance directory
            self.shaderpacks_dir = Path(path) / "shaderpacks"
            self.backup_dir = Path(path) / "shaderpack_backups"
        else:
            # Standard Minecraft installation
            self.shaderpacks_dir = Path(path) / "shaderpacks"
            self.backup_dir = Path(path) / "shaderpack_backups"
        
        self.backup_dir.mkdir(exist_ok=True)
        
    def get_installed_shaderpacks(self) -> List[Dict]:
        """Get list of installed shaderpacks with metadata"""
        if not self.shaderpacks_dir or not self.shaderpacks_dir.exists():
            return []
            
        shaderpacks = []
        for shaderpack_file in self.shaderpacks_dir.glob("*.zip"):
            shaderpack_info = {
                'name': shaderpack_file.stem,  # Name without .zip extension
                'filename': shaderpack_file.name,
                'path': str(shaderpack_file),
                'size': shaderpack_file.stat().st_size,
                'modified': datetime.fromtimestamp(shaderpack_file.stat().st_mtime),
                'enabled': True
            }
            
            # Try to extract shaderpack info from zip
            try:
                with zipfile.ZipFile(shaderpack_file, 'r') as zip_file:
                    # Look for shaderpack metadata files
                    for info_file in ['shaders/shaders.properties', 'shaders.properties', 'shader.properties']:
                        if info_file in zip_file.namelist():
                            with zip_file.open(info_file) as f:
                                content = f.read().decode('utf-8', errors='ignore')
                                shaderpack_info.update(self._parse_shaderpack_info(content))
                                break
            except Exception as e:
                shaderpack_info['error'] = str(e)
                
            shaderpacks.append(shaderpack_info)
            
        return sorted(shaderpacks, key=lambda x: x['name'])
    
    def _parse_shaderpack_info(self, content: str) -> Dict:
        """Parse shaderpack information from properties file"""
        info = {}
        
        try:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'shaderpack.name':
                        info['display_name'] = value
                    elif key == 'shaderpack.version':
                        info['version'] = value
                    elif key == 'shaderpack.author':
                        info['author'] = value
                    elif key == 'shaderpack.description':
                        info['description'] = value
        except Exception:
            pass
        
        return info
    
    def upload_shaderpacks(self, shaderpack_files: List[str]) -> Dict:
        """Upload shaderpack files to the shaderpacks directory"""
        if not self.shaderpacks_dir:
            raise ValueError("Minecraft directory not set")
        
        results = {
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        for shaderpack_file in shaderpack_files:
            try:
                source_path = Path(shaderpack_file)
                dest_path = self.shaderpacks_dir / source_path.name
                
                # Check if shaderpack already exists
                if dest_path.exists():
                    results['skipped'].append({
                        'file': source_path.name,
                        'reason': 'Shaderpack already exists'
                    })
                    continue
                
                # Copy the shaderpack file
                shutil.copy2(source_path, dest_path)
                results['successful'].append(source_path.name)
                
            except Exception as e:
                results['failed'].append({
                    'file': source_path.name,
                    'error': str(e)
                })
        
        return results
    
    def remove_shaderpacks(self, shaderpack_names: List[str]) -> Dict:
        """Remove shaderpack files"""
        if not self.shaderpacks_dir:
            raise ValueError("Minecraft directory not set")
        
        results = {
            'successful': [],
            'failed': []
        }
        
        for shaderpack_name in shaderpack_names:
            try:
                shaderpack_path = self.shaderpacks_dir / shaderpack_name
                if shaderpack_path.exists():
                    shaderpack_path.unlink()
                    results['successful'].append(shaderpack_name)
                else:
                    results['failed'].append({
                        'shaderpack': shaderpack_name,
                        'error': 'File not found'
                    })
            except Exception as e:
                results['failed'].append({
                    'shaderpack': shaderpack_name,
                    'error': str(e)
                })
        
        return results
    
    def backup_shaderpacks(self) -> str:
        """Create a backup of all shaderpacks"""
        if not self.shaderpacks_dir or not self.shaderpacks_dir.exists():
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"shaderpacks_backup_{timestamp}"
        
        shutil.copytree(self.shaderpacks_dir, backup_path)
        return str(backup_path)
    
    def restore_shaderpacks(self, backup_path: str):
        """Restore shaderpacks from backup"""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_path}")
            
        if self.shaderpacks_dir.exists():
            shutil.rmtree(self.shaderpacks_dir)
            
        shutil.copytree(backup_path, self.shaderpacks_dir)
    
    def get_backup_list(self) -> List[Dict]:
        """Get list of available shaderpack backups"""
        if not self.backup_dir or not self.backup_dir.exists():
            return []
        
        backups = []
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir() and backup_path.name.startswith('shaderpacks_backup_'):
                backup_info = {
                    'name': backup_path.name,
                    'path': str(backup_path),
                    'created': datetime.fromtimestamp(backup_path.stat().st_mtime),
                    'size': sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
                }
                backups.append(backup_info)
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def disable_shaderpack(self, shaderpack_name: str):
        """Disable a shaderpack by renaming it"""
        shaderpack_path = self.shaderpacks_dir / shaderpack_name
        if shaderpack_path.exists():
            disabled_path = shaderpack_path.with_suffix('.zip.disabled')
            shaderpack_path.rename(disabled_path)
    
    def enable_shaderpack(self, shaderpack_name: str):
        """Enable a disabled shaderpack"""
        disabled_path = self.shaderpacks_dir / f"{shaderpack_name}.disabled"
        if disabled_path.exists():
            shaderpack_path = disabled_path.with_suffix('.zip')
            disabled_path.rename(shaderpack_path)
