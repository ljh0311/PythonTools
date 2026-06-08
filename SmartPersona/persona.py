import os
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception:
    pass


class SmartPersona:
    def __init__(self):
        """Initialize the SmartPersona (user identity)."""
        load_dotenv()
        self.name = os.getenv("PERSONA_NAME", "SmartPersona")
        self.age = int(os.getenv("PERSONA_AGE", 28))
        self.gender = os.getenv("PERSONA_GENDER", "male")
        self.occupation = os.getenv("PERSONA_OCCUPATION", "software engineer")
        self.location = os.getenv("PERSONA_LOCATION", "Singapore")
        self.email = os.getenv("PERSONA_EMAIL", "smartpersona.sg@gmail.com")
        self.phone = os.getenv("PERSONA_PHONE", "+65 9123 4567")
        self.address = os.getenv("PERSONA_ADDRESS", "10 Anson Road, #27-15 International Plaza, Singapore 079903")

    def get_name(self):
        return self.name

    def get_age(self):
        return self.age

    def get_gender(self):
        return self.gender

    def get_occupation(self):
        return self.occupation

    def get_location(self):
        return self.location

    def get_email(self):
        return self.email

    def get_phone(self):
        return self.phone

    def get_address(self):
        return self.address
