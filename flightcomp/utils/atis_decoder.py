"""
ATIS Decoder Module
Parses and formats ATIS information for easier readability
"""
import re
from datetime import datetime

class ATISDecoder:
    def __init__(self, experience_level="beginner"):
        self.experience_level = experience_level
        
    def decode_atis(self, raw_atis):
        """Decode raw ATIS text into a structured format"""
        # Clean up input
        raw_atis = raw_atis.strip().upper()
        
        # Parse the ATIS components
        result = {
            "airport": self._extract_airport(raw_atis),
            "information": self._extract_information_code(raw_atis),
            "time": self._extract_time(raw_atis),
            "runway_info": self._extract_runway_info(raw_atis),
            "weather": self._extract_weather(raw_atis),
            "altimeter": self._extract_altimeter(raw_atis),
            "remarks": self._extract_remarks(raw_atis),
            "frequency": self._extract_frequency(raw_atis)
        }
        
        return result
    
    def format_decoded_atis(self, decoded_atis, verbose=True):
        """Format decoded ATIS for display, with verbosity level based on experience"""
        sections = []
        
        # Airport and Information code
        header = f"{decoded_atis['airport']} INFORMATION {decoded_atis['information']}"
        sections.append(header)
        
        # Time
        if decoded_atis['time']:
            sections.append(f"Time: {decoded_atis['time']}")
        
        # Runway information
        if decoded_atis['runway_info']:
            sections.append(f"Runway: {decoded_atis['runway_info']}")
        
        # Weather information
        if decoded_atis['weather']:
            weather = decoded_atis['weather']
            if verbose:
                sections.append("Weather:")
                for key, value in weather.items():
                    if value:
                        sections.append(f"  {key.capitalize()}: {value}")
            else:
                weather_str = []
                if weather.get('visibility'): 
                    weather_str.append(f"Vis {weather['visibility']}")
                if weather.get('wind'): 
                    weather_str.append(f"Wind {weather['wind']}")
                if weather.get('clouds'): 
                    weather_str.append(f"Clouds {weather['clouds']}")
                if weather.get('temperature'): 
                    weather_str.append(f"Temp {weather['temperature']}")
                sections.append("Weather: " + ", ".join(weather_str))
        
        # Altimeter
        if decoded_atis['altimeter']:
            sections.append(f"Altimeter: {decoded_atis['altimeter']}")
        
        # Frequency for initial contact
        if decoded_atis['frequency']:
            sections.append(f"Contact: {decoded_atis['frequency']}")
        
        # Remarks
        if decoded_atis['remarks']:
            sections.append(f"Remarks: {decoded_atis['remarks']}")
        
        return "\n".join(sections)
    
    def _extract_airport(self, raw_atis):
        """Extract airport identifier from ATIS"""
        # Look for common airport identifier patterns (3-4 letter codes)
        airport_match = re.search(r'\b([A-Z]{3,4})\b', raw_atis[:30])
        if airport_match:
            return airport_match.group(1)
        return "Unknown"
    
    def _extract_information_code(self, raw_atis):
        """Extract ATIS information code (letter)"""
        info_match = re.search(r'INFORMATION\s+([A-Z])\b', raw_atis)
        if info_match:
            return info_match.group(1)
        return "Unknown"
    
    def _extract_time(self, raw_atis):
        """Extract time from ATIS"""
        # Look for time format NNNNZ (e.g., 1430Z)
        time_match = re.search(r'\b(\d{4})Z\b', raw_atis)
        if time_match:
            time_str = time_match.group(1)
            try:
                hour = int(time_str[:2])
                minute = int(time_str[2:])
                return f"{hour:02d}:{minute:02d}Z"
            except ValueError:
                return time_str + "Z"
        return ""
    
    def _extract_runway_info(self, raw_atis):
        """Extract runway information from ATIS"""
        # Look for runway in use
        runway_match = re.search(r'RUNWAY\s+IN\s+USE\s+(\d{1,2}[LCR]?(?:\s+AND\s+\d{1,2}[LCR]?)*)', raw_atis)
        if not runway_match:
            # Alternative pattern
            runway_match = re.search(r'LANDING\s+AND\s+DEPARTING\s+RUNWAY\s+(\d{1,2}[LCR]?(?:\s+AND\s+\d{1,2}[LCR]?)*)', raw_atis)
        if not runway_match:
            # Try to find just runway numbers
            runway_match = re.search(r'RUNWAY\s+(\d{1,2}[LCR]?(?:\s+AND\s+\d{1,2}[LCR]?)*)', raw_atis)
            
        if runway_match:
            return runway_match.group(1)
        return ""
    
    def _extract_weather(self, raw_atis):
        """Extract weather information from ATIS"""
        weather = {}
        
        # Extract visibility
        vis_match = re.search(r'VISIBILITY\s+(\d+(?:\s+\d+/\d+)?)\s+(?:MILE|MILES|SM)', raw_atis)
        if vis_match:
            weather['visibility'] = vis_match.group(1) + " SM"
        
        # Extract wind
        wind_match = re.search(r'WIND\s+(\d{3})\s+AT\s+(\d+)(?:\s+GUST(?:ING)?\s+(\d+))?', raw_atis)
        if wind_match:
            direction = wind_match.group(1)
            speed = wind_match.group(2)
            gust = wind_match.group(3)
            
            if gust:
                weather['wind'] = f"{direction}° at {speed} knots gusting {gust}"
            else:
                weather['wind'] = f"{direction}° at {speed} knots"
        
        # Extract cloud coverage
        cloud_match = re.search(r'(SKC|CLR|FEW|SCT|BKN|OVC)(?:\s+(\d+))?', raw_atis)
        if cloud_match:
            coverage = cloud_match.group(1)
            height = cloud_match.group(2)
            
            coverage_full = {
                'SKC': 'Sky Clear',
                'CLR': 'Clear',
                'FEW': 'Few',
                'SCT': 'Scattered',
                'BKN': 'Broken',
                'OVC': 'Overcast'
            }.get(coverage, coverage)
            
            if height:
                weather['clouds'] = f"{coverage_full} at {height}00 feet"
            else:
                weather['clouds'] = coverage_full
        
        # Extract temperature and dew point
        temp_match = re.search(r'TEMPERATURE\s+(-?\d+)(?:\s+DEW\s+POINT\s+(-?\d+))?', raw_atis)
        if temp_match:
            temp = temp_match.group(1)
            dew = temp_match.group(2)
            
            if dew:
                weather['temperature'] = f"{temp}°C / Dew Point {dew}°C"
            else:
                weather['temperature'] = f"{temp}°C"
        
        return weather
    
    def _extract_altimeter(self, raw_atis):
        """Extract altimeter setting from ATIS"""
        alt_match = re.search(r'ALTIMETER\s+(\d{4}|\d\.\d{2}|\d{2}\.\d{2})', raw_atis)
        if alt_match:
            return alt_match.group(1)
        return ""
    
    def _extract_remarks(self, raw_atis):
        """Extract remarks from ATIS"""
        remarks_match = re.search(r'REMARKS[.:]?(.*?)(?:ADVISE|INFORM|CONTACT|END)', raw_atis, re.DOTALL)
        if remarks_match:
            return remarks_match.group(1).strip()
        return ""
    
    def _extract_frequency(self, raw_atis):
        """Extract frequency for initial contact"""
        freq_match = re.search(r'(?:ADVISE|INFORM|CONTACT).*?ON\s+(\d{3}\.\d{1,2})', raw_atis)
        if freq_match:
            return freq_match.group(1)
        return ""

def parse_atis_example():
    """Example of parsing an ATIS message"""
    sample_atis = """
    KXYZ INFORMATION ALPHA. 1430Z. RUNWAY IN USE 27L AND 27R. 
    WIND 280 AT 10 KNOTS. VISIBILITY 10 MILES. FEW CLOUDS AT 5000. 
    TEMPERATURE 22 DEW POINT 15. ALTIMETER 2992. 
    ILS APPROACH IN PROGRESS. BIRDS REPORTED VICINITY OF AIRPORT.
    ADVISE YOU HAVE INFORMATION ALPHA ON INITIAL CONTACT. CONTACT TOWER ON 118.7.
    """
    
    decoder = ATISDecoder()
    decoded = decoder.decode_atis(sample_atis)
    formatted = decoder.format_decoded_atis(decoded)
    
    return formatted 