"""
Compatibility Checker - Check for mod conflicts and compatibility issues
"""

import re
import json
from typing import Dict, List, Set, Tuple
from mod_manager import ModManager

class CompatibilityChecker:
    """Check for mod compatibility and conflicts"""
    
    def __init__(self, mod_manager: ModManager):
        self.mod_manager = mod_manager
        self.known_conflicts = self._load_known_conflicts()
        self.version_patterns = self._load_version_patterns()
        
    def _load_known_conflicts(self) -> Dict[str, List[str]]:
        """Load known mod conflicts from a simple database"""
        # This is a simplified version - in a real app, this would be loaded from a file or API
        return {
            "OptiFine": ["Sodium", "Iris", "Canvas"],
            "Sodium": ["OptiFine"],
            "Iris": ["OptiFine"],
            "JEI": ["NEI", "Just Enough Items"],
            "NEI": ["JEI", "Just Enough Items"],
            "Just Enough Items": ["JEI", "NEI"],
            "Forge": ["Fabric"],
            "Fabric": ["Forge"]
        }
    
    def _load_version_patterns(self) -> Dict[str, str]:
        """Load version compatibility patterns"""
        return {
            "1.20.1": ["1.20", "1.20.1"],
            "1.20": ["1.20", "1.20.1"],
            "1.19.4": ["1.19", "1.19.4"],
            "1.19.3": ["1.19", "1.19.3"],
            "1.19.2": ["1.19", "1.19.2"],
            "1.19.1": ["1.19", "1.19.1"],
            "1.19": ["1.19", "1.19.1", "1.19.2", "1.19.3", "1.19.4"]
        }
    
    def check_mod_compatibility(self) -> Dict[str, List[Dict]]:
        """Check all installed mods for compatibility issues"""
        mods = self.mod_manager.get_installed_mods()
        issues = {
            "conflicts": [],
            "version_mismatches": [],
            "missing_dependencies": [],
            "warnings": []
        }
        
        # Check for conflicts
        issues["conflicts"] = self._check_conflicts(mods)
        
        # Check for version mismatches
        issues["version_mismatches"] = self._check_version_mismatches(mods)
        
        # Check for missing dependencies
        issues["missing_dependencies"] = self._check_dependencies(mods)
        
        # General warnings
        issues["warnings"] = self._check_general_warnings(mods)
        
        return issues
    
    def _check_conflicts(self, mods: List[Dict]) -> List[Dict]:
        """Check for known mod conflicts"""
        conflicts = []
        mod_names = [mod.get('display_name', mod['name']) for mod in mods]
        
        for mod in mods:
            mod_name = mod.get('display_name', mod['name'])
            
            if mod_name in self.known_conflicts:
                conflicting_mods = self.known_conflicts[mod_name]
                for conflict_mod in conflicting_mods:
                    if conflict_mod in mod_names:
                        conflicts.append({
                            "type": "conflict",
                            "mod1": mod_name,
                            "mod2": conflict_mod,
                            "severity": "high",
                            "description": f"{mod_name} conflicts with {conflict_mod}",
                            "solution": f"Remove either {mod_name} or {conflict_mod}"
                        })
        
        return conflicts
    
    def _check_version_mismatches(self, mods: List[Dict]) -> List[Dict]:
        """Check for version compatibility issues"""
        version_issues = []
        
        # Group mods by version
        version_groups = {}
        for mod in mods:
            version = mod.get('version', 'Unknown')
            if version != 'Unknown':
                if version not in version_groups:
                    version_groups[version] = []
                version_groups[version].append(mod)
        
        # Check for incompatible versions
        if len(version_groups) > 1:
            versions = list(version_groups.keys())
            for i, version1 in enumerate(versions):
                for version2 in versions[i+1:]:
                    if not self._are_versions_compatible(version1, version2):
                        version_issues.append({
                            "type": "version_mismatch",
                            "version1": version1,
                            "version2": version2,
                            "mods1": [mod.get('display_name', mod['name']) for mod in version_groups[version1]],
                            "mods2": [mod.get('display_name', mod['name']) for mod in version_groups[version2]],
                            "severity": "medium",
                            "description": f"Version mismatch between {version1} and {version2} mods",
                            "solution": "Update all mods to the same Minecraft version"
                        })
        
        return version_issues
    
    def _check_dependencies(self, mods: List[Dict]) -> List[Dict]:
        """Check for missing dependencies"""
        dependency_issues = []
        mod_names = [mod.get('display_name', mod['name']).lower() for mod in mods]
        
        # Common dependency patterns
        dependencies = {
            "forge": ["minecraftforge", "forge"],
            "fabric": ["fabricloader", "fabric"],
            "optifine": ["forge", "fabric"],
            "jei": ["forge", "fabric"],
            "waila": ["forge"],
            "hwyla": ["forge"],
            "theoneprobe": ["forge"]
        }
        
        for mod in mods:
            mod_name = mod.get('display_name', mod['name']).lower()
            
            if mod_name in dependencies:
                required_deps = dependencies[mod_name]
                missing_deps = []
                
                for dep in required_deps:
                    if not any(dep in name for name in mod_names):
                        missing_deps.append(dep)
                
                if missing_deps:
                    dependency_issues.append({
                        "type": "missing_dependency",
                        "mod": mod.get('display_name', mod['name']),
                        "missing": missing_deps,
                        "severity": "high",
                        "description": f"{mod.get('display_name', mod['name'])} requires: {', '.join(missing_deps)}",
                        "solution": f"Install the missing dependencies: {', '.join(missing_deps)}"
                    })
        
        return dependency_issues
    
    def _check_general_warnings(self, mods: List[Dict]) -> List[Dict]:
        """Check for general warnings"""
        warnings = []
        
        # Check for too many mods
        if len(mods) > 100:
            warnings.append({
                "type": "performance_warning",
                "severity": "low",
                "description": f"You have {len(mods)} mods installed, which may impact performance",
                "solution": "Consider removing unused mods or using a modpack"
            })
        
        # Check for large mods
        large_mods = [mod for mod in mods if mod['size'] > 50 * 1024 * 1024]  # 50MB
        if large_mods:
            warnings.append({
                "type": "large_mods_warning",
                "severity": "low",
                "description": f"Large mods detected: {', '.join([mod.get('display_name', mod['name']) for mod in large_mods])}",
                "solution": "Monitor performance with these large mods"
            })
        
        # Check for duplicate mods
        mod_names = [mod.get('display_name', mod['name']) for mod in mods]
        duplicates = set([name for name in mod_names if mod_names.count(name) > 1])
        if duplicates:
            warnings.append({
                "type": "duplicate_mods",
                "severity": "medium",
                "description": f"Duplicate mods found: {', '.join(duplicates)}",
                "solution": "Remove duplicate mod files"
            })
        
        return warnings
    
    def _are_versions_compatible(self, version1: str, version2: str) -> bool:
        """Check if two Minecraft versions are compatible"""
        # Extract major version (e.g., "1.20" from "1.20.1")
        major1 = '.'.join(version1.split('.')[:2])
        major2 = '.'.join(version2.split('.')[:2])
        
        return major1 == major2
    
    def get_compatibility_report(self) -> str:
        """Generate a human-readable compatibility report"""
        issues = self.check_mod_compatibility()
        
        report = "=== MOD COMPATIBILITY REPORT ===\n\n"
        
        if issues["conflicts"]:
            report += "🚨 CONFLICTS FOUND:\n"
            for conflict in issues["conflicts"]:
                report += f"  • {conflict['description']}\n"
                report += f"    Solution: {conflict['solution']}\n\n"
        
        if issues["version_mismatches"]:
            report += "⚠️  VERSION MISMATCHES:\n"
            for mismatch in issues["version_mismatches"]:
                report += f"  • {mismatch['description']}\n"
                report += f"    Solution: {mismatch['solution']}\n\n"
        
        if issues["missing_dependencies"]:
            report += "❌ MISSING DEPENDENCIES:\n"
            for dep in issues["missing_dependencies"]:
                report += f"  • {dep['description']}\n"
                report += f"    Solution: {dep['solution']}\n\n"
        
        if issues["warnings"]:
            report += "ℹ️  WARNINGS:\n"
            for warning in issues["warnings"]:
                report += f"  • {warning['description']}\n"
                report += f"    Suggestion: {warning['solution']}\n\n"
        
        if not any(issues.values()):
            report += "✅ No compatibility issues found!\n"
        
        return report
