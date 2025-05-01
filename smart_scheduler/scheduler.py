import numpy as np
from datetime import datetime, timedelta, time
import logging
from typing import List, Dict, Any, Optional

# Use SQLite database
from database_sqlite import db_client
from models import Doctor, Patient, Appointment, AppointmentSlot, DoctorAvailability
from config import (
    APPOINTMENT_TYPES,
    WORKING_HOURS_START,
    WORKING_HOURS_END,
    BUFFER_BETWEEN_APPOINTMENTS,
    OPTIMIZATION_WEIGHT_DOCTOR_LOAD,
    OPTIMIZATION_WEIGHT_TIME_PREFERENCE,
    OPTIMIZATION_WEIGHT_URGENCY
)

logger = logging.getLogger(__name__)


class AppointmentScheduler:
    """
    AI-driven appointment scheduling algorithm that optimizes for:
    1. Doctor availability
    2. Patient preference
    3. Urgency level
    4. Balanced doctor workload
    """

    def __init__(self):
        self.db = db_client

    def get_doctor_appointments(self, doctor_id, start_date, end_date):
        """Get all appointments for a doctor within a date range"""
        result = self.db.get_doctor_appointments(doctor_id, start_date, end_date)
        appointments = []

        if 'data' in result and result['data']:
            for appt_data in result['data']:
                appointments.append(Appointment.from_dict(appt_data))

        return appointments

    def get_doctor_availability(self, doctor_id, date_obj):
        """Get doctor's availability for a specific date"""
        result = self.db.get_doctor_availability(doctor_id)
        availabilities = []

        if 'data' in result and result['data']:
            for avail_data in result['data']:
                avail = DoctorAvailability.from_dict(avail_data)

                # Check if this availability applies to our date
                day_of_week = date_obj.weekday()  # 0 = Monday, 6 = Sunday

                # Check for specific date availability
                if avail.specific_date and avail.specific_date == date_obj:
                    availabilities.append(avail)
                # Check for recurring availability on this day of the week
                elif avail.recurring and avail.day_of_week == day_of_week:
                    availabilities.append(avail)

        return availabilities

    def find_optimal_slots(
            self,
            doctor_ids: List[int],
            start_date: datetime,
            end_date: datetime,
            appointment_type: str,
            patient_id: Optional[int] = None,
            urgency_level: int = 3,
            preferred_time: Optional[time] = None,
            max_slots: int = 10
    ) -> List[AppointmentSlot]:
        """
        Find optimal appointment slots based on multiple factors

        Args:
            doctor_ids: List of doctor IDs to consider
            start_date: Start date for appointment search
            end_date: End date for appointment search
            appointment_type: Type of appointment (determines duration)
            patient_id: ID of patient (for preference analysis)
            urgency_level: Urgency level (1-5)
            preferred_time: Preferred time of day
            max_slots: Maximum number of slots to return

        Returns:
            List of AppointmentSlot objects sorted by optimal score
        """
        logger.info(f"Finding optimal slots for {appointment_type} appointment between {start_date} and {end_date}")

        # Get appointment duration
        if appointment_type not in APPOINTMENT_TYPES:
            raise ValueError(f"Invalid appointment type: {appointment_type}")

        duration_minutes = APPOINTMENT_TYPES[appointment_type]
        duration = timedelta(minutes=duration_minutes)

        # Collect all possible slots
        all_slots = []

        for doctor_id in doctor_ids:
            # Get doctor info
            doctor_result = self.db.get_doctor(doctor_id)

            if not doctor_result['data'] or not doctor_result['data'][0]:
                logger.warning(f"Doctor ID {doctor_id} not found. Skipping.")
                continue

            doctor = Doctor.from_dict(doctor_result['data'][0])

            # Iterate through each day in the range
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

            while current_date.date() <= end_date.date():
                # Get doctor's availability for this day
                availabilities = self.get_doctor_availability(doctor_id, current_date.date())

                if not availabilities:
                    # Use default working hours if no specific availability is set
                    default_start = time(hour=WORKING_HOURS_START, minute=0)
                    default_end = time(hour=WORKING_HOURS_END, minute=0)

                    availabilities = [
                        DoctorAvailability(
                            id=-1,
                            doctor_id=doctor_id,
                            day_of_week=current_date.weekday(),
                            start_time=default_start,
                            end_time=default_end,
                            recurring=True,
                            specific_date=None
                        )
                    ]

                # Get existing appointments for this day
                day_start = datetime.combine(current_date.date(), time(0, 0))
                day_end = day_start + timedelta(days=1)
                existing_appointments = self.get_doctor_appointments(doctor_id, day_start, day_end)

                # Generate slots for each availability block
                for avail in availabilities:
                    # Convert availability to datetime objects
                    avail_start = datetime.combine(current_date.date(), avail.start_time)
                    avail_end = datetime.combine(current_date.date(), avail.end_time)

                    # Generate all possible time slots
                    slot_start = avail_start
                    while slot_start + duration <= avail_end:
                        slot_end = slot_start + duration

                        # Check for conflicts with existing appointments
                        is_conflict = False
                        for appt in existing_appointments:
                            # Add buffer time between appointments
                            appt_start_with_buffer = appt.start_time - BUFFER_BETWEEN_APPOINTMENTS
                            appt_end_with_buffer = appt.end_time + BUFFER_BETWEEN_APPOINTMENTS

                            if (slot_start < appt_end_with_buffer and slot_end > appt_start_with_buffer):
                                is_conflict = True
                                break

                        if not is_conflict:
                            # Calculate slot score
                            score = self._calculate_slot_score(
                                slot_start,
                                doctor_id,
                                existing_appointments,
                                urgency_level,
                                preferred_time,
                                patient_id
                            )

                            all_slots.append(AppointmentSlot(
                                start_time=slot_start,
                                end_time=slot_end,
                                doctor_id=doctor_id,
                                doctor_name=doctor.name,
                                score=score
                            ))

                        # Move to next slot
                        slot_start += timedelta(minutes=15)  # 15-minute intervals

                # Move to next day
                current_date += timedelta(days=1)

        # Sort slots by score (descending)
        all_slots.sort(key=lambda x: x.score, reverse=True)

        # Return top slots
        return all_slots[:max_slots]

    def _calculate_slot_score(
            self,
            slot_time: datetime,
            doctor_id: int,
            existing_appointments: List[Appointment],
            urgency_level: int,
            preferred_time: Optional[time] = None,
            patient_id: Optional[int] = None
    ) -> float:
        """
        Calculate a score for a specific appointment slot

        Higher score = better slot
        Score is based on:
        1. Doctor workload balance
        2. Patient time preference (if provided)
        3. Urgency level (higher urgency = prefer sooner slots)
        """
        score = 0.0

        # 1. Doctor workload - fewer appointments on the day = higher score
        daily_appointment_count = sum(1 for a in existing_appointments
                                      if a.start_time.date() == slot_time.date())

        workload_score = 1.0 - (daily_appointment_count / 10)  # Assuming 10 appointments is a full day
        workload_score = max(0.1, min(1.0, workload_score))  # Keep between 0.1 and 1.0

        # 2. Patient time preference
        time_pref_score = 0.5  # Default middle score

        if preferred_time:
            # Calculate how close the slot is to preferred time
            slot_hour = slot_time.hour + (slot_time.minute / 60.0)
            preferred_hour = preferred_time.hour + (preferred_time.minute / 60.0)
            hour_diff = abs(slot_hour - preferred_hour)

            # Convert to a score (closer = higher score)
            time_pref_score = 1.0 - (hour_diff / 8.0)  # Within 8 hours is the range
            time_pref_score = max(0.1, min(1.0, time_pref_score))
        elif patient_id:
            # If we have a patient but no explicit preference,
            # we could analyze their past appointments to infer a preference
            # This would be implemented here
            pass

        # 3. Urgency - higher urgency prefers sooner slots
        days_from_now = (slot_time.date() - datetime.now().date()).days
        if days_from_now < 0:
            # Past slots should not be considered
            urgency_score = 0.0
        elif urgency_level >= 4:  # High urgency
            # Strong preference for slots in next 2 days
            urgency_score = 1.0 - (min(days_from_now, 7) / 7.0)
        else:  # Normal or low urgency
            # Modest preference for sooner slots
            urgency_score = 0.8 - (min(days_from_now, 14) / 20.0)

        urgency_score = max(0.1, min(1.0, urgency_score))

        # Combine scores with weights
        score = (
                OPTIMIZATION_WEIGHT_DOCTOR_LOAD * workload_score +
                OPTIMIZATION_WEIGHT_TIME_PREFERENCE * time_pref_score +
                OPTIMIZATION_WEIGHT_URGENCY * urgency_score
        )

        return score