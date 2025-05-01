import os
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Union

# Import configuration
from config import (
    GOOGLE_CREDENTIALS_FILE,
    GOOGLE_TOKEN_FILE,
    GOOGLE_API_SCOPES,
    GOOGLE_CREDENTIALS,
    BASE_DIR
)

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service to handle integrations with Google Calendar"""

    def __init__(self):
        self.service = None
        try:
            self._authenticate()
        except Exception as e:
            logger.warning(f"Google Calendar authentication failed: {str(e)}")
            logger.warning("Running in limited mode without Google Calendar integration")

    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        # Check if credentials file exists
        credentials_path = os.path.join(BASE_DIR, GOOGLE_CREDENTIALS_FILE)
        if not os.path.exists(credentials_path):
            logger.warning(f"{GOOGLE_CREDENTIALS_FILE} not found. Using mock Google Calendar service.")
            return

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError

            creds = None
            token_path = os.path.join(BASE_DIR, GOOGLE_TOKEN_FILE)

            # Load existing token if it exists
            if os.path.exists(token_path):
                try:
                    creds = Credentials.from_authorized_user_info(
                        json.load(open(token_path)), GOOGLE_API_SCOPES
                    )
                except Exception as e:
                    logger.error(f"Error loading token: {str(e)}")

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logger.error(f"Error refreshing token: {str(e)}")
                        creds = None

                if not creds:
                    if not GOOGLE_CREDENTIALS:
                        raise ValueError("Google credentials not available")

                    flow = InstalledAppFlow.from_client_config(
                        GOOGLE_CREDENTIALS, GOOGLE_API_SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save the credentials
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Authenticated with Google Calendar API")

        except ImportError:
            logger.warning("Google API packages not installed. Running without Google Calendar integration.")
            self.service = None
        except Exception as e:
            logger.error(f"Error setting up Google Calendar: {str(e)}")
            self.service = None

    def get_calendar_list(self):
        """Get list of user's calendars"""
        if not self.service:
            logger.warning("Google Calendar service not available")
            return []

        try:
            calendar_list = self.service.calendarList().list().execute()
            return calendar_list.get('items', [])
        except Exception as e:
            logger.error(f"Error getting calendar list: {str(e)}")
            return []

    def create_event(self, calendar_id, appointment):
        """
        Create a new event in Google Calendar

        Args:
            calendar_id: ID of the calendar to add the event to
            appointment: Appointment object

        Returns:
            Event ID if successful, None otherwise
        """
        if not self.service:
            logger.warning("Google Calendar service not available")
            return None

        try:
            from googleapiclient.errors import HttpError

            # Create Google Calendar event
            event_body = {
                'summary': f"Appointment: {appointment.appointment_type}",
                'description': f"Patient ID: {appointment.patient_id}\nUrgency: {appointment.urgency_level}\nNotes: {appointment.notes or 'None'}",
                'start': {
                    'dateTime': appointment.start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': appointment.end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},  # 30 minutes before
                    ],
                },
            }

            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates='all'
            ).execute()

            logger.info(f"Event created: {event.get('htmlLink')}")
            return event['id']
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            return None

    def update_event(self, calendar_id, event_id, appointment):
        """
        Update an existing event in Google Calendar

        Args:
            calendar_id: ID of the calendar
            event_id: ID of the event to update
            appointment: Updated Appointment object

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.warning("Google Calendar service not available")
            return False

        try:
            from googleapiclient.errors import HttpError

            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

            event['summary'] = f"Appointment: {appointment.appointment_type}"
            event[
                'description'] = f"Patient ID: {appointment.patient_id}\nUrgency: {appointment.urgency_level}\nNotes: {appointment.notes or 'None'}"
            event['start'] = {
                'dateTime': appointment.start_time.isoformat(),
                'timeZone': 'UTC',
            }
            event['end'] = {
                'dateTime': appointment.end_time.isoformat(),
                'timeZone': 'UTC',
            }

            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()

            logger.info(f"Event updated: {updated_event.get('htmlLink')}")
            return True
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            return False

    def delete_event(self, calendar_id, event_id):
        """
        Delete an event from Google Calendar

        Args:
            calendar_id: ID of the calendar
            event_id: ID of the event to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            logger.warning("Google Calendar service not available")
            return False

        try:
            from googleapiclient.errors import HttpError

            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates='all'
            ).execute()

            logger.info(f"Event deleted: {event_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            return False

    def get_free_busy(self, calendar_ids, start_time, end_time):
        """
        Get free/busy information for calendars in the specified time range

        Args:
            calendar_ids: List of calendar IDs to check
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            Dictionary of busy time periods for each calendar
        """
        if not self.service:
            logger.warning("Google Calendar service not available")
            return {}

        try:
            from googleapiclient.errors import HttpError

            body = {
                "timeMin": start_time.isoformat(),
                "timeMax": end_time.isoformat(),
                "timeZone": "UTC",
                "items": [{"id": cal_id} for cal_id in calendar_ids]
            }

            response = self.service.freebusy().query(body=body).execute()
            return response.get('calendars', {})
        except Exception as e:
            logger.error(f"Error getting free/busy information: {str(e)}")
            return {}

    def get_events(self, calendar_id, start_time, end_time):
        """
        Get events from a calendar within the specified time range

        Args:
            calendar_id: ID of the calendar
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            List of events
        """
        if not self.service:
            logger.warning("Google Calendar service not available")
            return []

        try:
            from googleapiclient.errors import HttpError

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            return events_result.get('items', [])
        except Exception as e:
            logger.error(f"Error getting events: {str(e)}")
            return []