import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# Google Calendar API config
GOOGLE_CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "")#add you credentials.json file here
GOOGLE_TOKEN_FILE = os.environ.get("GOOGLE_TOKEN_FILE", "")#add your token.json file here
GOOGLE_API_SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Load credentials
try:
    credentials_path = os.path.join(BASE_DIR, GOOGLE_CREDENTIALS_FILE)
    if os.path.exists(credentials_path):
        with open(credentials_path, 'r') as file:
            GOOGLE_CREDENTIALS = json.load(file)
    else:
        print(f"Warning: {GOOGLE_CREDENTIALS_FILE} not found. Google Calendar integration will not work.")
        GOOGLE_CREDENTIALS = None
except Exception as e:
    print(f"Error loading Google credentials: {str(e)}")
    GOOGLE_CREDENTIALS = None

# Scheduling parameters
DEFAULT_APPOINTMENT_DURATION = timedelta(minutes=30)
WORKING_HOURS_START = 9  # 9 AM
WORKING_HOURS_END = 17   # 5 PM
MAX_APPOINTMENTS_PER_DOCTOR_PER_DAY = 12
BUFFER_BETWEEN_APPOINTMENTS = timedelta(minutes=5)
LOOKAHEAD_DAYS = 30  # Schedule appointments up to 30 days in advance
OPTIMIZATION_WEIGHT_DOCTOR_LOAD = 0.3
OPTIMIZATION_WEIGHT_TIME_PREFERENCE = 0.2
OPTIMIZATION_WEIGHT_URGENCY = 0.5

# Appointment types and their durations (in minutes)
APPOINTMENT_TYPES = {
    "routine_checkup": 30,
    "follow_up": 15,
    "consultation": 45,
    "procedure": 60,
    "emergency": 30
}

# Urgency levels (1-5, where 5 is most urgent)
URGENCY_LEVELS = {
    1: "Low",
    2: "Normal",
    3: "Medium",
    4: "High",
    5: "Emergency"
}