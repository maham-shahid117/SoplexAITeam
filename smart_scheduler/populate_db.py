from database_sqlite import db_client
from datetime import datetime, timedelta


def populate_sample_data():
    print("Adding sample data to the database...")

    # Add sample doctors
    doctor1 = {
        "name": "Dr. John Smith",
        "email": "john.smith@example.com",
        "specialty": "Cardiology"
    }

    doctor2 = {
        "name": "Dr. Sarah Johnson",
        "email": "sarah.johnson@example.com",
        "specialty": "Neurology"
    }

    doctor3 = {
        "name": "Dr. Michael Lee",
        "email": "michael.lee@example.com",
        "specialty": "Pediatrics"
    }

    print("Adding doctors...")
    db_client.create_doctor(doctor1)
    db_client.create_doctor(doctor2)
    db_client.create_doctor(doctor3)

    # Add sample patients
    patient1 = {
        "name": "James Wilson",
        "email": "james.wilson@example.com",
        "phone": "555-123-4567",
        "date_of_birth": "1980-05-15"
    }

    patient2 = {
        "name": "Emily Davis",
        "email": "emily.davis@example.com",
        "phone": "555-987-6543",
        "date_of_birth": "1992-11-23"
    }

    print("Adding patients...")
    db_client.create_patient(patient1)
    db_client.create_patient(patient2)

    # Add doctor availability
    # Monday to Friday, 9 AM to 5 PM for Dr. Smith
    for day in range(5):
        availability = {
            "doctor_id": 1,
            "day_of_week": day,
            "start_time": "09:00",
            "end_time": "17:00",
            "recurring": 1
        }
        db_client.create_doctor_availability(availability)

    # Monday, Wednesday, Friday for Dr. Johnson
    for day in [0, 2, 4]:
        availability = {
            "doctor_id": 2,
            "day_of_week": day,
            "start_time": "10:00",
            "end_time": "18:00",
            "recurring": 1
        }
        db_client.create_doctor_availability(availability)

    # Add some appointments
    today = datetime.now()

    appointment1 = {
        "doctor_id": 1,
        "patient_id": 1,
        "start_time": (today + timedelta(days=1, hours=10)).isoformat(),
        "end_time": (today + timedelta(days=1, hours=10, minutes=30)).isoformat(),
        "appointment_type": "routine_checkup",
        "urgency_level": 3
    }

    appointment2 = {
        "doctor_id": 2,
        "patient_id": 2,
        "start_time": (today + timedelta(days=2, hours=14)).isoformat(),
        "end_time": (today + timedelta(days=2, hours=14, minutes=45)).isoformat(),
        "appointment_type": "consultation",
        "urgency_level": 2
    }

    print("Adding appointments...")
    db_client.create_appointment(appointment1)
    db_client.create_appointment(appointment2)

    print("Sample data added successfully!")


if __name__ == "__main__":
    populate_sample_data()