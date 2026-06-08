#!/usr/bin/env python3
"""
Pygame Car Racing Simulation based on rental data from 22 - Sheet1.csv
Cars race based on their real-world performance metrics (fuel efficiency, cost, distance).
"""

import pygame
import pandas as pd
import numpy as np
import os
import random
from typing import List, Dict, Optional, Tuple

# Initialize Pygame
pygame.init()

# Constants
DEFAULT_SCREEN_WIDTH = 1000
DEFAULT_SCREEN_HEIGHT = 600
MIN_SCREEN_WIDTH = 800
MIN_SCREEN_HEIGHT = 500
FPS = 60
RACE_DISTANCE = 800  # pixels
START_X = 50
PIXELS_PER_KM = 10  # Conversion factor: 1 km = 10 pixels on screen

# UI Layout Constants
SECTION_SPACING = 15  # Space between major sections
COMPONENT_SPACING = 10  # Space between related components
PADDING = 10  # General padding

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (64, 64, 64)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)

# Category colors
CATEGORY_COLORS = {
    "Getgo": BLUE,
    "Car Club": GREEN,
    "Econ": YELLOW,
    "Stand": ORANGE,
    "Getgo(EV)": CYAN,
}


class Car:
    """Enhanced Car class with pygame attributes and performance metrics"""
    
    def __init__(self, name: str, category: str, stats: Dict, performance_score: float):
        self.name = name
        self.category = category
        self.stats = stats
        self.performance_score = performance_score
        
        # Pygame attributes
        self.position = [START_X, 0]  # x, y (y will be set based on lane)
        self.base_speed = 2.0 + (performance_score * 5.0)  # Base speed in pixels per frame
        self.current_speed = self.base_speed
        self.acceleration = 0.1
        self.color = CATEGORY_COLORS.get(category, WHITE)
        self.is_ev = category == "Getgo(EV)"
        
        # Race state
        self.finished = False
        self.finish_time = 0
        self.race_position = 0
        
        # Endurance race attributes
        self.fuel_capacity = 0.0  # Tank size in liters (user input)
        self.fuel_level = 0.0  # Current fuel remaining in liters
        self.distance_traveled_km = 0.0  # Total distance traveled in kilometers
        self.max_distance_km = 0.0  # Target distance for the race (user input)
        self.is_endurance_mode = False  # Flag to indicate endurance race mode
        
    def update(self, frame_count: int):
        """Update car position during race"""
        if not self.finished:
            # Add some random variation for realism
            speed_variation = random.uniform(0.9, 1.1)
            self.current_speed = self.base_speed * speed_variation
            
            # Update position
            self.position[0] += self.current_speed
            
            # Check if finished (will be updated dynamically in race screen)
            # This check is handled in the race update method
    
    def get_progress(self) -> float:
        """Get race progress as percentage"""
        if self.is_endurance_mode and self.max_distance_km > 0:
            # Endurance mode: progress based on distance traveled
            progress = (self.distance_traveled_km / self.max_distance_km) * 100
            return min(100.0, max(0.0, progress))
        else:
            # Basic mode: progress based on pixel position
            progress = ((self.position[0] - START_X) / RACE_DISTANCE) * 100
            return min(100.0, max(0.0, progress))
    
    def draw(self, screen: pygame.Surface, y_offset: int, font: pygame.font.Font):
        """Draw the car on screen"""
        car_width = 60
        car_height = 30
        
        # Draw car body
        car_rect = pygame.Rect(self.position[0], y_offset, car_width, car_height)
        pygame.draw.rect(screen, self.color, car_rect)
        pygame.draw.rect(screen, BLACK, car_rect, 2)
        
        # Draw car name
        name_surface = font.render(self.name[:15], True, BLACK)
        name_rect = name_surface.get_rect(center=(self.position[0] + car_width // 2, y_offset + car_height // 2))
        screen.blit(name_surface, name_rect)
        
        # Draw EV indicator if applicable
        if self.is_ev:
            ev_text = font.render("EV", True, BLACK)
            screen.blit(ev_text, (self.position[0] + car_width + 5, y_offset))


def calculate_performance_score(car_data: pd.Series, max_consumption: float, 
                                max_cost_per_km: float, max_distance: float) -> float:
    """
    Calculate combined performance score from multiple metrics.
    Higher score = better performance = faster car.
    """
    # Get metrics (handle missing values)
    consumption = car_data.get("Consumption (KM/L)", 0) or 0
    cost_per_km = car_data.get("Cost per KM", 0) or 0
    distance = car_data.get("Distance (KM)", 0) or 0
    
    # Normalize metrics (0-1 range)
    if max_consumption > 0:
        fuel_efficiency_factor = min(1.0, consumption / max_consumption)
    else:
        fuel_efficiency_factor = 0.5
    
    if max_cost_per_km > 0:
        # Lower cost is better, so invert
        cost_efficiency_factor = 1.0 - min(1.0, cost_per_km / max_cost_per_km)
    else:
        cost_efficiency_factor = 0.5
    
    if max_distance > 0:
        distance_factor = min(1.0, distance / max_distance)
    else:
        distance_factor = 0.5
    
    # Weighted combination (fuel efficiency most important)
    performance_score = (
        fuel_efficiency_factor * 0.5 +
        cost_efficiency_factor * 0.3 +
        distance_factor * 0.2
    )
    
    return max(0.0, min(1.0, performance_score))


def load_cars_from_csv(csv_path: str) -> List[Car]:
    """
    Load and process CSV data to create Car objects.
    Groups by car model and calculates average metrics.
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        return []
    
    try:
        # Load CSV
        df = pd.read_csv(csv_path)
        
        # Filter out calculator-generated records
        if "Car model" in df.columns:
            df = df[df["Car model"] != "Calculator Generated"]
        
        if df.empty:
            print("Error: No valid car data found in CSV")
            return []
        
        # Calculate max values for normalization
        max_consumption = df["Consumption (KM/L)"].max() if "Consumption (KM/L)" in df.columns else 30.0
        max_cost_per_km = df["Cost per KM"].max() if "Cost per KM" in df.columns else 3.0
        max_distance = df["Distance (KM)"].max() if "Distance (KM)" in df.columns else 150.0
        
        # Group by car model and category to get unique cars with average stats
        cars_data = []
        
        # Get unique combinations of car model and category
        if "Car model" in df.columns and "Car Cat" in df.columns:
            grouped = df.groupby(["Car model", "Car Cat"])
            
            for (car_model, category), group in grouped:
                if pd.isna(car_model) or pd.isna(category):
                    continue
                
                # Calculate average stats for this car
                avg_stats = {
                    "consumption": group["Consumption (KM/L)"].mean() if "Consumption (KM/L)" in group.columns else 0,
                    "cost_per_km": group["Cost per KM"].mean() if "Cost per KM" in group.columns else 0,
                    "distance": group["Distance (KM)"].mean() if "Distance (KM)" in group.columns else 0,
                    "total_cost": group["Total"].mean() if "Total" in group.columns else 0,
                }
                
                # Create a representative row for performance calculation
                representative_row = pd.Series({
                    "Consumption (KM/L)": avg_stats["consumption"],
                    "Cost per KM": avg_stats["cost_per_km"],
                    "Distance (KM)": avg_stats["distance"],
                })
                
                # Calculate performance score
                performance_score = calculate_performance_score(
                    representative_row, max_consumption, max_cost_per_km, max_distance
                )
                
                cars_data.append({
                    "name": str(car_model),
                    "category": str(category),
                    "stats": avg_stats,
                    "performance_score": performance_score
                })
        
        # Create Car objects
        cars = []
        for car_data in cars_data:
            car = Car(
                name=car_data["name"],
                category=car_data["category"],
                stats=car_data["stats"],
                performance_score=car_data["performance_score"]
            )
            cars.append(car)
        
        return cars
        
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []


class CarRacingSimulation:
    """Main simulation class managing the game loop and screens"""
    
    def __init__(self):
        # Initialize with default size, but make resizable
        self.screen_width = DEFAULT_SCREEN_WIDTH
        self.screen_height = DEFAULT_SCREEN_HEIGHT
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), 
            pygame.RESIZABLE
        )
        pygame.display.set_caption("Car Racing Simulation - Rental Data")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Game state
        self.state = "selection"  # "selection", "racing", "results"
        self.all_cars = []
        self.selected_cars = []
        self.race_results = []
        self.frame_count = 0
        
        # Load cars from CSV
        csv_path = "22 - Sheet1.csv"
        self.all_cars = load_cars_from_csv(csv_path)
        
        if not self.all_cars:
            print("Warning: No cars loaded. Using default cars.")
            # Create some default cars for testing
            self.all_cars = [
                Car("Toyota Corolla", "Econ", {"consumption": 15.0, "cost_per_km": 1.0, "distance": 50.0, "total_cost": 50.0}, 0.6),
                Car("Honda Fit", "Stand", {"consumption": 18.0, "cost_per_km": 0.8, "distance": 60.0, "total_cost": 48.0}, 0.7),
                Car("Mazda 3", "Getgo", {"consumption": 12.0, "cost_per_km": 0.9, "distance": 70.0, "total_cost": 63.0}, 0.65),
            ]
        
        # Selection screen state
        self.selection_scroll = 0
        self.selection_selected = set()
        
        # Search, filter, and sort state
        self.search_text = ""
        self.selected_category = "All Categories"
        self.sort_option = "Name (A-Z)"
        self.filtered_cars = []  # Filtered and sorted cars
        self.car_list_indices = []  # Map from filtered index to original index
        self.search_focused = False
        self.filter_dropdown_open = False
        self.sort_dropdown_open = False
        self.scrollbar_dragging = False
        self.scrollbar_drag_start_y = 0
        self.scrollbar_drag_start_scroll = 0
        
        # Endurance race state variables
        self.endurance_distance_km = 100.0  # Target distance (default: 100 km)
        self.endurance_distance_input = "100"  # String for distance input field
        self.endurance_input_focused = False  # Boolean for input focus state
        self.endurance_tank_capacities = {}  # Dict mapping car index to tank capacity
        self.endurance_tank_input_dialog = False  # Boolean for showing tank input dialog
        self.endurance_tank_inputs = {}  # Dict mapping car index to input string
        self.endurance_tank_input_focused = None  # Currently focused tank input (car index)
        self.tank_input_rects = {}  # Dict mapping car index to input rect (for click detection)
        self.tank_dialog_confirm_rect = None  # Confirm button rect in tank dialog
        
        # Initialize filtered cars
        self.update_filtered_cars()
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    # Handle window resize
                    self.screen_width = max(MIN_SCREEN_WIDTH, event.w)
                    self.screen_height = max(MIN_SCREEN_HEIGHT, event.h)
                    self.screen = pygame.display.set_mode(
                        (self.screen_width, self.screen_height),
                        pygame.RESIZABLE
                    )
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "racing":
                            self.state = "selection"
                        elif self.state == "results":
                            self.state = "selection"
                        else:
                            running = False
                    elif event.key == pygame.K_RETURN and self.state == "selection":
                        if len(self.selection_selected) >= 2:
                            self.start_race()
                    elif event.key == pygame.K_r and self.state == "results":
                        self.state = "selection"
                    elif self.state == "selection":
                        # Handle tank capacity dialog input
                        if self.endurance_tank_input_dialog and self.endurance_tank_input_focused is not None:
                            if event.key == pygame.K_BACKSPACE:
                                car_idx = self.endurance_tank_input_focused
                                if car_idx in self.endurance_tank_inputs:
                                    self.endurance_tank_inputs[car_idx] = self.endurance_tank_inputs[car_idx][:-1]
                            elif event.key == pygame.K_RETURN:
                                # Confirm button in dialog
                                if hasattr(self, 'tank_dialog_confirm_rect'):
                                    self.start_race()
                        # Handle distance input
                        elif self.race_type == "endurance" and self.endurance_input_focused:
                            if event.key == pygame.K_BACKSPACE:
                                self.endurance_distance_input = self.endurance_distance_input[:-1]
                        # Handle search input
                        elif self.search_focused:
                            if event.key == pygame.K_BACKSPACE:
                                self.search_text = self.search_text[:-1]
                                self.update_filtered_cars()
                        # Handle keyboard scrolling
                        elif not self.search_focused and not self.endurance_input_focused:
                            item_height = 40
                            list_height = self.screen_height - 230
                            max_scroll = max(0, len(self.filtered_cars) * item_height - list_height)
                            
                            if event.key == pygame.K_UP:
                                self.selection_scroll = max(0, self.selection_scroll - item_height)
                            elif event.key == pygame.K_DOWN:
                                self.selection_scroll = min(max_scroll, self.selection_scroll + item_height)
                            elif event.key == pygame.K_PAGEUP:
                                self.selection_scroll = max(0, self.selection_scroll - list_height)
                            elif event.key == pygame.K_PAGEDOWN:
                                self.selection_scroll = min(max_scroll, self.selection_scroll + list_height)
                            elif event.key == pygame.K_HOME:
                                self.selection_scroll = 0
                            elif event.key == pygame.K_END:
                                self.selection_scroll = max_scroll
                
                elif event.type == pygame.TEXTINPUT:
                    if self.state == "selection" and self.search_focused:
                        self.search_text += event.text
                        self.update_filtered_cars()
                
                elif event.type == pygame.MOUSEWHEEL:
                    if self.state == "selection":
                        item_height = 40
                        scroll_amount = -event.y * item_height  # Negative because wheel up should scroll up
                        list_height = self.screen_height - 230
                        max_scroll = max(0, len(self.filtered_cars) * item_height - list_height)
                        self.selection_scroll = max(0, min(max_scroll, self.selection_scroll + scroll_amount))
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.state == "selection":
                        # Handle tank capacity dialog clicks
                        if self.endurance_tank_input_dialog:
                            x, y = event.pos
                            # Check confirm button
                            if hasattr(self, 'tank_dialog_confirm_rect') and self.tank_dialog_confirm_rect.collidepoint(x, y):
                                self.start_race()
                                continue
                            # Check tank input fields
                            if hasattr(self, 'tank_input_rects'):
                                for car_idx, rect in self.tank_input_rects.items():
                                    if rect.collidepoint(x, y):
                                        self.endurance_tank_input_focused = car_idx
                                        break
                                else:
                                    self.endurance_tank_input_focused = None
                            continue
                        # Handle normal selection screen clicks
                        self.handle_selection_click(event.pos)
                    elif self.state == "results":
                        self.state = "selection"
                
                elif event.type == pygame.MOUSEMOTION:
                    if self.state == "selection" and self.scrollbar_dragging:
                        # Handle scrollbar dragging
                        list_y = 130
                        list_height = self.screen_height - 230
                        item_height = 40
                        max_scroll = max(0, len(self.filtered_cars) * item_height - list_height)
                        
                        if max_scroll > 0:
                            drag_delta = event.pos[1] - self.scrollbar_drag_start_y
                            scroll_delta = int((drag_delta / list_height) * max_scroll)
                            self.selection_scroll = max(0, min(max_scroll, self.scrollbar_drag_start_scroll + scroll_delta))
                
                elif event.type == pygame.MOUSEBUTTONUP:
                    if self.scrollbar_dragging:
                        self.scrollbar_dragging = False
            
            # Update game state
            if self.state == "racing":
                self.update_race()
            
            # Draw current screen
            if self.state == "selection":
                self.draw_selection_screen()
            elif self.state == "racing":
                self.draw_race_screen()
            elif self.state == "results":
                self.draw_results_screen()
            
            pygame.display.flip()
            self.clock.tick(FPS)
            self.frame_count += 1
        
        pygame.quit()
    
    def update_filtered_cars(self):
        """Update filtered and sorted car list based on current search, filter, and sort settings"""
        # Start with all cars
        filtered = list(self.all_cars)
        indices = list(range(len(self.all_cars)))
        
        # Apply search filter
        if self.search_text:
            search_lower = self.search_text.lower()
            new_filtered = []
            new_indices = []
            for i, car in enumerate(filtered):
                if (search_lower in car.name.lower() or 
                    search_lower in car.category.lower()):
                    new_filtered.append(car)
                    new_indices.append(indices[i])
            filtered = new_filtered
            indices = new_indices
        
        # Apply category filter
        if self.selected_category != "All Categories":
            new_filtered = []
            new_indices = []
            for i, car in enumerate(filtered):
                if car.category == self.selected_category:
                    new_filtered.append(car)
                    new_indices.append(indices[i])
            filtered = new_filtered
            indices = new_indices
        
        # Apply sorting
        if self.sort_option == "Name (A-Z)":
            sorted_pairs = sorted(zip(filtered, indices), key=lambda x: x[0].name.lower())
        elif self.sort_option == "Name (Z-A)":
            sorted_pairs = sorted(zip(filtered, indices), key=lambda x: x[0].name.lower(), reverse=True)
        elif self.sort_option == "Performance (High to Low)":
            sorted_pairs = sorted(zip(filtered, indices), key=lambda x: x[0].performance_score, reverse=True)
        elif self.sort_option == "Performance (Low to High)":
            sorted_pairs = sorted(zip(filtered, indices), key=lambda x: x[0].performance_score)
        elif self.sort_option == "Category":
            sorted_pairs = sorted(zip(filtered, indices), key=lambda x: (x[0].category, x[0].name.lower()))
        elif self.sort_option == "Efficiency (High to Low)":
            sorted_pairs = sorted(zip(filtered, indices), key=lambda x: x[0].stats.get('consumption', 0), reverse=True)
        elif self.sort_option == "Cost (Low to High)":
            sorted_pairs = sorted(zip(filtered, indices), key=lambda x: x[0].stats.get('cost_per_km', 0))
        else:
            sorted_pairs = list(zip(filtered, indices))
        
        self.filtered_cars = [car for car, _ in sorted_pairs]
        self.car_list_indices = [idx for _, idx in sorted_pairs]
        
        # Reset scroll if needed (will be recalculated in draw_selection_screen with correct list_height)
        # This is just a safety check
        estimated_list_height = self.screen_height - 200
        max_scroll = max(0, len(self.filtered_cars) * 40 - estimated_list_height)
        self.selection_scroll = min(self.selection_scroll, max_scroll)
    
    def handle_selection_click(self, pos: Tuple[int, int]):
        """Handle mouse clicks on selection screen"""
        x, y = pos
        
        # Get component positions (use stored values if available, otherwise use defaults)
        if hasattr(self, 'search_box_rect'):
            search_x, search_y, search_w, search_h = self.search_box_rect
            filter_x, filter_y, filter_w, filter_h = self.filter_dropdown_rect
            sort_x, sort_y, sort_w, sort_h = self.sort_dropdown_rect
        else:
            # Fallback to default positions
            search_x, search_y, search_w, search_h = 20, 90, 480, 25
            filter_x, filter_y, filter_w, filter_h = 520, 90, 100, 25
            sort_x, sort_y, sort_w, sort_h = 630, 90, 150, 25
        
        # Check race type buttons
        if hasattr(self, 'race_type_button_areas'):
            for race_type, button_rect in self.race_type_button_areas.items():
                if button_rect.collidepoint(x, y):
                    self.race_type = race_type
                    return
        
        # Close dropdowns if clicking outside
        dropdown_bounds_x = min(filter_x, sort_x)
        dropdown_bounds_w = max(filter_x + filter_w, sort_x + sort_w) - dropdown_bounds_x
        dropdown_bounds_y = min(filter_y, sort_y)
        dropdown_bounds_h = 115 + 30 * 7 - dropdown_bounds_y
        
        if not (dropdown_bounds_x <= x <= dropdown_bounds_x + dropdown_bounds_w and 
                dropdown_bounds_y <= y <= dropdown_bounds_y + dropdown_bounds_h):
            self.filter_dropdown_open = False
            self.sort_dropdown_open = False
        
        # Unfocus search if clicking outside
        if not (search_x <= x <= search_x + search_w and search_y <= y <= search_y + search_h):
            self.search_focused = False
        
        # Handle endurance distance input click
        if self.race_type == "endurance" and hasattr(self, 'endurance_distance_input_rect'):
            if self.endurance_distance_input_rect.collidepoint(x, y):
                self.endurance_input_focused = True
            else:
                self.endurance_input_focused = False
        
        # Check if click is in search box
        if search_x <= x <= search_x + search_w and search_y <= y <= search_y + search_h:
            # Check if clicked on clear button
            if search_x + search_w - 25 <= x <= search_x + search_w - 5 and self.search_text:
                self.search_text = ""
                self.update_filtered_cars()
            else:
                self.search_focused = True
            return
        
        # Check if click is in filter dropdown button
        if filter_x <= x <= filter_x + filter_w and filter_y <= y <= filter_y + filter_h:
            self.filter_dropdown_open = not self.filter_dropdown_open
            self.sort_dropdown_open = False
            return
        
        # Check if click is in filter dropdown options
        if self.filter_dropdown_open and filter_x <= x <= filter_x + filter_w:
            option_start_y = filter_y + filter_h
            if option_start_y <= y <= option_start_y + 30 * 6:
                option_index = (y - option_start_y) // 30
                categories = ["All Categories", "Getgo", "Car Club", "Econ", "Stand", "Getgo(EV)"]
                if 0 <= option_index < len(categories):
                    self.selected_category = categories[option_index]
                    self.update_filtered_cars()
                    self.filter_dropdown_open = False
            return
        
        # Check if click is in sort dropdown button
        if sort_x <= x <= sort_x + sort_w and sort_y <= y <= sort_y + sort_h:
            self.sort_dropdown_open = not self.sort_dropdown_open
            self.filter_dropdown_open = False
            return
        
        # Check if click is in sort dropdown options
        if self.sort_dropdown_open and sort_x <= x <= sort_x + sort_w:
            option_start_y = sort_y + sort_h
            if option_start_y <= y <= option_start_y + 30 * 7:
                option_index = (y - option_start_y) // 30
                sort_options = ["Name (A-Z)", "Name (Z-A)", "Performance (High to Low)", 
                              "Performance (Low to High)", "Category", "Efficiency (High to Low)", 
                              "Cost (Low to High)"]
                if 0 <= option_index < len(sort_options):
                    self.sort_option = sort_options[option_index]
                    self.update_filtered_cars()
                    self.sort_dropdown_open = False
            return
        
        # Check scrollbar
        list_x = 20
        list_y = 130
        list_width = 480
        list_height = self.screen_height - 230
        scrollbar_x = list_x + list_width
        scrollbar_width = 15
        
        if scrollbar_x <= x <= scrollbar_x + scrollbar_width and list_y <= y <= list_y + list_height:
            # Clicked on scrollbar
            item_height = 40
            max_scroll = max(0, len(self.filtered_cars) * item_height - list_height)
            if max_scroll > 0:
                # Calculate thumb position
                thumb_height = max(20, int((list_height / (len(self.filtered_cars) * item_height)) * list_height))
                thumb_y = list_y + int((self.selection_scroll / max_scroll) * (list_height - thumb_height))
                
                if thumb_y <= y <= thumb_y + thumb_height:
                    # Clicked on thumb - start dragging
                    self.scrollbar_dragging = True
                    self.scrollbar_drag_start_y = y
                    self.scrollbar_drag_start_scroll = self.selection_scroll
                else:
                    # Clicked on scrollbar track - jump to position
                    scroll_ratio = (y - list_y) / list_height
                    self.selection_scroll = int(scroll_ratio * max_scroll)
            return
        
        # Check if click is in car list area
        if list_x <= x <= list_x + list_width and list_y <= y <= list_y + list_height:
            # Calculate which car was clicked
            item_height = 40
            scroll_offset = self.selection_scroll
            clicked_index = (y - list_y + scroll_offset) // item_height
            
            if 0 <= clicked_index < len(self.filtered_cars):
                # Get original index from mapping
                original_index = self.car_list_indices[clicked_index]
                if original_index in self.selection_selected:
                    self.selection_selected.remove(original_index)
                else:
                    self.selection_selected.add(original_index)
            return
        
        # Check scroll buttons (up/down arrows)
        if list_x <= x <= list_x + list_width:
            if list_y - 30 <= y <= list_y:
                # Up arrow
                item_height = 40
                self.selection_scroll = max(0, self.selection_scroll - item_height)
            elif list_y + list_height <= y <= list_y + list_height + 30:
                # Down arrow
                item_height = 40
                max_scroll = max(0, len(self.filtered_cars) * item_height - list_height)
                self.selection_scroll = min(max_scroll, self.selection_scroll + item_height)
    
    def start_race(self):
        """Start a race with selected cars"""
        # Check if endurance mode and need to show tank capacity dialog
        if self.race_type == "endurance" and not self.endurance_tank_input_dialog:
            # Validate distance input
            try:
                distance = float(self.endurance_distance_input) if self.endurance_distance_input else 100.0
                if distance <= 0:
                    return  # Invalid distance
                self.endurance_distance_km = distance
            except ValueError:
                return  # Invalid input
            
            # Show tank capacity dialog
            self.endurance_tank_input_dialog = True
            # Initialize tank inputs with defaults
            for car_idx in self.selection_selected:
                car = self.all_cars[car_idx]
                if car_idx not in self.endurance_tank_inputs:
                    self.endurance_tank_inputs[car_idx] = str(self.get_default_tank_capacity(car.category))
            return
        
        # If we're here and it's endurance mode, we should have tank capacities set
        if self.race_type == "endurance":
            # Validate all cars have tank capacity
            for car_idx in self.selection_selected:
                if car_idx not in self.endurance_tank_inputs:
                    return  # Missing tank capacity
            
            # Parse and store tank capacities
            for car_idx in self.selection_selected:
                try:
                    capacity = float(self.endurance_tank_inputs[car_idx])
                    if capacity <= 0:
                        return  # Invalid capacity
                    self.endurance_tank_capacities[car_idx] = capacity
                except ValueError:
                    return  # Invalid input
        
        selected_indices = list(self.selection_selected)
        self.selected_cars = [self.all_cars[i] for i in selected_indices]
        
        # Reset car positions and assign lanes
        lane_height = 50
        start_y = 150
        for i, car in enumerate(self.selected_cars):
            car.position = [START_X, start_y + i * lane_height]
            car.finished = False
            car.finish_time = 0
            car.race_position = 0
            
            # Initialize endurance mode attributes
            if self.race_type == "endurance":
                car.is_endurance_mode = True
                car.fuel_capacity = self.endurance_tank_capacities[selected_indices[i]]
                car.fuel_level = car.fuel_capacity  # Start with full tank
                car.max_distance_km = self.endurance_distance_km
                car.distance_traveled_km = 0.0
            else:
                car.is_endurance_mode = False
        
        # Close tank input dialog if it was open
        self.endurance_tank_input_dialog = False
        
        self.frame_count = 0
        self.state = "racing"
    
    def update_race(self):
        """Update race state"""
        is_endurance = self.race_type == "endurance"
        
        if is_endurance:
            # Endurance mode: fuel-based race
            # Update all cars (fuel consumption handled in Car.update())
            for car in self.selected_cars:
                if not car.finished:
                    car.update(self.frame_count)
                    # Car.update() handles fuel consumption and marks finished when fuel runs out
                    # Also check if car reached max distance
                    if car.distance_traveled_km >= car.max_distance_km:
                        car.finished = True
                        car.finish_time = self.frame_count
            
            # Race ends when all cars run out of fuel
            all_finished = all(car.finished for car in self.selected_cars)
            if all_finished:
                # Sort by distance traveled (descending)
                finished_cars = sorted(self.selected_cars, key=lambda c: c.distance_traveled_km, reverse=True)
                for i, car in enumerate(finished_cars):
                    car.race_position = i + 1
                self.race_results = finished_cars
                self.state = "results"
        else:
            # Basic mode: original logic
            # Calculate finish line position dynamically
            finish_line_x = min(START_X + RACE_DISTANCE, self.screen_width - 100)
            
            # Update all cars
            for car in self.selected_cars:
                if not car.finished:
                    car.update(self.frame_count)
                    # Check if finished (using dynamic finish line)
                    if car.position[0] >= finish_line_x:
                        car.finished = True
                        car.position[0] = finish_line_x
                        car.finish_time = self.frame_count
            
            # Check if race is complete
            all_finished = all(car.finished for car in self.selected_cars)
            if all_finished:
                # Calculate final positions
                finished_cars = sorted(self.selected_cars, key=lambda c: c.finish_time)
                for i, car in enumerate(finished_cars):
                    car.race_position = i + 1
                self.race_results = finished_cars
                self.state = "results"
    
    def apply_margin_to_components(self, components, margin=(8, 7, 16, 14)):
        """
        Automatically apply margins to a group of components to ensure proper spacing.
        Each component should be a tuple/list: (x, y, width, height) or dict with keys.
        Returns a new list of components with the margin applied.
        
        Args:
            components: List of components, each as (x, y, width, height) or dict
            margin: Tuple of (left_margin, top_margin, width_reduction, height_reduction)
        
        Returns:
            List of adjusted components as (x, y, width, height) tuples
        """
        mx, my, mw, mh = margin
        adjusted = []
        for comp in components:
            if isinstance(comp, dict):
                x, y, width, height = comp.get("x", 0), comp.get("y", 0), comp.get("width", 0), comp.get("height", 0)
            else:
                x, y, width, height = comp
            adjusted.append((
                x + mx,
                y + my,
                max(0, width - mw),  # Ensure width doesn't go negative
                max(0, height - mh)  # Ensure height doesn't go negative
            ))
        return adjusted
    
    def draw_selection_screen(self):
        """Draw car selection screen with search, filter, sort, race type, and scrollbar"""
        self.screen.fill(WHITE)
        
        # Title - smaller, left-aligned
        title_y = 15
        title = self.small_font.render("Car Racing Simulation", True, BLACK)
        self.screen.blit(title, (PADDING, title_y))
        
        # Race Type Selection - compact, top right, same line as title
        if not hasattr(self, "race_type"):
            self.race_type = "basic"
        
        race_type_x = self.screen_width - 240
        race_type_y = title_y
        button_width = 100
        button_height = 25
        button_gap = 10
        
        # Basic Race button
        basic_rect = pygame.Rect(race_type_x, race_type_y, button_width, button_height)
        pygame.draw.rect(self.screen, LIGHT_GRAY if self.race_type == "basic" else WHITE, basic_rect, border_radius=5)
        pygame.draw.rect(self.screen, GREEN if self.race_type == "basic" else DARK_GRAY, basic_rect, 2, border_radius=5)
        basic_label = self.small_font.render("Basic", True, BLACK)
        self.screen.blit(basic_label, (race_type_x + 5, race_type_y + 4))
        
        # Fuel Endurance button
        fuel_rect = pygame.Rect(race_type_x + button_width + button_gap, race_type_y, 120, button_height)
        pygame.draw.rect(self.screen, LIGHT_GRAY if self.race_type == "endurance" else WHITE, fuel_rect, border_radius=5)
        pygame.draw.rect(self.screen, GREEN if self.race_type == "endurance" else DARK_GRAY, fuel_rect, 2, border_radius=5)
        fuel_label = self.small_font.render("Endurance", True, BLACK)
        self.screen.blit(fuel_label, (race_type_x + button_width + button_gap + 5, race_type_y + 4))

        # Store button areas for click handling
        self.race_type_button_areas = {
            "basic": basic_rect,
            "endurance": fuel_rect,
        }

        # Simplified instructions - 2 short lines
        instructions_y = title_y + 30
        instruction_line1 = self.small_font.render("Select 2+ cars to race", True, DARK_GRAY)
        self.screen.blit(instruction_line1, (PADDING, instructions_y))
        
        instruction_line2 = self.small_font.render("Controls: ENTER=Start | ESC=Quit", True, DARK_GRAY)
        self.screen.blit(instruction_line2, (PADDING, instructions_y + 18))
        
        # Endurance mode distance input
        if self.race_type == "endurance":
            distance_input_y = instructions_y + 45
            distance_label = self.small_font.render("Target Distance (km):", True, BLACK)
            self.screen.blit(distance_label, (PADDING, distance_input_y))
            
            # Input box
            input_box_x = PADDING + 150
            input_box_y = distance_input_y
            input_box_width = 100
            input_box_height = 25
            input_box_rect = pygame.Rect(input_box_x, input_box_y, input_box_width, input_box_height)
            
            # Draw input box
            box_color = YELLOW if self.endurance_input_focused else WHITE
            pygame.draw.rect(self.screen, box_color, input_box_rect)
            pygame.draw.rect(self.screen, BLACK, input_box_rect, 2)
            
            # Draw input text
            input_text = self.endurance_distance_input if self.endurance_distance_input else "100"
            input_surface = self.small_font.render(input_text, True, BLACK)
            self.screen.blit(input_surface, (input_box_x + 5, input_box_y + 3))
            
            # Store rect for click detection
            self.endurance_distance_input_rect = input_box_rect
        
        # New container for search/filter/sort with margin/padding background
        # Adjust y position based on whether endurance mode is active
        if self.race_type == "endurance":
            container_y = instructions_y + 75  # More space for distance input
        else:
            container_y = instructions_y + 40  # Normal spacing
        container_x = PADDING
        container_width = min(485, self.screen_width - 2 * PADDING)
        container_height = 38  # Slightly reduced height

        pygame.draw.rect(self.screen, (240, 246, 252), (container_x, container_y, container_width, container_height), border_radius=10)
        pygame.draw.rect(self.screen, DARK_GRAY, (container_x, container_y, container_width, container_height), 1, border_radius=10)

        # Define component positions and sizes
        search_width = 180
        filter_width = 100
        sort_width = 140
        component_height = 25
        component_gap = 10  # Gap between components
        
        # Calculate positions with margins applied
        content_x = container_x + 8
        content_y = container_y + 7
        
        # Define components with their base positions
        components = [
            (content_x, content_y, search_width, component_height),  # Search box
            (content_x + search_width + component_gap, content_y, filter_width, component_height),  # Filter
            (content_x + search_width + component_gap + filter_width + component_gap, content_y, sort_width, component_height),  # Sort
        ]
        
        # Apply margins to ensure no overlapping
        component_margins = (0, 0, 4, 2)  # Small horizontal and vertical spacing
        adjusted_components = self.apply_margin_to_components(components, component_margins)
        
        # Store component positions for click handling
        search_x, search_y, search_w, search_h = adjusted_components[0]
        filter_x, filter_y, filter_w, filter_h = adjusted_components[1]
        sort_x, sort_y, sort_w, sort_h = adjusted_components[2]
        
        self.search_box_rect = (search_x, search_y, search_w, search_h)
        self.filter_dropdown_rect = (filter_x, filter_y, filter_w, filter_h)
        self.sort_dropdown_rect = (sort_x, sort_y, sort_w, sort_h)
        
        # Draw search box, filter, and sort with adjusted positions
        self.draw_search_box(pos=(search_x, search_y), width=search_w, height=search_h)
        self.draw_filter_dropdown(pos=(filter_x, filter_y), width=filter_w, height=filter_h)
        self.draw_sort_dropdown(pos=(sort_x, sort_y), width=sort_w, height=sort_h)
        
        # Scrollable car list area - moved higher, more space
        list_x = PADDING
        list_y = container_y + container_height + SECTION_SPACING
        list_width = min(480, self.screen_width - 2 * PADDING - 20)  # Account for scrollbar
        item_height = 40
        list_height = self.screen_height - list_y - 60  # More space, compact bottom bar
        
        # Draw list background
        list_rect = pygame.Rect(list_x, list_y, list_width, list_height)
        pygame.draw.rect(self.screen, (235, 235, 240), list_rect)
        pygame.draw.rect(self.screen, DARK_GRAY, list_rect, 2)
        
        # Calculate scroll bounds
        max_scroll = max(0, len(self.filtered_cars) * item_height - list_height)
        self.selection_scroll = min(self.selection_scroll, max_scroll)
        self.selection_scroll = max(self.selection_scroll, 0)
        
        # Draw cars from filtered list
        if len(self.filtered_cars) == 0:
            # No results message
            no_results = self.font.render("No cars match your search/filter", True, DARK_GRAY)
            self.screen.blit(no_results, (list_x + 20, list_y + list_height // 2))
        else:
            # Only loop over relevant visible range for performance
            start_index = max(0, self.selection_scroll // item_height)
            end_index = min(len(self.filtered_cars), (self.selection_scroll + list_height) // item_height + 1)
            
            for i in range(start_index, end_index):
                car = self.filtered_cars[i]
                original_index = self.car_list_indices[i]
                y_pos = list_y + (i * item_height) - self.selection_scroll
                
                # Only draw visible items within rect
                if (list_y - item_height) <= y_pos <= (list_y + list_height):
                    # Highlight if selected
                    if original_index in self.selection_selected:
                        highlight_rect = pygame.Rect(list_x, y_pos, list_width, item_height)
                        pygame.draw.rect(self.screen, LIGHT_GRAY, highlight_rect)
                    
                    # Car info
                    car_text = f"{car.name} ({car.category})"
                    car_surface = self.small_font.render(car_text, True, BLACK)
                    self.screen.blit(car_surface, (list_x + 10, y_pos + 10))
                    
                    # Stats
                    stats_text = f"Eff: {car.stats['consumption']:.1f} km/L | Cost: ${car.stats['cost_per_km']:.2f}/km | Perf: {car.performance_score:.2f}"
                    stats_surface = self.small_font.render(stats_text, True, DARK_GRAY)
                    self.screen.blit(stats_surface, (list_x + 10, y_pos + 25))
                    
                    # Selection indicator
                    if original_index in self.selection_selected:
                        check = self.small_font.render("✓", True, GREEN)
                        self.screen.blit(check, (list_x + list_width - 35, y_pos + 10))
        
        # Draw scrollbar
        self.draw_scrollbar(list_x, list_y, list_width, list_height, max_scroll, item_height)
        
        # Draw tank capacity input dialog if endurance mode and dialog is open
        if self.race_type == "endurance" and self.endurance_tank_input_dialog:
            self.draw_tank_capacity_dialog()
        
        # Compact status bar - single line combining all info
        status_y = self.screen_height - 35
        selected_count = len(self.selection_selected)
        race_type_short = "Basic" if self.race_type == "basic" else "Endurance"
        
        # Build status text
        if selected_count >= 2:
            if self.race_type == "endurance" and not self.endurance_tank_input_dialog:
                status_parts = [
                    f"{selected_count} cars selected",
                    f"Race: {race_type_short}",
                    "Ready - Press ENTER to set tank capacities"
                ]
            else:
                status_parts = [
                    f"{selected_count} cars selected",
                    f"Race: {race_type_short}",
                    "Ready - Press ENTER to start"
                ]
            status_color = GREEN
        else:
            status_parts = [
                f"{selected_count} cars selected",
                f"Race: {race_type_short}",
                "Select 2+ cars to race"
            ]
            status_color = RED
        
        status_text = " | ".join(status_parts)
        status_surface = self.small_font.render(status_text, True, status_color)
        self.screen.blit(status_surface, (PADDING, status_y))
    def draw_search_box(self, pos=None, width=None, height=None):
        """Draw search input box"""
        if pos is None:
            search_x = 20
            search_y = 90
        else:
            search_x, search_y = pos
        
        if width is None:
            search_width = 480
        else:
            search_width = width
            
        if height is None:
            search_height = 25
        else:
            search_height = height
        
        # Draw search box background
        search_rect = pygame.Rect(search_x, search_y, search_width, search_height)
        border_color = BLUE if self.search_focused else DARK_GRAY
        pygame.draw.rect(self.screen, WHITE, search_rect)
        pygame.draw.rect(self.screen, border_color, search_rect, 2)
        
        # Draw search text or placeholder
        if self.search_text:
            search_surface = self.small_font.render(self.search_text, True, BLACK)
            self.screen.blit(search_surface, (search_x + 5, search_y + 5))
            
            # Draw clear button (X)
            clear_rect = pygame.Rect(search_x + search_width - 25, search_y + 2, 20, 20)
            pygame.draw.rect(self.screen, LIGHT_GRAY, clear_rect)
            pygame.draw.rect(self.screen, DARK_GRAY, clear_rect, 1)
            x_text = self.small_font.render("×", True, BLACK)
            self.screen.blit(x_text, (search_x + search_width - 20, search_y + 3))
        else:
            placeholder = self.small_font.render("Search cars...", True, GRAY)
            self.screen.blit(placeholder, (search_x + 5, search_y + 5))
    
    def draw_filter_dropdown(self, pos=None, width=None, height=None):
        """Draw category filter dropdown"""
        if pos is None:
            filter_x = 520
            filter_y = 90
        else:
            filter_x, filter_y = pos
        
        if width is None:
            filter_width = 100
        else:
            filter_width = width
            
        if height is None:
            filter_height = 25
        else:
            filter_height = height
        
        # Draw dropdown button
        filter_rect = pygame.Rect(filter_x, filter_y, filter_width, filter_height)
        pygame.draw.rect(self.screen, LIGHT_GRAY, filter_rect)
        pygame.draw.rect(self.screen, DARK_GRAY, filter_rect, 2)
        
        # Draw current selection
        filter_text = self.small_font.render(self.selected_category[:12], True, BLACK)
        self.screen.blit(filter_text, (filter_x + 5, filter_y + 5))
        
        # Draw arrow
        arrow_y = filter_y + filter_height // 2
        pygame.draw.polygon(
            self.screen,
            BLACK,
            [
                (filter_x + filter_width - 15, arrow_y - 3),
                (filter_x + filter_width - 5, arrow_y - 3),
                (filter_x + filter_width - 10, arrow_y + 3),
            ],
        )
        
        # Draw dropdown options if open
        if self.filter_dropdown_open:
            categories = ["All Categories", "Getgo", "Car Club", "Econ", "Stand", "Getgo(EV)"]
            option_height = 30
            dropdown_rect = pygame.Rect(filter_x, filter_y + filter_height, filter_width, len(categories) * option_height)
            pygame.draw.rect(self.screen, WHITE, dropdown_rect)
            pygame.draw.rect(self.screen, DARK_GRAY, dropdown_rect, 2)
            
            for i, category in enumerate(categories):
                option_y = filter_y + filter_height + i * option_height
                option_rect = pygame.Rect(filter_x, option_y, filter_width, option_height)
                
                # Highlight if selected
                if category == self.selected_category:
                    pygame.draw.rect(self.screen, LIGHT_GRAY, option_rect)
                
                # Draw option text
                option_text = self.small_font.render(category[:12], True, BLACK)
                self.screen.blit(option_text, (filter_x + 5, option_y + 5))
    
    def draw_sort_dropdown(self, pos=None, width=None, height=None):
        """Draw sort options dropdown"""
        if pos is None:
            sort_x = 630
            sort_y = 90
        else:
            sort_x, sort_y = pos
        
        if width is None:
            sort_width = 150
        else:
            sort_width = width
            
        if height is None:
            sort_height = 25
        else:
            sort_height = height
        
        # Draw dropdown button
        sort_rect = pygame.Rect(sort_x, sort_y, sort_width, sort_height)
        pygame.draw.rect(self.screen, LIGHT_GRAY, sort_rect)
        pygame.draw.rect(self.screen, DARK_GRAY, sort_rect, 2)
        
        # Draw current selection
        sort_text = self.small_font.render(self.sort_option[:18], True, BLACK)
        self.screen.blit(sort_text, (sort_x + 5, sort_y + 5))
        
        # Draw arrow
        arrow_y = sort_y + sort_height // 2
        pygame.draw.polygon(
            self.screen,
            BLACK,
            [
                (sort_x + sort_width - 15, arrow_y - 3),
                (sort_x + sort_width - 5, arrow_y - 3),
                (sort_x + sort_width - 10, arrow_y + 3),
            ],
        )
        
        # Draw dropdown options if open
        if self.sort_dropdown_open:
            sort_options = ["Name (A-Z)", "Name (Z-A)", "Performance (High to Low)", 
                          "Performance (Low to High)", "Category", "Efficiency (High to Low)", 
                          "Cost (Low to High)"]
            option_height = 30
            dropdown_rect = pygame.Rect(sort_x, sort_y + sort_height, sort_width, len(sort_options) * option_height)
            pygame.draw.rect(self.screen, WHITE, dropdown_rect)
            pygame.draw.rect(self.screen, DARK_GRAY, dropdown_rect, 2)
            
            for i, option in enumerate(sort_options):
                option_y = sort_y + sort_height + i * option_height
                option_rect = pygame.Rect(sort_x, option_y, sort_width, option_height)
                
                # Highlight if selected
                if option == self.sort_option:
                    pygame.draw.rect(self.screen, LIGHT_GRAY, option_rect)
                
                # Draw option text
                option_text = self.small_font.render(option[:20], True, BLACK)
                self.screen.blit(option_text, (sort_x + 5, option_y + 5))
    
    def draw_tank_capacity_dialog(self):
        """Draw tank capacity input dialog for endurance mode"""
        # Dialog dimensions
        dialog_width = 500
        dialog_height = min(400, self.screen_height - 100)
        dialog_x = (self.screen_width - dialog_width) // 2
        dialog_y = (self.screen_height - dialog_height) // 2
        
        # Draw dialog background with semi-transparent overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Draw dialog box
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(self.screen, WHITE, dialog_rect)
        pygame.draw.rect(self.screen, BLACK, dialog_rect, 3)
        
        # Title
        title = self.font.render("Set Tank Capacities (Liters)", True, BLACK)
        title_x = dialog_x + (dialog_width - title.get_width()) // 2
        self.screen.blit(title, (title_x, dialog_y + 15))
        
        # Instructions
        instructions = self.small_font.render("Enter fuel tank capacity for each car:", True, DARK_GRAY)
        self.screen.blit(instructions, (dialog_x + 20, dialog_y + 45))
        
        # Get selected cars
        selected_cars = [(i, self.all_cars[i]) for i in self.selection_selected]
        
        # Draw input fields for each selected car
        input_y = dialog_y + 75
        input_height = 30
        input_spacing = 35
        self.tank_input_rects = {}
        
        for idx, (car_idx, car) in enumerate(selected_cars):
            if input_y + input_height > dialog_y + dialog_height - 60:
                break  # Don't draw beyond dialog
            
            # Car name
            car_name = car.name[:25]  # Truncate if too long
            name_surface = self.small_font.render(f"{car_name}:", True, BLACK)
            self.screen.blit(name_surface, (dialog_x + 20, input_y + 5))
            
            # Input box
            input_box_x = dialog_x + 200
            input_box_width = 100
            input_box_rect = pygame.Rect(input_box_x, input_y, input_box_width, input_height)
            
            # Get default tank capacity based on category
            default_capacity = self.get_default_tank_capacity(car.category)
            if car_idx not in self.endurance_tank_inputs:
                self.endurance_tank_inputs[car_idx] = str(default_capacity)
            
            # Draw input box
            box_color = YELLOW if self.endurance_tank_input_focused == car_idx else WHITE
            pygame.draw.rect(self.screen, box_color, input_box_rect)
            pygame.draw.rect(self.screen, BLACK, input_box_rect, 2)
            
            # Draw input text
            input_text = self.endurance_tank_inputs.get(car_idx, str(default_capacity))
            input_surface = self.small_font.render(input_text, True, BLACK)
            self.screen.blit(input_surface, (input_box_x + 5, input_y + 5))
            
            # Liter label
            liter_label = self.small_font.render("L", True, BLACK)
            self.screen.blit(liter_label, (input_box_x + input_box_width + 5, input_y + 5))
            
            # Store rect for click detection
            self.tank_input_rects[car_idx] = input_box_rect
            
            input_y += input_spacing
        
        # Confirm button
        button_y = dialog_y + dialog_height - 50
        button_width = 120
        button_height = 35
        button_x = dialog_x + (dialog_width - button_width) // 2
        confirm_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        pygame.draw.rect(self.screen, GREEN, confirm_rect)
        pygame.draw.rect(self.screen, BLACK, confirm_rect, 2)
        confirm_text = self.small_font.render("Confirm", True, BLACK)
        confirm_text_x = button_x + (button_width - confirm_text.get_width()) // 2
        self.screen.blit(confirm_text, (confirm_text_x, button_y + 8))
        
        # Store confirm button rect
        self.tank_dialog_confirm_rect = confirm_rect
    
    def get_default_tank_capacity(self, category: str) -> float:
        """Get default tank capacity based on car category"""
        defaults = {
            "Econ": 40.0,
            "Stand": 40.0,
            "Getgo": 45.0,
            "Car Club": 45.0,
            "Getgo(EV)": 50.0,
        }
        return defaults.get(category, 45.0)
    
    def draw_scrollbar(self, list_x, list_y, list_width, list_height, max_scroll, item_height):
        """Draw visual scrollbar"""
        scrollbar_x = list_x + list_width
        scrollbar_width = 15
        
        # Draw scrollbar track
        track_rect = pygame.Rect(scrollbar_x, list_y, scrollbar_width, list_height)
        pygame.draw.rect(self.screen, (200, 200, 200), track_rect)
        pygame.draw.rect(self.screen, DARK_GRAY, track_rect, 1)
        
        if max_scroll > 0 and len(self.filtered_cars) > 0:
            # Calculate thumb size and position
            total_height = len(self.filtered_cars) * item_height
            thumb_height = max(20, int((list_height / total_height) * list_height))
            thumb_y = list_y + int((self.selection_scroll / max_scroll) * (list_height - thumb_height))
            
            # Draw thumb
            thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)
            thumb_color = (100, 100, 100) if self.scrollbar_dragging else (150, 150, 150)
            pygame.draw.rect(self.screen, thumb_color, thumb_rect)
            pygame.draw.rect(self.screen, BLACK, thumb_rect, 1)
    def draw_race_screen(self):
        """Draw race screen"""
        self.screen.fill(WHITE)
        
        is_endurance = self.race_type == "endurance"
        
        # Draw track/road
        road_rect = pygame.Rect(0, 100, self.screen_width, self.screen_height - 200)
        pygame.draw.rect(self.screen, DARK_GRAY, road_rect)
        
        # Draw lane markers
        for car in self.selected_cars:
            lane_y = car.position[1]
            # Draw dashed line
            for x in range(0, self.screen_width, 20):
                pygame.draw.line(self.screen, YELLOW, (x, lane_y + 30), (x + 10, lane_y + 30), 2)
        
        # Draw finish line (calculate dynamically)
        if is_endurance:
            # For endurance: convert max_distance_km to pixels
            if len(self.selected_cars) > 0 and self.selected_cars[0].max_distance_km > 0:
                max_distance_pixels = self.selected_cars[0].max_distance_km * PIXELS_PER_KM
                finish_line_x = min(START_X + max_distance_pixels, self.screen_width - 100)
            else:
                finish_line_x = min(START_X + RACE_DISTANCE, self.screen_width - 100)
        else:
            # Basic mode: use fixed distance
            finish_line_x = min(START_X + RACE_DISTANCE, self.screen_width - 100)
        
        finish_line_y1 = 100
        finish_line_y2 = self.screen_height - 100
        for y in range(finish_line_y1, finish_line_y2, 20):
            pygame.draw.line(self.screen, BLACK, (finish_line_x, y), (finish_line_x, y + 10), 3)
        
        finish_text = self.font.render("FINISH", True, BLACK)
        self.screen.blit(finish_text, (finish_line_x + 10, finish_line_y1))
        
        # Draw cars
        for car in self.selected_cars:
            car.draw(self.screen, car.position[1], self.small_font)
        
        # Draw stats panel (right side)
        panel_x = min(600, self.screen_width - 250)
        panel_y = 100
        panel_width = self.screen_width - panel_x - 20
        panel_height = self.screen_height - 200
        
        # Panel background
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(self.screen, LIGHT_GRAY, panel_rect)
        pygame.draw.rect(self.screen, BLACK, panel_rect, 2)
        
        # Panel title
        panel_title = self.font.render("Race Stats", True, BLACK)
        self.screen.blit(panel_title, (panel_x + 10, panel_y + 10))
        
        # Car stats
        stats_y = panel_y + 50
        for i, car in enumerate(self.selected_cars):
            if stats_y > panel_y + panel_height - 30:
                break
            
            # Car name and progress
            progress = car.get_progress()
            car_info = f"{i+1}. {car.name[:20]}"
            car_surface = self.small_font.render(car_info, True, BLACK)
            self.screen.blit(car_surface, (panel_x + 10, stats_y))
            
            # Progress bar
            bar_width = panel_width - 40
            bar_height = 15
            bar_x = panel_x + 10
            bar_y = stats_y + 20
            
            # Background
            pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, bar_width, bar_height))
            # Progress
            progress_width = int((progress / 100) * bar_width)
            pygame.draw.rect(self.screen, car.color, (bar_x, bar_y, progress_width, bar_height))
            pygame.draw.rect(self.screen, BLACK, (bar_x, bar_y, bar_width, bar_height), 1)
            
            # Progress text
            progress_text = self.small_font.render(f"{progress:.1f}%", True, BLACK)
            self.screen.blit(progress_text, (bar_x + bar_width + 5, bar_y))
            
            stats_y += 60
        
        # Race info
        info_y = self.screen_height - 80
        if is_endurance:
            race_type_text = self.small_font.render("Endurance Race", True, BLACK)
            self.screen.blit(race_type_text, (20, info_y))
            
            finished_count = sum(1 for car in self.selected_cars if car.finished)
            finished_text = self.small_font.render(f"Finished: {finished_count}/{len(self.selected_cars)}", True, BLACK)
            self.screen.blit(finished_text, (20, info_y + 20))
        else:
            frame_text = self.small_font.render(f"Frame: {self.frame_count}", True, BLACK)
            self.screen.blit(frame_text, (20, info_y))
            
            finished_count = sum(1 for car in self.selected_cars if car.finished)
            finished_text = self.small_font.render(f"Finished: {finished_count}/{len(self.selected_cars)}", True, BLACK)
            self.screen.blit(finished_text, (20, info_y + 20))
    
    
    
    def draw_results_screen(self):
        """Draw results screen"""
        self.screen.fill(WHITE)
        
        is_endurance = self.race_type == "endurance"
        
        # Title
        title_text = "Endurance Race Results" if is_endurance else "Race Results"
        title = self.font.render(title_text, True, BLACK)
        self.screen.blit(title, (self.screen_width // 2 - 100, 20))
        
        # Results table
        table_y = 100
        header_y = table_y
        
        # Headers (different for endurance vs basic)
        if is_endurance:
            headers = ["Position", "Car Name", "Distance (km)", "Fuel Used (L)", "Efficiency"]
        else:
            headers = ["Position", "Car Name", "Category", "Performance", "Time"]
        
        header_x = 50
        for header in headers:
            header_surface = self.font.render(header, True, BLACK)
            self.screen.blit(header_surface, (header_x, header_y))
            header_x += 200
        
        # Results
        results_y = table_y + 50
        for car in self.race_results:
            # Position
            pos_text = f"{car.race_position}"
            pos_surface = self.font.render(pos_text, True, BLACK)
            self.screen.blit(pos_surface, (50, results_y))
            
            # Car name
            name_surface = self.font.render(car.name[:25], True, car.color)
            self.screen.blit(name_surface, (250, results_y))
            
            if is_endurance:
                # Distance traveled
                distance_text = f"{car.distance_traveled_km:.2f}"
                distance_surface = self.font.render(distance_text, True, BLACK)
                self.screen.blit(distance_surface, (450, results_y))
                
                # Fuel consumed
                fuel_consumed = car.fuel_capacity - car.fuel_level
                fuel_text = f"{fuel_consumed:.2f}"
                fuel_surface = self.font.render(fuel_text, True, BLACK)
                self.screen.blit(fuel_surface, (650, results_y))
                
                # Efficiency (km per liter)
                if fuel_consumed > 0:
                    efficiency = car.distance_traveled_km / fuel_consumed
                    eff_text = f"{efficiency:.2f} km/L"
                else:
                    eff_text = "N/A"
                eff_surface = self.font.render(eff_text, True, BLACK)
                self.screen.blit(eff_surface, (850, results_y))
            else:
                # Category
                cat_surface = self.font.render(car.category, True, BLACK)
                self.screen.blit(cat_surface, (450, results_y))
                
                # Performance score
                perf_text = f"{car.performance_score:.2f}"
                perf_surface = self.font.render(perf_text, True, BLACK)
                self.screen.blit(perf_surface, (650, results_y))
                
                # Finish time
                time_text = f"{car.finish_time / FPS:.2f}s"
                time_surface = self.font.render(time_text, True, BLACK)
                self.screen.blit(time_surface, (850, results_y))
            
            results_y += 40
        
        # Instructions
        instructions = self.small_font.render(
            "Press R to race again, ESC to return to selection", 
            True, DARK_GRAY
        )
        self.screen.blit(instructions, (self.screen_width // 2 - 200, self.screen_height - 40))


def main():
    """Main entry point"""
    try:
        simulation = CarRacingSimulation()
        simulation.run()
    except Exception as e:
        print(f"Error running simulation: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()


if __name__ == "__main__":
    main()
