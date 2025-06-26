"""
ATC Instructions Module
Contains common ATC instructions and proper readback formats
"""

class ATCInstructions:
    def __init__(self, experience_level="beginner", aircraft_type="single_engine"):
        self.experience_level = experience_level
        self.aircraft_type = aircraft_type
        self.instructions_db = self._load_instructions()
        
    def _load_instructions(self):
        """Load appropriate instructions based on experience and aircraft type"""
        instructions = {
            "Ground": {
                "Taxi to Runway": {
                    "instruction": "{callsign}, taxi to runway {runway} via {taxiways}, hold short of runway {runway}",
                    "readback": "Taxi to runway {runway} via {taxiways}, hold short runway {runway}, {callsign}",
                    "explanation": "Authorization to move the aircraft to a specified runway.",
                    "parameters": ["callsign", "runway", "taxiways"]
                },
                "Line Up and Wait": {
                    "instruction": "{callsign}, runway {runway}, line up and wait",
                    "readback": "Runway {runway}, line up and wait, {callsign}",
                    "explanation": "Instruction to enter the runway and await takeoff clearance.",
                    "parameters": ["callsign", "runway"]
                },
                "Position and Hold": {
                    "instruction": "{callsign}, runway {runway}, position and hold",
                    "readback": "Position and hold runway {runway}, {callsign}",
                    "explanation": "Older phraseology for 'Line Up and Wait'.",
                    "parameters": ["callsign", "runway"]
                },
            },
            "Departure": {
                "Cleared for Takeoff": {
                    "instruction": "{callsign}, runway {runway}, wind {wind_direction} at {wind_speed} knots, cleared for takeoff",
                    "readback": "Runway {runway}, cleared for takeoff, {callsign}",
                    "explanation": "Authorization to take off from the specified runway.",
                    "parameters": ["callsign", "runway", "wind_direction", "wind_speed"]
                },
                "Initial Clearance": {
                    "instruction": "{callsign}, cleared to {destination} airport as filed, maintain {altitude}, expect {cruising_altitude} one zero minutes after departure. Departure frequency is {frequency}, squawk {squawk}",
                    "readback": "Cleared to {destination} as filed, maintain {altitude}, expect {cruising_altitude} one zero minutes after departure, departure on {frequency}, squawk {squawk}, {callsign}",
                    "explanation": "Standard IFR clearance format.",
                    "parameters": ["callsign", "destination", "altitude", "cruising_altitude", "frequency", "squawk"]
                },
            },
            "En-route": {
                "Turn to Heading": {
                    "instruction": "{callsign}, turn {direction} heading {heading}",
                    "readback": "Turn {direction} heading {heading}, {callsign}",
                    "explanation": "Instruction to turn to a specific magnetic heading.",
                    "parameters": ["callsign", "direction", "heading"]
                },
                "Climb and Maintain": {
                    "instruction": "{callsign}, climb and maintain {altitude}",
                    "readback": "Climb and maintain {altitude}, {callsign}",
                    "explanation": "Instruction to climb to and maintain a specific altitude.",
                    "parameters": ["callsign", "altitude"]
                },
                "Descend and Maintain": {
                    "instruction": "{callsign}, descend and maintain {altitude}",
                    "readback": "Descend and maintain {altitude}, {callsign}",
                    "explanation": "Instruction to descend to and maintain a specific altitude.",
                    "parameters": ["callsign", "altitude"]
                },
                "Contact": {
                    "instruction": "{callsign}, contact {facility} on {frequency}",
                    "readback": "Contact {facility} on {frequency}, {callsign}",
                    "explanation": "Instruction to switch to a different ATC frequency.",
                    "parameters": ["callsign", "facility", "frequency"]
                },
                "Traffic Advisory": {
                    "instruction": "{callsign}, traffic, {clock_position} o'clock, {distance} miles, {movement}, a {aircraft_type} at {altitude}",
                    "readback": "Looking for traffic, {callsign}",
                    "alternative_readback": "Traffic in sight, {callsign}",
                    "explanation": "Provides information about nearby traffic.",
                    "parameters": ["callsign", "clock_position", "distance", "movement", "aircraft_type", "altitude"]
                },
                "Altimeter": {
                    "instruction": "{callsign}, {location} altimeter {setting}",
                    "readback": "Altimeter {setting}, {callsign}",
                    "explanation": "Provides the current barometric pressure.",
                    "parameters": ["callsign", "location", "setting"]
                },
                "Flight Following": {
                    "instruction": "{callsign}, radar contact at {altitude}, squawk {squawk}",
                    "readback": "Squawk {squawk}, {callsign}",
                    "explanation": "Confirmation of radar contact for VFR flight, including altitude.",
                    "parameters": ["callsign", "altitude", "squawk"]
                }
            },
            "Arrival": {
                "Cleared to Land": {
                    "instruction": "{callsign}, runway {runway}, wind {wind_direction} at {wind_speed} knots, cleared to land",
                    "readback": "Runway {runway}, cleared to land, {callsign}",
                    "explanation": "Authorization to land on the specified runway.",
                    "parameters": ["callsign", "runway", "wind_direction", "wind_speed"]
                }
            },
            "Advanced": {}
        }

        if self.experience_level in ["intermediate", "advanced"]:
            instructions["Advanced"].update({
                "Hold": {
                    "instruction": "{callsign}, hold {direction} of {fix} on the {radial} radial, {leg_length} mile legs, {turn_direction} turns, expect further clearance at {expect_time}",
                    "readback": "Hold {direction} of {fix} on the {radial} radial, {leg_length} mile legs, {turn_direction} turns, expect further clearance at {expect_time}, {callsign}",
                    "explanation": "Instruction to fly a holding pattern at a specific fix.",
                    "parameters": ["callsign", "direction", "fix", "radial", "leg_length", "turn_direction", "expect_time"]
                },
                "Approach Clearance": {
                    "instruction": "{callsign}, you are {distance} miles from {fix}, turn {direction} heading {heading}, maintain {altitude} until established on the localizer, cleared {approach_type} runway {runway} approach",
                    "readback": "Cleared {approach_type} runway {runway} approach, {callsign}",
                    "explanation": "Authorization to fly an instrument approach.",
                    "parameters": ["callsign", "distance", "fix", "direction", "heading", "altitude", "approach_type", "runway"]
                },
                "Missed Approach": {
                    "instruction": "{callsign}, execute missed approach, climb and maintain {altitude}, {instructions}",
                    "readback": "Execute missed approach, climb and maintain {altitude}, {callsign}",
                    "explanation": "Instructions to follow if the landing cannot be completed.",
                    "parameters": ["callsign", "altitude", "instructions"]
                },
                "Sidestep": {
                    "instruction": "{callsign}, cleared to sidestep to runway {runway}",
                    "readback": "Cleared to sidestep to runway {runway}, {callsign}",
                    "explanation": "Instruction to land on a parallel runway.",
                    "parameters": ["callsign", "runway"]
                },
                "Circling Approach": {
                    "instruction": "{callsign}, circle {direction} for runway {runway}",
                    "readback": "Circle {direction} for runway {runway}, {callsign}",
                    "explanation": "Authorization to circle the airport to land on a different runway.",
                    "parameters": ["callsign", "direction", "runway"]
                }
            })

        if self.aircraft_type in ["jet", "turboprop"]:
            instructions["Advanced"].update({
                "Speed Restriction": {
                    "instruction": "{callsign}, maintain {speed} knots or greater",
                    "readback": "Maintain {speed} knots or greater, {callsign}",
                    "explanation": "Instruction to maintain a specific airspeed.",
                    "parameters": ["callsign", "speed"]
                },
                "Climb Rate": {
                    "instruction": "{callsign}, climb at {rate} feet per minute {reason}",
                    "readback": "Climb at {rate} feet per minute {reason}, {callsign}",
                    "explanation": "Instruction to maintain a specific vertical speed with optional reason.",
                    "parameters": ["callsign", "rate", "reason"]
                },
                "Crossing Restriction": {
                    "instruction": "{callsign}, cross {fix} at or above {altitude}, maintain {speed} knots",
                    "readback": "Cross {fix} at or above {altitude}, maintain {speed} knots, {callsign}",
                    "explanation": "Instruction to cross a waypoint at a specific altitude and speed.",
                    "parameters": ["callsign", "fix", "altitude", "speed"]
                },
                "Expect Runway": {
                    "instruction": "{callsign}, expect runway {runway}, {extra_info}",
                    "readback": "Expect runway {runway}, {callsign}",
                    "explanation": "Advisory about the expected landing runway.",
                    "parameters": ["callsign", "runway", "extra_info"]
                },
                "Descend Via": {
                    "instruction": "{callsign}, descend via the {arrival_name} arrival",
                    "readback": "Descend via the {arrival_name} arrival, {callsign}",
                    "explanation": "Instruction to follow a published STAR arrival route.",
                    "parameters": ["callsign", "arrival_name"]
                }
            })
            
        return instructions
    
    def get_instruction(self, instruction_name):
        """Get an ATC instruction by its user-friendly name"""
        for category in self.instructions_db.values():
            if instruction_name in category:
                return category[instruction_name]
        return None
    
    def get_readback(self, instruction_name, **kwargs):
        """Generate a readback for a specific instruction with variable substitution"""
        instruction_data = self.get_instruction(instruction_name)
        if instruction_data:
            try:
                if "alternative_readback" in instruction_data and kwargs.get("traffic_in_sight", False):
                    return instruction_data["alternative_readback"].format(**kwargs)
                return instruction_data["readback"].format(**kwargs)
            except KeyError as e:
                return f"Error: Missing parameter {e} for readback"
        return None
    
    def get_all_instruction_types(self):
        """Get a list of all available instruction types with separators"""
        instruction_list = []
        for category_name, instructions in self.instructions_db.items():
            if instructions: # Only add separator if category is not empty
                instruction_list.append(f"--- {category_name.upper()} ---")
                instruction_list.extend(list(instructions.keys()))
        return instruction_list
    
    def get_parameters_for_instruction(self, instruction_name):
        """Get the required parameters for a specific instruction type"""
        instruction_data = self.get_instruction(instruction_name)
        if instruction_data and "parameters" in instruction_data:
            return instruction_data["parameters"]
        return []

def format_readback_example(instruction_name, instruction_obj, **kwargs):
    """Format an example with both the instruction and proper readback"""
    instr = instruction_obj.get_instruction(instruction_name)
    if not instr:
        return f"Error: Instruction '{instruction_name}' not found."
    
    try:
        atc_msg = f"ATC: {instr['instruction'].format(**kwargs)}"
        pilot_msg = f"YOU: {instr['readback'].format(**kwargs)}"
        return f"{atc_msg}\n{pilot_msg}\n"
    except KeyError as e:
        return f"Error: Missing parameter {e} for example" 