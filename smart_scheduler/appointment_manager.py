import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union

# Use SQLite database
from database_sqlite import db_client
from models import Appointment, Doctor, Patient, AppointmentSlot
from scheduler import AppointmentScheduler
from calendar_integration import GoogleCalendarService
from SoplexAITeam.medchatbot.config import APPOINTMENT_TYPES

logger = logging.getLogger(__name__)


class AppointmentManager:
    """
    Core business logic for appointment management
    """

    def __init__(self):
        self.db = db_client
        self.scheduler = AppointmentScheduler()
        try:
            self.calendar_service = GoogleCalendarService()
        except Exception as e:
            logger.warning(f"Could not initialize calendar service: {e}")
            self.calendar_service = None

    def get_appointment(self, appointment_id: int) -> Optional[Appointment]:
        """Get appointment details"""
        result = self.db.table("appointments").select("*").eq("id", appointment_id).execute()

        if not result.get('data') or not result['data']:
            return None

        return Appointment.from_dict(result['data'][0])

    def suggest_appointment_slots(
            self,
            doctor_ids: List[int] = None,
            specialty: Optional[str] = None,
            appointment_type: str = "routine_checkup",
            patient_id: Optional[int] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            urgency_level: int = 3,
            preferred_time: Optional[datetime] = None,
            max_slots: int = 10
    ) -> List[AppointmentSlot]:
        """
        Suggest optimal appointment slots based on given criteria
        """
        # Validate appointment type
        if appointment_type not in APPOINTMENT_TYPES:
            raise ValueError(
                f"Invalid appointment type: {appointment_type}. Must be one of: {', '.join(APPOINTMENT_TYPES.keys())}")

        # Default date range if not provided
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=14)  # Look 2 weeks ahead by default

        # If specific doctors aren't provided but specialty is, find doctors with that specialty
        if not doctor_ids and specialty:
            doctor_result = self.db.table("doctors").select("id").eq("specialty", specialty).eq("active",
                                                                                                True).execute()

            if doctor_result.get('data'):
                doctor_ids = [doc['id'] for doc in doctor_result['data']]
            else:
                logger.warning(f"No doctors found with specialty: {specialty}")
                return []

        if not doctor_ids:
            # Get all active doctors if none specified
            doctor_result = self.db.table("doctors").select("id").eq("active", True).execute()

            if doctor_result.get('data'):
                doctor_ids = [doc['id'] for doc in doctor_result['data']]
            else:
                logger.warning("No active doctors found")
                return []

        # Extract just the time part if preferred_time is a full datetime
        preferred_time_only = None
        if preferred_time:
            preferred_time_only = preferred_time.time()

        # Use scheduler to find optimal slots
        return self.scheduler.find_optimal_slots(
            doctor_ids=doctor_ids,
            start_date=start_date,
            end_date=end_date,
            appointment_type=appointment_type,
            patient_id=patient_id,
            urgency_level=urgency_level,
            preferred_time=preferred_time_only,
            max_slots=max_slots
        )

    def create_appointment(
            self,
            doctor_id: int,
            patient_id: int,
            start_time: datetime,
            end_time: datetime,
            appointment_type: str,
            urgency_level: int = 3,
            notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new appointment
        """
        # Validate appointment type
        if appointment_type not in APPOINTMENT_TYPES:
            raise ValueError(f"Invalid appointment type: {appointment_type}")

        # Validate doctor and patient
        doctor_result = self.db.get_doctor(doctor_id)
        if not doctor_result.get('data'):
            raise ValueError(f"Doctor with ID {doctor_id} not found")

        patient_result = self.db.get_patient(patient_id)
        if not patient_result.get('data'):
            raise ValueError(f"Patient with ID {patient_id} not found")

        # Check for conflicts
        day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        existing_appointments = self.scheduler.get_doctor_appointments(doctor_id, day_start, day_end)

        for appt in existing_appointments:
            if (start_time < appt.end_time and end_time > appt.start_time):
                raise ValueError(f"Appointment conflict detected with appointment ID {appt.id}")

        # Create appointment record
        appointment_data = {
            'doctor_id': doctor_id,
            'patient_id': patient_id,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'appointment_type': appointment_type,
            'urgency_level': urgency_level,
            'status': 'scheduled'
        }

        if notes:
            appointment_data['notes'] = notes

        # Insert into database
        result = self.db.create_appointment(appointment_data)

        if not result.get('data') or not result['data']:
            raise Exception("Failed to create appointment")

        new_appointment = Appointment.from_dict(result['data'][0])

        # Sync with Google Calendar if doctor has a calendar ID and calendar service is available
        doctor = Doctor.from_dict(doctor_result['data'][0])

        if doctor.calendar_id and self.calendar_service:
            logger.info(f"Syncing appointment to Google Calendar for doctor {doctor_id}")

            event_id = self.calendar_service.create_event(
                calendar_id=doctor.calendar_id,
                appointment=new_appointment
            )

            if event_id:
                # Update appointment with calendar event ID
                self.db.update_appointment(
                    new_appointment.id,
                    {'google_calendar_event_id': event_id}
                )
                new_appointment.google_calendar_event_id = event_id

        return new_appointment.to_dict()

    def update_appointment(
            self,
            appointment_id: int,
            updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing appointment

        Args:
            appointment_id: ID of appointment to update
            updates: Dictionary of fields to update

        Returns:
            Updated appointment data
        """
        # Get current appointment
        current_appointment = self.get_appointment(appointment_id)
        if not current_appointment:
            raise ValueError(f"Appointment with ID {appointment_id} not found")

        # Check for conflicts if changing time
        if 'start_time' in updates or 'end_time' in updates:
            start_time = updates.get('start_time', current_appointment.start_time)
            end_time = updates.get('end_time', current_appointment.end_time)

            day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            existing_appointments = self.scheduler.get_doctor_appointments(
                current_appointment.doctor_id, day_start, day_end
            )

            for appt in existing_appointments:
                if appt.id != appointment_id and (start_time < appt.end_time and end_time > appt.start_time):
                    raise ValueError(f"Appointment conflict detected with appointment ID {appt.id}")

        # Update in database
        result = self.db.update_appointment(appointment_id, updates)

        if not result.get('data') or not result['data']:
            raise Exception("Failed to update appointment")

        updated_appointment = Appointment.from_dict(result['data'][0])

        # If we have a Google Calendar event ID, update it
        if updated_appointment.google_calendar_event_id and self.calendar_service:
            # Get doctor's calendar ID
            doctor_result = self.db.get_doctor(updated_appointment.doctor_id)

            if doctor_result.get('data') and doctor_result['data'][0].get('calendar_id'):
                doctor = Doctor.from_dict(doctor_result['data'][0])

                self.calendar_service.update_event(
                    calendar_id=doctor.calendar_id,
                    event_id=updated_appointment.google_calendar_event_id,
                    appointment=updated_appointment
                )

        return updated_appointment.to_dict()

    def cancel_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """
        Cancel an appointment
        """
        # Get current appointment
        current_appointment = self.get_appointment(appointment_id)
        if not current_appointment:
            raise ValueError(f"Appointment with ID {appointment_id} not found")

        # Update status
        result = self.db.update_appointment(appointment_id, {'status': 'cancelled'})

        if not result.get('data') or not result['data']:
            raise Exception("Failed to cancel appointment")

        updated_appointment = Appointment.from_dict(result['data'][0])

        # If we have a Google Calendar event ID, delete or update it
        if updated_appointment.google_calendar_event_id and self.calendar_service:
            # Get doctor's calendar ID
            doctor_result = self.db.get_doctor(updated_appointment.doctor_id)

            if doctor_result.get('data') and doctor_result['data'][0].get('calendar_id'):
                doctor = Doctor.from_dict(doctor_result['data'][0])

                self.calendar_service.delete_event(
                    calendar_id=doctor.calendar_id,
                    event_id=updated_appointment.google_calendar_event_id
                )

        return updated_appointment.to_dict()

    def get_doctor_schedule(
            self,
            doctor_id: int,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a doctor's appointment schedule
        """
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=7)  # Default to one week

        appointments = self.scheduler.get_doctor_appointments(doctor_id, start_date, end_date)
        return [appt.to_dict() for appt in appointments]

    def get_patient_appointments(
            self,
            patient_id: int,
            include_past: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get a patient's appointments
        """
        result = self.db.get_patient_appointments(patient_id)

        if not result.get('data'):
            return []

        appointments = [Appointment.from_dict(appt_data) for appt_data in result['data']]

        if not include_past:
            now = datetime.now()
            appointments = [appt for appt in appointments if appt.start_time >= now]

        return [appt.to_dict() for appt in appointments]