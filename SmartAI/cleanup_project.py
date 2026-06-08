#!/usr/bin/env python3
"""
Project Cleanup Script
Organizes and removes unnecessary files from the SmartAI project
"""

import os
import shutil
import sys
from pathlib import Path

def create_directory_if_not_exists(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def move_file(source, destination):
    """Move file with error handling"""
    try:
        if os.path.exists(source):
            shutil.move(source, destination)
            print(f"Moved: {source} -> {destination}")
        else:
            print(f"File not found: {source}")
    except Exception as e:
        print(f"Error moving {source}: {e}")

def remove_file(file_path):
    """Remove file with error handling"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed: {file_path}")
        else:
            print(f"File not found: {file_path}")
    except Exception as e:
        print(f"Error removing {file_path}: {e}")

def cleanup_project():
    """Main cleanup function"""
    print("=== SmartAI Project Cleanup ===\n")
    
    # Create organized directories
    directories = ['tests', 'demos', 'utils', 'docs']
    for directory in directories:
        create_directory_if_not_exists(directory)
    
    print("\n--- Moving Test Files ---")
    test_files = [
        'test_sensor_availability.py',
        'test_speed_verification.py',
        'test_adaptive_speed.py',
        'test_opengl.py',
        'test_system.py'
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            move_file(test_file, f"tests/{test_file}")
    
    print("\n--- Moving Demo Files ---")
    demo_files = [
        'simple_2d_demo.py',
        'vision_demo.py',
        'simulation_demo.py',
        'floor_plan_gui_demo.py'
    ]
    
    for demo_file in demo_files:
        if os.path.exists(demo_file):
            move_file(demo_file, f"demos/{demo_file}")
    
    print("\n--- Moving Utility Files ---")
    utility_files = [
        'generate_rectangular_floor_plan.py',
        'generate_hdb_floor_plan.py',
        'generate_floor_plan.py',
        'floor_plan_utils.py'
    ]
    
    for utility_file in utility_files:
        if os.path.exists(utility_file):
            move_file(utility_file, f"utils/{utility_file}")
    
    print("\n--- Moving Documentation ---")
    doc_files = [
        'FLOOR_PLAN_INTEGRATION_GUIDE.md'
    ]
    
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            move_file(doc_file, f"docs/{doc_file}")
    
    print("\n--- Removing Unnecessary Files ---")
    files_to_remove = [
        'requirements2.txt',  # Empty file
        'exploration_graph.json',  # Removed functionality
        'gui_floor_plan_integration.py'  # Duplicate file
    ]
    
    for file_to_remove in files_to_remove:
        remove_file(file_to_remove)
    
    print("\n--- Checking for Empty Files ---")
    # Check for any remaining empty files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') or file.endswith('.txt'):
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) == 0:
                    print(f"Found empty file: {file_path}")
                    response = input(f"Remove empty file {file_path}? (y/n): ")
                    if response.lower() == 'y':
                        remove_file(file_path)
    
    print("\n--- Creating .gitkeep files ---")
    # Add .gitkeep files to empty directories to preserve them in git
    for directory in directories:
        gitkeep_file = f"{directory}/.gitkeep"
        if not os.path.exists(gitkeep_file):
            with open(gitkeep_file, 'w') as f:
                f.write("# This file ensures the directory is tracked by git\n")
            print(f"Created: {gitkeep_file}")
    
    print("\n=== Cleanup Summary ===")
    print("✅ Created organized directories: tests/, demos/, utils/, docs/")
    print("✅ Moved test files to tests/")
    print("✅ Moved demo files to demos/")
    print("✅ Moved utility files to utils/")
    print("✅ Moved documentation to docs/")
    print("✅ Removed unnecessary files")
    print("\n📁 Current project structure:")
    
    # Show current structure
    for item in sorted(os.listdir('.')):
        if os.path.isdir(item) and not item.startswith('.') and item not in ['venv', '__pycache__']:
            print(f"  📁 {item}/")
        elif os.path.isfile(item) and not item.startswith('.'):
            print(f"  📄 {item}")
    
    print("\n🎉 Project cleanup completed!")

if __name__ == "__main__":
    # Ask for confirmation before proceeding
    print("This script will reorganize your project files.")
    print("It will move test files to tests/, demo files to demos/, etc.")
    response = input("Do you want to proceed? (y/n): ")
    
    if response.lower() == 'y':
        cleanup_project()
    else:
        print("Cleanup cancelled.") 