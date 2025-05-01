import logging
import sys
import os
from datetime import datetime, timedelta
import argparse
from typing import List, Dict, Optional, Any
from pathlib import Path

# Set up base directory
BASE_DIR = Path(__file__).resolve().parent

# Use SQLite database
from database_sqlite import db_client

print("Using SQLite database for offline development")

from models import Doctor, Patient, Appointment, AppointmentSlot
from appointment_manager import AppointmentManager
from calendar_integration import GoogleCalendarService
from SoplexAITeam.medchatbot.config import BASE_DIR

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, "scheduler.log"))
    ]
)

logger = logging.getLogger(__name__)


class SmartAppointmentScheduler:
    """
    Main application class for the Smart Appointment Scheduler
    """

    def __init__(self):
        self.db = db_client
        self.appointment_manager = AppointmentManager()
        try:
            self.calendar_service = GoogleCalendarService()
        except Exception as e:
            logger.warning(f"Could not initialize Google Calendar service: {e}")
            self.calendar_service = None

        logger.info("Smart Appointment Scheduler initialized")

    def list_doctors(self, specialty: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available doctors"""
        try:
            query = self.db.table("doctors").select("*")

            if specialty:
                query = query.eq("specialty", specialty)

            result = query.eq("active", True).execute()

            doctors = []
            if result.get('data'):
                doctors = [Doctor.from_dict(doc).__dict__ for doc in result['data']]

            return doctors
        except Exception as e:
            logger.error(f"Error listing doctors: {e}")
            return []

    def list_patients(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """List patients"""
        try:
            query = self.db.table("patients").select("*")

            if search:
                # Simple search by name
                query = query.ilike("name", f"%{search}%")

            result = query.eq("active", True).execute()

            patients = []
            if result.get('data'):
                patients = [Patient.from_dict(pat).__dict__ for pat in result['data']]

            return patients
        except Exception as e:
            logger.error(f"Error listing patients: {e}")
            return []

    def find_available_slots(
            self,
            doctor_id: Optional[int] = None,
            specialty: Optional[str] = None,
            appointment_type: str = "routine_checkup",
            patient_id: Optional[int] = None,
            date_range_days: int = 14,
            urgency_level: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find available appointment slots using the AI scheduler
        """
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=date_range_days)

            doctor_ids = None
            if doctor_id:
                doctor_ids = [doctor_id]

            slots = self.appointment_manager.suggest_appointment_slots(
                doctor_ids=doctor_ids,
                specialty=specialty,
                appointment_type=appointment_type,
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                urgency_level=urgency_level
            )

            return [vars(slot) for slot in slots]
        except Exception as e:
            logger.error(f"Error finding available slots: {e}")
            return []

    def book_appointment(
            self,
            doctor_id: int,
            patient_id: int,
            start_time: datetime,
            appointment_type: str,
            notes: Optional[str] = None,
            urgency_level: int = 3
    ) -> Dict[str, Any]:
        """
        Book a new appointment
        """
        try:
            from SoplexAITeam.medchatbot.config import APPOINTMENT_TYPES

            # Calculate end time based on appointment type duration
            if appointment_type not in APPOINTMENT_TYPES:
                raise ValueError(f"Invalid appointment type. Must be one of: {', '.join(APPOINTMENT_TYPES.keys())}")

            duration_minutes = APPOINTMENT_TYPES[appointment_type]
            end_time = start_time + timedelta(minutes=duration_minutes)

            return self.appointment_manager.create_appointment(
                doctor_id=doctor_id,
                patient_id=patient_id,
                start_time=start_time,
                end_time=end_time,
                appointment_type=appointment_type,
                urgency_level=urgency_level,
                notes=notes
            )
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            raise

    def update_appointment(self, appointment_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an appointment"""
        try:
            return self.appointment_manager.update_appointment(appointment_id, updates)
        except Exception as e:
            logger.error(f"Error updating appointment: {e}")
            raise

    def cancel_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """Cancel an appointment"""
        try:
            return self.appointment_manager.cancel_appointment(appointment_id)
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            raise

    def get_doctor_schedule(self, doctor_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Get a doctor's schedule"""
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days)

            return self.appointment_manager.get_doctor_schedule(
                doctor_id=doctor_id,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error(f"Error getting doctor schedule: {e}")
            return []

    def get_patient_appointments(self, patient_id: int, include_past: bool = False) -> List[Dict[str, Any]]:
        """Get a patient's appointments"""
        try:
            return self.appointment_manager.get_patient_appointments(
                patient_id=patient_id,
                include_past=include_past
            )
        except Exception as e:
            logger.error(f"Error getting patient appointments: {e}")
            return []


def main():
    parser = argparse.ArgumentParser(description="MedNexusAI Smart Appointment Scheduler")
    parser.add_argument("--list-doctors", action="store_true", help="List all doctors")
    parser.add_argument("--list-patients", action="store_true", help="List all patients")
    parser.add_argument("--find-slots", action="store_true", help="Find available appointment slots")
    parser.add_argument("--book", action="store_true", help="Book an appointment")
    parser.add_argument("--cancel", type=int, help="Cancel appointment by ID")
    parser.add_argument("--doctor-schedule", type=int, help="Get doctor schedule by ID")
    parser.add_argument("--patient-appointments", type=int, help="Get patient appointments by ID")

    # Parameters for find-slots
    parser.add_argument("--doctor-id", type=int, help="Doctor ID")
    parser.add_argument("--specialty", type=str, help="Doctor specialty")
    parser.add_argument("--patient-id", type=int, help="Patient ID")
    parser.add_argument("--appointment-type", type=str, default="routine_checkup", help="Appointment type")
    parser.add_argument("--days", type=int, default=14, help="Days to look ahead")
    parser.add_argument("--urgency", type=int, default=3, help="Urgency level (1-5)")

    # Parameters for book
    parser.add_argument("--start-time", type=str, help="Appointment start time (ISO format)")
    parser.add_argument("--notes", type=str, help="Appointment notes")

    args = parser.parse_args()

    try:
        scheduler = SmartAppointmentScheduler()

        if args.list_doctors:
            doctors = scheduler.list_doctors(args.specialty)
            print(f"Found {len(doctors)} doctors:")
            for doc in doctors:
                print(f"  ID: {doc['id']}, Name: {doc['name']}, Specialty: {doc['specialty']}")

        elif args.list_patients:
            patients = scheduler.list_patients()
            print(f"Found {len(patients)} patients:")
            for pat in patients:
                print(f"  ID: {pat['id']}, Name: {pat['name']}")

        elif args.find_slots:
            if not (args.doctor_id or args.specialty):
                print("Error: Either --doctor-id or --specialty must be provided")
                sys.exit(1)

            slots = scheduler.find_available_slots(
                doctor_id=args.doctor_id,
                specialty=args.specialty,
                appointment_type=args.appointment_type,
                patient_id=args.patient_id,
                date_range_days=args.days,
                urgency_level=args.urgency
            )

            print(f"Found {len(slots)} available slots:")
            for i, slot in enumerate(slots):
                print(
                    f"  {i + 1}. {slot['start_time'].strftime('%Y-%m-%d %H:%M')} with Dr. {slot['doctor_name']} (Score: {slot['score']:.2f})")

        elif args.book:
            required = ['doctor_id', 'patient_id', 'start_time']
            missing = [arg for arg in required if getattr(args, arg.replace('-', '_')) is None]

            if missing:
                print(f"Error: Missing required arguments: {', '.join(['--' + arg for arg in missing])}")
                sys.exit(1)

            try:
                start_time = datetime.fromisoformat(args.start_time)

                appointment = scheduler.book_appointment(
                    doctor_id=args.doctor_id,
                    patient_id=args.patient_id,
                    start_time=start_time,
                    appointment_type=args.appointment_type,
                    notes=args.notes,
                    urgency_level=args.urgency
                )

                print(f"Appointment booked successfully:")
                print(f"  ID: {appointment['id']}")
                print(f"  Doctor ID: {appointment['doctor_id']}")
                print(f"  Patient ID: {appointment['patient_id']}")
                print(f"  Time: {appointment['start_time']} to {appointment['end_time']}")
                print(f"  Type: {appointment['appointment_type']}")
                if appointment.get('google_calendar_event_id'):
                    print(f"  Google Calendar: Synced")

            except ValueError as e:
                print(f"Error: {str(e)}")
                sys.exit(1)

        elif args.cancel is not None:
            try:
                result = scheduler.cancel_appointment(args.cancel)
                print(f"Appointment {args.cancel} cancelled successfully")
            except ValueError as e:
                print(f"Error: {str(e)}")
                sys.exit(1)

        elif args.doctor_schedule is not None:
            appointments = scheduler.get_doctor_schedule(
                doctor_id=args.doctor_schedule,
                days=args.days
            )

            print(f"Doctor {args.doctor_schedule} schedule ({len(appointments)} appointments):")
            for appt in appointments:
                start = datetime.fromisoformat(appt['start_time']).strftime('%Y-%m-%d %H:%M')
                print(f"  {start} - {appt['appointment_type']} - Status: {appt['status']}")

        elif args.patient_appointments is not None:
            appointments = scheduler.get_patient_appointments(
                patient_id=args.patient_appointments
            )

            print(f"Patient {args.patient_appointments} appointments ({len(appointments)}):")
            for appt in appointments:
                start = datetime.fromisoformat(appt['start_time']).strftime('%Y-%m-%d %H:%M')
                print(f"  {start} - {appt['appointment_type']} - Status: {appt['status']}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        logger.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()