# -*- coding: utf-8 -*-
"""
Floor Plan GUI Integration Demo
Shows how to integrate the floor plan JSON into the robot GUI
"""

import sys
import os
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import math
import numpy as np
from PIL import Image, ImageDraw

# Add the src directory to the path
sys.path.append("src")

from src.core.floor_plan_types import load_floor_plan_from_json, FloorPlanObject, ObjectType


class FloorPlanCameraPanel:
    """Camera panel that renders the actual floor plan environment"""
    
    def __init__(self, parent, width=320, height=240):
        self.parent = parent
        self.width = width
        self.height = height
        
        # Load floor plan
        self.floor_plan_objects = load_floor_plan_from_json("floor_plan.json")
        print(f"Loaded {len(self.floor_plan_objects)} objects for camera panel")
        
        # Create camera view frame
        self.frame = ctk.CTkFrame(parent)
        
        # Title
        self.title_label = ctk.CTkLabel(self.frame, text="Surveillance Camera", font=("Arial", 14, "bold"))
        self.title_label.pack(pady=5)
        
        # Camera view canvas
        self.canvas = tk.Canvas(self.frame, width=width, height=height, bg="lightgray")
        self.canvas.pack(pady=5)
        
        # Status info
        self.status_label = ctk.CTkLabel(self.frame, text="Objects detected: 0")
        self.status_label.pack(pady=5)
        
        # Initial render
        self.update_camera_view(0, 0, 0)  # Robot at origin
    
    def update_camera_view(self, robot_x, robot_y, robot_angle):
        """Update camera view based on robot position and orientation"""
        # Create a new image for the camera view
        image = Image.new('RGB', (self.width, self.height), (220, 220, 220))
        draw = ImageDraw.Draw(image)
        
        # Camera parameters
        scale = 20  # pixels per meter
        fov = 90  # field of view in degrees
        view_distance = 10  # meters
        
        # Draw objects visible to the camera
        visible_objects = 0
        
        for obj in self.floor_plan_objects:
            # Transform object position to robot's local frame
            dx = obj.position[0] - robot_x
            dy = obj.position[1] - robot_y
            
            # Rotate to robot's frame
            local_x = dx * math.cos(-robot_angle) - dy * math.sin(-robot_angle)
            local_y = dx * math.sin(-robot_angle) + dy * math.cos(-robot_angle)
            
            # Only draw objects in front of robot and within FOV
            angle_to_obj = math.atan2(local_y, local_x)
            fov_rad = math.radians(fov)
            
            if local_x > 0 and abs(angle_to_obj) < fov_rad/2 and local_x < view_distance:
                # Project to camera surface
                px = int(self.width/2 + (local_y / (view_distance * math.tan(fov_rad/2))) * (self.width/2))
                py = int(self.height - (local_x / view_distance) * self.height)
                
                # Calculate object size on screen
                obj_w = max(2, int(obj.dimensions[0] * scale * self.width / (view_distance * scale)))
                obj_h = max(2, int(obj.dimensions[1] * scale * self.height / (view_distance * scale)))
                
                # Draw object rectangle
                rect = [px - obj_w//2, py - obj_h//2, px + obj_w//2, py + obj_h//2]
                draw.rectangle(rect, fill=obj.color, outline=(0, 0, 0))
                
                visible_objects += 1
        
        # Draw robot indicator (bottom center)
        robot_points = [
            (self.width//2, self.height - 5),
            (self.width//2 - 8, self.height),
            (self.width//2 + 8, self.height)
        ]
        draw.polygon(robot_points, fill=(100, 150, 255), outline=(0, 0, 0))
        
        # Update canvas
        self.photo = tk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        
        # Update status
        self.status_label.configure(text=f"Objects detected: {visible_objects}")
        
        return visible_objects


class FloorPlanMapPanel:
    """2D map panel showing the floor plan from above"""
    
    def __init__(self, parent, width=400, height=300):
        self.parent = parent
        self.width = width
        self.height = height
        
        # Load floor plan
        self.floor_plan_objects = load_floor_plan_from_json("floor_plan.json")
        
        # Create map frame
        self.frame = ctk.CTkFrame(parent)
        
        # Title
        self.title_label = ctk.CTkLabel(self.frame, text="Floor Plan Map", font=("Arial", 14, "bold"))
        self.title_label.pack(pady=5)
        
        # Map canvas
        self.canvas = tk.Canvas(self.frame, width=width, height=height, bg="white")
        self.canvas.pack(pady=5)
        
        # Legend
        self.create_legend()
        
        # Initial render
        self.render_map()
    
    def create_legend(self):
        """Create a legend for the map"""
        legend_frame = ctk.CTkFrame(self.frame)
        legend_frame.pack(pady=5)
        
        legend_items = [
            ("Walls", (150, 150, 150)),
            ("Obstacles", (255, 0, 0)),
            ("Furniture", (139, 69, 19)),
            ("Doors", (139, 69, 19)),
            ("Windows", (173, 216, 230))
        ]
        
        for i, (name, color) in enumerate(legend_items):
            item_frame = ctk.CTkFrame(legend_frame)
            item_frame.pack(side="left", padx=5)
            
            # Color indicator
            color_canvas = tk.Canvas(item_frame, width=20, height=20, bg=f'#{color[0]:02x}{color[1]:02x}{color[2]:02x}')
            color_canvas.pack(side="left", padx=2)
            
            # Label
            ctk.CTkLabel(item_frame, text=name, font=("Arial", 10)).pack(side="left", padx=2)
    
    def render_map(self):
        """Render the floor plan map"""
        # Clear canvas
        self.canvas.delete("all")
        
        # Calculate scale to fit all objects
        scale = min(self.width / 40, self.height / 40)  # 40m x 40m world
        center_x = self.width // 2
        center_y = self.height // 2
        
        # Draw grid
        for i in range(-20, 21, 2):
            grid_x = center_x + i * scale
            grid_y = center_y + i * scale
            self.canvas.create_line(grid_x, 0, grid_x, self.height, fill="lightgray", width=1)
            self.canvas.create_line(0, grid_y, self.width, grid_y, fill="lightgray", width=1)
        
        # Draw objects
        for obj in self.floor_plan_objects:
            # Convert world coordinates to screen coordinates
            screen_x = center_x + obj.position[0] * scale
            screen_y = center_y + obj.position[1] * scale
            
            # Calculate object size on screen
            obj_width = obj.dimensions[0] * scale
            obj_height = obj.dimensions[1] * scale
            
            # Draw object rectangle
            x1 = screen_x - obj_width/2
            y1 = screen_y - obj_height/2
            x2 = screen_x + obj_width/2
            y2 = screen_y + obj_height/2
            
            color = f'#{obj.color[0]:02x}{obj.color[1]:02x}{obj.color[2]:02x}'
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", width=1)
            
            # Add object name if it fits
            if obj_width > 30 and obj_height > 15:
                self.canvas.create_text(screen_x, screen_y, text=obj.name, font=("Arial", 8))
        
        # Draw coordinate axes
        self.canvas.create_line(center_x, 0, center_x, self.height, fill="blue", width=2)
        self.canvas.create_line(0, center_y, self.width, center_y, fill="red", width=2)
        
        # Draw origin marker
        self.canvas.create_oval(center_x-3, center_y-3, center_x+3, center_y+3, fill="green")


class FloorPlanIntegrationDemo:
    """Demo application showing floor plan integration"""
    
    def __init__(self):
        # Setup GUI
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Floor Plan Integration Demo")
        self.root.geometry("800x600")
        
        # Create main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(self.main_frame, text="Floor Plan Integration Demo", 
                                  font=("Arial", 18, "bold"))
        title_label.pack(pady=10)
        
        # Create panels frame
        panels_frame = ctk.CTkFrame(self.main_frame)
        panels_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel - Camera view
        left_frame = ctk.CTkFrame(panels_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        self.camera_panel = FloorPlanCameraPanel(left_frame)
        self.camera_panel.frame.pack(fill="both", expand=True)
        
        # Right panel - Map view
        right_frame = ctk.CTkFrame(panels_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        self.map_panel = FloorPlanMapPanel(right_frame)
        self.map_panel.frame.pack(fill="both", expand=True)
        
        # Control panel
        control_frame = ctk.CTkFrame(self.main_frame)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Robot position controls
        pos_frame = ctk.CTkFrame(control_frame)
        pos_frame.pack(pady=5)
        
        ctk.CTkLabel(pos_frame, text="Robot Position:").pack(side="left", padx=5)
        
        # X position
        ctk.CTkLabel(pos_frame, text="X:").pack(side="left", padx=2)
        self.x_var = tk.DoubleVar(value=0.0)
        x_entry = ctk.CTkEntry(pos_frame, textvariable=self.x_var, width=60)
        x_entry.pack(side="left", padx=2)
        
        # Y position
        ctk.CTkLabel(pos_frame, text="Y:").pack(side="left", padx=2)
        self.y_var = tk.DoubleVar(value=0.0)
        y_entry = ctk.CTkEntry(pos_frame, textvariable=self.y_var, width=60)
        y_entry.pack(side="left", padx=2)
        
        # Angle
        ctk.CTkLabel(pos_frame, text="Angle:").pack(side="left", padx=2)
        self.angle_var = tk.DoubleVar(value=0.0)
        angle_entry = ctk.CTkEntry(pos_frame, textvariable=self.angle_var, width=60)
        angle_entry.pack(side="left", padx=2)
        
        # Update button
        update_btn = ctk.CTkButton(pos_frame, text="Update Camera", command=self.update_camera)
        update_btn.pack(side="left", padx=10)
        
        # Info label
        self.info_label = ctk.CTkLabel(control_frame, text="Floor plan loaded successfully!")
        self.info_label.pack(pady=5)
    
    def update_camera(self):
        """Update camera view with current robot position"""
        x = self.x_var.get()
        y = self.y_var.get()
        angle = math.radians(self.angle_var.get())
        
        visible_objects = self.camera_panel.update_camera_view(x, y, angle)
        self.info_label.configure(text=f"Camera updated - {visible_objects} objects visible")
    
    def run(self):
        """Run the demo application"""
        self.root.mainloop()


def main():
    """Main function"""
    print("🏠 Floor Plan Integration Demo")
    print("=" * 40)
    
    # Check if floor plan file exists
    if not os.path.exists("floor_plan.json"):
        print("❌ floor_plan.json not found!")
        print("Please run generate_floor_plan.py first")
        return
    
    print("✅ floor_plan.json found")
    print("🚀 Starting demo application...")
    
    # Run the demo
    demo = FloorPlanIntegrationDemo()
    demo.run()


if __name__ == "__main__":
    main() 