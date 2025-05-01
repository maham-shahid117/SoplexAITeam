import sqlite3
import os
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SQLiteClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                # Create database file in the project directory
                db_path = Path(__file__).resolve().parent / "scheduler.db"
                cls._instance.conn = sqlite3.connect(str(db_path))
                cls._instance.conn.row_factory = sqlite3.Row
                cls._instance.cursor = cls._instance.conn.cursor()

                # Create tables if they don't exist
                cls._instance._create_tables()
                cls._instance.connected = True
                logger.info(f"Connected to SQLite database at {db_path}")
            except Exception as e:
                cls._instance.connected = False
                logger.error(f"Failed to connect to SQLite database: {str(e)}")
                raise
        return cls._instance

    def _create_tables(self):
        # Create doctors table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            specialty TEXT,
            calendar_id TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create patients table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            date_of_birth TEXT,
            medical_history TEXT,
            appointment_history TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create appointments table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            appointment_type TEXT NOT NULL,
            urgency_level INTEGER DEFAULT 3,
            status TEXT DEFAULT 'scheduled',
            notes TEXT,
            google_calendar_event_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doctor_id) REFERENCES doctors (id),
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
        ''')

        # Create doctor_availability table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctor_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            recurring INTEGER DEFAULT 1,
            specific_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doctor_id) REFERENCES doctors (id)
        )
        ''')

        self.conn.commit()

    def get_client(self):
        return self

    def table(self, table_name):
        return TableQuery(self, table_name)

    def get_doctors(self):
        self.cursor.execute("SELECT * FROM doctors WHERE active = 1")
        rows = self.cursor.fetchall()
        return {"data": [dict(row) for row in rows]}

    def get_doctor(self, doctor_id):
        self.cursor.execute("SELECT * FROM doctors WHERE id = ? AND active = 1", (doctor_id,))
        row = self.cursor.fetchone()
        if row:
            return {"data": [dict(row)]}
        return {"data": []}

    def create_doctor(self, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO doctors ({columns}) VALUES ({placeholders})"

        self.cursor.execute(query, list(data.values()))
        self.conn.commit()

        doctor_id = self.cursor.lastrowid
        return self.get_doctor(doctor_id)

    def update_doctor(self, doctor_id, data):
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE doctors SET {set_clause} WHERE id = ?"

        values = list(data.values())
        values.append(doctor_id)

        self.cursor.execute(query, values)
        self.conn.commit()

        return self.get_doctor(doctor_id)

    def get_patients(self):
        self.cursor.execute("SELECT * FROM patients WHERE active = 1")
        rows = self.cursor.fetchall()
        return {"data": [dict(row) for row in rows]}

    def get_patient(self, patient_id):
        self.cursor.execute("SELECT * FROM patients WHERE id = ? AND active = 1", (patient_id,))
        row = self.cursor.fetchone()
        if row:
            return {"data": [dict(row)]}
        return {"data": []}

    def create_patient(self, data):
        # Handle JSON fields
        if 'medical_history' in data and isinstance(data['medical_history'], dict):
            data['medical_history'] = json.dumps(data['medical_history'])
        if 'appointment_history' in data and isinstance(data['appointment_history'], list):
            data['appointment_history'] = json.dumps(data['appointment_history'])

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO patients ({columns}) VALUES ({placeholders})"

        self.cursor.execute(query, list(data.values()))
        self.conn.commit()

        patient_id = self.cursor.lastrowid
        return self.get_patient(patient_id)

    def update_patient(self, patient_id, data):
        # Handle JSON fields
        if 'medical_history' in data and isinstance(data['medical_history'], dict):
            data['medical_history'] = json.dumps(data['medical_history'])
        if 'appointment_history' in data and isinstance(data['appointment_history'], list):
            data['appointment_history'] = json.dumps(data['appointment_history'])

        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE patients SET {set_clause} WHERE id = ?"

        values = list(data.values())
        values.append(patient_id)

        self.cursor.execute(query, values)
        self.conn.commit()

        return self.get_patient(patient_id)

    def get_appointments(self):
        self.cursor.execute("SELECT * FROM appointments")
        rows = self.cursor.fetchall()
        return {"data": [dict(row) for row in rows]}

    def get_doctor_appointments(self, doctor_id, start_date=None, end_date=None):
        query = "SELECT * FROM appointments WHERE doctor_id = ?"
        params = [doctor_id]

        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND end_time <= ?"
            params.append(end_date.isoformat())

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return {"data": [dict(row) for row in rows]}

    def get_patient_appointments(self, patient_id):
        self.cursor.execute("SELECT * FROM appointments WHERE patient_id = ?", (patient_id,))
        rows = self.cursor.fetchall()
        return {"data": [dict(row) for row in rows]}

    def create_appointment(self, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO appointments ({columns}) VALUES ({placeholders})"

        self.cursor.execute(query, list(data.values()))
        self.conn.commit()

        appointment_id = self.cursor.lastrowid

        self.cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        row = self.cursor.fetchone()
        if row:
            return {"data": [dict(row)]}
        return {"data": []}

    def update_appointment(self, appointment_id, data):
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE appointments SET {set_clause} WHERE id = ?"

        values = list(data.values())
        values.append(appointment_id)

        self.cursor.execute(query, values)
        self.conn.commit()

        self.cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        row = self.cursor.fetchone()
        if row:
            return {"data": [dict(row)]}
        return {"data": []}

    def delete_appointment(self, appointment_id):
        self.cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        self.conn.commit()
        return {"data": []}

    def get_doctor_availability(self, doctor_id):
        self.cursor.execute("SELECT * FROM doctor_availability WHERE doctor_id = ?", (doctor_id,))
        rows = self.cursor.fetchall()
        return {"data": [dict(row) for row in rows]}

    def create_doctor_availability(self, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO doctor_availability ({columns}) VALUES ({placeholders})"

        self.cursor.execute(query, list(data.values()))
        self.conn.commit()

        availability_id = self.cursor.lastrowid

        self.cursor.execute("SELECT * FROM doctor_availability WHERE id = ?", (availability_id,))
        row = self.cursor.fetchone()
        if row:
            return {"data": [dict(row)]}
        return {"data": []}


class TableQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.select_cols = "*"
        self.conditions = []
        self.condition_values = []

    def select(self, cols="*"):
        self.select_cols = cols
        return self

    def eq(self, column, value):
        self.conditions.append(f"{column} = ?")
        self.condition_values.append(value)
        return self

    def ilike(self, column, pattern):
        self.conditions.append(f"{column} LIKE ?")
        self.condition_values.append(pattern)
        return self

    def gte(self, column, value):
        self.conditions.append(f"{column} >= ?")
        self.condition_values.append(value)
        return self

    def lte(self, column, value):
        self.conditions.append(f"{column} <= ?")
        self.condition_values.append(value)
        return self

    def execute(self):
        query = f"SELECT {self.select_cols} FROM {self.table_name}"

        if self.conditions:
            query += " WHERE " + " AND ".join(self.conditions)

        self.client.cursor.execute(query, self.condition_values)
        rows = self.client.cursor.fetchall()
        return {"data": [dict(row) for row in rows]}

    def insert(self, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"

        self.client.cursor.execute(query, list(data.values()))
        self.client.conn.commit()

        item_id = self.client.cursor.lastrowid

        self.client.cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (item_id,))
        row = self.client.cursor.fetchone()
        if row:
            return {"data": [dict(row)]}
        return {"data": []}

    def update(self, data):
        self.update_data = data
        return self

    def delete(self):
        return self


# Initialize SQLite client
db_client = SQLiteClient()