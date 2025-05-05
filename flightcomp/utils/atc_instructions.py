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
        # Base instructions that all pilots need
        instructions = {
            # Clearances
            "takeoff": {
                "instruction": "Cleared for takeoff, runway {runway}, wind {wind_direction} at {wind_speed} knots",
                "readback": "Cleared for takeoff, runway {runway}, {callsign}",
                "explanation": "Authorization to take off from specified runway with wind information",
                "parameters": ["runway", "callsign", "wind_direction", "wind_speed"]
            },
            "landing": {
                "instruction": "Cleared to land, runway {runway}, wind {wind_direction} at {wind_speed} knots",
                "readback": "Cleared to land, runway {runway}, {callsign}",
                "explanation": "Authorization to land on specified runway with wind information",
                "parameters": ["runway", "callsign", "wind_direction", "wind_speed"]
            },
            "initial_clearance": {
                "instruction": "{callsign} is cleared to {destination} airport via {route}, maintain {altitude}, expect {cruising_altitude} {time_frame}, departure frequency {frequency}, squawk {squawk}",
                "readback": "Cleared to {destination} via {route}, maintain {altitude}, expect {cruising_altitude} {time_frame}, departure frequency {frequency}, squawk {squawk}, {callsign}",
                "explanation": "Initial IFR clearance with routing, altitude, and transponder code",
                "parameters": ["callsign", "destination", "route", "altitude", "cruising_altitude", "time_frame", "frequency", "squawk"]
            },
            
            # Instructions
            "turn_heading": {
                "instruction": "Turn {direction} heading {heading} {reason}",
                "readback": "Turn {direction} heading {heading}, {callsign}",
                "explanation": "Instruction to turn to a specific magnetic heading",
                "parameters": ["direction", "heading", "callsign", "reason"]
            },
            "climb_descend": {
                "instruction": "{climb_descend} and maintain {altitude} {restriction}",
                "readback": "{climb_descend} and maintain {altitude}, {callsign}",
                "explanation": "Instruction to change altitude to a specific value",
                "parameters": ["climb_descend", "altitude", "callsign", "restriction"]
            },
            "contact": {
                "instruction": "Contact {facility} on {frequency} {additional_info}",
                "readback": "Contact {facility} on {frequency}, {callsign}",
                "explanation": "Instruction to change radio frequency and contact a different ATC facility",
                "parameters": ["facility", "frequency", "callsign", "additional_info"]
            },
            
            # Traffic advisories
            "traffic_advisory": {
                "instruction": "Traffic, {position} o'clock, {distance} miles, {altitude}, {aircraft_type}, {movement}",
                "readback": "Looking for traffic, {callsign}",
                "alternative_readback": "Traffic in sight, {callsign}",
                "explanation": "Information about nearby traffic",
                "parameters": ["position", "distance", "altitude", "aircraft_type", "callsign", "movement"]
            },
            
            # Taxi Instructions
            "taxi": {
                "instruction": "Taxi to runway {runway} via {taxiways}, {hold_short}",
                "readback": "Taxi to runway {runway} via {taxiways}, {hold_short}, {callsign}",
                "explanation": "Instructions for taxiing to a runway",
                "parameters": ["runway", "taxiways", "callsign", "hold_short"]
            },
            
            # Line Up and Wait
            "lineup_wait": {
                "instruction": "Line up and wait runway {runway} {additional_info}",
                "readback": "Line up and wait runway {runway}, {callsign}",
                "explanation": "Instruction to enter the runway and wait without taking off",
                "parameters": ["runway", "callsign", "additional_info"]
            },
            
            # Position and Hold (older phraseology)
            "position_hold": {
                "instruction": "Position and hold runway {runway}",
                "readback": "Position and hold runway {runway}, {callsign}",
                "explanation": "Older phraseology for 'Line up and wait'",
                "parameters": ["runway", "callsign"]
            },
            
            # Altimeter Setting
            "altimeter": {
                "instruction": "{location} altimeter {setting}",
                "readback": "Altimeter {setting}, {callsign}",
                "explanation": "Information about current altimeter setting",
                "parameters": ["location", "setting", "callsign"]
            },
            
            # VFR Flight Following
            "flight_following": {
                "instruction": "Radar contact, {altitude}, squawk {squawk}",
                "readback": "Squawk {squawk}, {callsign}",
                "explanation": "Confirmation of radar contact for VFR flight following",
                "parameters": ["altitude", "squawk", "callsign"]
            }
        }
        
        # Add more complex instructions for experienced pilots
        if self.experience_level in ["intermediate", "advanced"]:
            instructions.update({
                "hold": {
                    "instruction": "Hold {direction} of {fix} on the {radial} radial, {leg_length} mile legs, {direction_turn} turns, expect further clearance at {expect_time}",
                    "readback": "Hold {direction} of {fix} on the {radial} radial, {leg_length} mile legs, {direction_turn} turns, expect further clearance at {expect_time}, {callsign}",
                    "explanation": "Instruction to enter and maintain a holding pattern",
                    "parameters": ["direction", "fix", "radial", "leg_length", "direction_turn", "expect_time", "callsign"]
                },
                "approach_clearance": {
                    "instruction": "Cleared {approach_type} approach runway {runway}, maintain {altitude} until established on the {segment}",
                    "readback": "Cleared {approach_type} approach runway {runway}, maintain {altitude} until established on the {segment}, {callsign}",
                    "explanation": "Clearance to conduct a specific approach to a runway",
                    "parameters": ["approach_type", "runway", "altitude", "segment", "callsign"]
                },
                "missed_approach": {
                    "instruction": "Execute missed approach, climb and maintain {altitude}, {instructions}",
                    "readback": "Execute missed approach, climb and maintain {altitude}, {callsign}",
                    "explanation": "Instructions for missed approach procedure",
                    "parameters": ["altitude", "instructions", "callsign"]
                },
                "sidestep": {
                    "instruction": "Cleared to sidestep to runway {runway}",
                    "readback": "Cleared to sidestep to runway {runway}, {callsign}",
                    "explanation": "Instruction to switch to a parallel runway during final approach",
                    "parameters": ["runway", "callsign"]
                },
                "circling_approach": {
                    "instruction": "Circle {direction} for runway {runway}",
                    "readback": "Circle {direction} for runway {runway}, {callsign}",
                    "explanation": "Instruction to circle to land on a different runway",
                    "parameters": ["direction", "runway", "callsign"]
                }
            })
        
        # Add jet-specific instructions for jet aircraft
        if self.aircraft_type in ["jet", "turboprop"]:
            instructions.update({
                "speed_restriction": {
                    "instruction": "Maintain {speed} knots {restriction}",
                    "readback": "Maintain {speed} knots, {callsign}",
                    "explanation": "Instruction to maintain a specific airspeed",
                    "parameters": ["speed", "callsign", "restriction"]
                },
                "climb_rate": {
                    "instruction": "Climb at {rate} feet per minute {reason}",
                    "readback": "Climb at {rate} feet per minute, {callsign}",
                    "explanation": "Instruction to climb at a specific vertical speed",
                    "parameters": ["rate", "callsign", "reason"]
                },
                "crossing_restriction": {
                    "instruction": "Cross {fix} at {altitude} and {speed} knots",
                    "readback": "Cross {fix} at {altitude} and {speed} knots, {callsign}",
                    "explanation": "Instruction to cross a fix at a specific altitude and speed",
                    "parameters": ["fix", "altitude", "speed", "callsign"]
                },
                "expect_runway": {
                    "instruction": "Expect runway {runway}, {extra_info}",
                    "readback": "Expect runway {runway}, {callsign}",
                    "explanation": "Information about expected landing runway",
                    "parameters": ["runway", "callsign", "extra_info"]
                },
                "descend_via": {
                    "instruction": "Descend via the {arrival} arrival",
                    "readback": "Descend via the {arrival} arrival, {callsign}",
                    "explanation": "Instruction to descend according to an arrival procedure",
                    "parameters": ["arrival", "callsign"]
                }
            })
            
        return instructions
    
    def get_instruction(self, instruction_type):
        """Get an ATC instruction by type"""
        if instruction_type in self.instructions_db:
            return self.instructions_db[instruction_type]
        return None
    
    def get_readback(self, instruction_type, **kwargs):
        """Generate a readback for a specific instruction with variable substitution"""
        if instruction_type in self.instructions_db:
            instruction_data = self.instructions_db[instruction_type]
            try:
                if "alternative_readback" in instruction_data and kwargs.get("traffic_in_sight", False):
                    return instruction_data["alternative_readback"].format(**kwargs)
                return instruction_data["readback"].format(**kwargs)
            except KeyError as e:
                return f"Error: Missing parameter {e} for readback"
        return None
    
    def get_all_instruction_types(self):
        """Get a list of all available instruction types"""
        return list(self.instructions_db.keys())
    
    def get_parameters_for_instruction(self, instruction_type):
        """Get the required parameters for a specific instruction type"""
        if instruction_type in self.instructions_db and "parameters" in self.instructions_db[instruction_type]:
            return self.instructions_db[instruction_type]["parameters"]
        return []


def format_readback_example(instruction_type, instruction_obj, **kwargs):
    """Format an example with both the instruction and proper readback"""
    instr = instruction_obj.instructions_db[instruction_type]
    
    try:
        atc_msg = f"ATC: {instr['instruction'].format(**kwargs)}"
        pilot_msg = f"YOU: {instr['readback'].format(**kwargs)}"
        return f"{atc_msg}\n{pilot_msg}\n"
    except KeyError as e:
        return f"Error: Missing parameter {e} for example" 