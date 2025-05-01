from dataclasses import dataclass
from datetime import datetime, date, time
from typing import List, Dict, Optional, Any
import json


@dataclass
class Doctor:
    id: int
    name: str
    email: str
    specialty: str
    calendar_id: Optional[str] = None
    active: bool = True
    created_at: Optional[str] = None  # Added created_at field

    @classmethod
    def from_dict(cls, data):
        # Filter out unknown fields
        valid_fields = ['id', 'name', 'email', 'specialty', 'calendar_id', 'active', 'created_at']
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        # Convert active from integer to boolean if needed
        if 'active' in filtered_data and isinstance(filtered_data['active'], int):
            filtered_data['active'] = bool(filtered_data['active'])
        return cls(**filtered_data)


@dataclass
class Patient:
    id: int
    name: str
    email: str
    phone: str
    date_of_birth: date
    medical_history: Optional[Dict] = None
    appointment_history: Optional[List[Dict]] = None
    active: bool = True
    created_at: Optional[str] = None  # Added created_at field

    @classmethod
    def from_dict(cls, data):
        # Filter out unknown fields
        valid_fields = [
            'id', 'name', 'email', 'phone', 'date_of_birth',
            'medical_history', 'appointment_history', 'active', 'created_at'
        ]
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        if 'date_of_birth' in filtered_data and isinstance(filtered_data['date_of_birth'], str):
            try:
                filtered_data['date_of_birth'] = datetime.fromisoformat(filtered_data['date_of_birth']).date()
            except ValueError:
                # Handle different date formats
                filtered_data['date_of_birth'] = datetime.strptime(filtered_data['date_of_birth'], "%Y-%m-%d").date()

        # Parse JSON strings to dictionaries/lists
        if 'medical_history' in filtered_data and isinstance(filtered_data['medical_history'], str):
            try:
                filtered_data['medical_history'] = json.loads(filtered_data['medical_history'])
            except json.JSONDecodeError:
                filtered_data['medical_history'] = {}

        if 'appointment_history' in filtered_data and isinstance(filtered_data['appointment_history'], str):
            try:
                filtered_data['appointment_history'] = json.loads(filtered_data['appointment_history'])
            except json.JSONDecodeError:
                filtered_data['appointment_history'] = []

        # Convert active from integer to boolean if needed
        if 'active' in filtered_data and isinstance(filtered_data['active'], int):
            filtered_data['active'] = bool(filtered_data['active'])

        return cls(**filtered_data)


@dataclass
class DoctorAvailability:
    id: int
    doctor_id: int
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: time
    end_time: time
    recurring: bool = True
    specific_date: Optional[date] = None
    created_at: Optional[str] = None  # Added created_at field

    @classmethod
    def from_dict(cls, data):
        # Filter out unknown fields
        valid_fields = [
            'id', 'doctor_id', 'day_of_week', 'start_time', 'end_time',
            'recurring', 'specific_date', 'created_at'
        ]
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        if 'start_time' in filtered_data and isinstance(filtered_data['start_time'], str):
            filtered_data['start_time'] = datetime.strptime(filtered_data['start_time'], "%H:%M").time()
        if 'end_time' in filtered_data and isinstance(filtered_data['end_time'], str):
            filtered_data['end_time'] = datetime.strptime(filtered_data['end_time'], "%H:%M").time()
        if 'specific_date' in filtered_data and filtered_data['specific_date'] and isinstance(
                filtered_data['specific_date'], str):
            try:
                filtered_data['specific_date'] = datetime.fromisoformat(filtered_data['specific_date']).date()
            except ValueError:
                filtered_data['specific_date'] = datetime.strptime(filtered_data['specific_date'], "%Y-%m-%d").date()

        # Convert recurring from integer to boolean if needed
        if 'recurring' in filtered_data and isinstance(filtered_data['recurring'], int):
            filtered_data['recurring'] = bool(filtered_data['recurring'])

        return cls(**filtered_data)


@dataclass
class Appointment:
    id: Optional[int]
    doctor_id: int
    patient_id: int
    start_time: datetime
    end_time: datetime
    appointment_type: str
    urgency_level: int
    status: str = "scheduled"  # scheduled, completed, cancelled, no_show
    notes: Optional[str] = None
    google_calendar_event_id: Optional[str] = None
    created_at: Optional[str] = None  # Added created_at field

    @classmethod
    def from_dict(cls, data):
        # Filter out unknown fields
        valid_fields = [
            'id', 'doctor_id', 'patient_id', 'start_time', 'end_time',
            'appointment_type', 'urgency_level', 'status', 'notes',
            'google_calendar_event_id', 'created_at'
        ]
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        if 'start_time' in filtered_data and isinstance(filtered_data['start_time'], str):
            try:
                filtered_data['start_time'] = datetime.fromisoformat(filtered_data['start_time'])
            except ValueError:
                # Try another format if ISO format fails
                filtered_data['start_time'] = datetime.strptime(filtered_data['start_time'], "%Y-%m-%d %H:%M:%S")

        if 'end_time' in filtered_data and isinstance(filtered_data['end_time'], str):
            try:
                filtered_data['end_time'] = datetime.fromisoformat(filtered_data['end_time'])
            except ValueError:
                # Try another format if ISO format fails
                filtered_data['end_time'] = datetime.strptime(filtered_data['end_time'], "%Y-%m-%d %H:%M:%S")

        return cls(**filtered_data)

    def to_dict(self):
        result = {
            'doctor_id': self.doctor_id,
            'patient_id': self.patient_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'appointment_type': self.appointment_type,
            'urgency_level': self.urgency_level,
            'status': self.status,
        }
        if self.id is not None:
            result['id'] = self.id
        if self.notes is not None:
            result['notes'] = self.notes
        if self.google_calendar_event_id is not None:
            result['google_calendar_event_id'] = self.google_calendar_event_id
        return result


@dataclass
class AppointmentSlot:
    start_time: datetime
    end_time: datetime
    doctor_id: int
    doctor_name: str
    score: float  # optimization score (0-1)