import os.path
from datetime import datetime
from typing import List, Union

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src import config
from src.models.schedule import ScheduledLecture


class CalendarClient:
    """
    A client for interacting with the Google Calendar API.

    Handles authentication and provides methods for calendar operations.
    """

    def __init__(self):
        """
        Initializes the CalendarClient by authenticating the user
        and building the API service object.
        """
        # Get valid user credentials
        self.credentials = self._get_credentials()

        # Raise exception if authentication failed.
        if not self.credentials:
            raise Exception("Could not authenticate with Google Calendar.")

        # Use credentials to build calendar service object
        self.service = build("calendar", "v3", credentials=self.credentials)

    def _get_credentials(self) -> Credentials:
        """
        Handles the entire OAuth 2.0 flow.
        - Loads existing token if available.
        - Refreshes expired token.
        - Runs first-time login if no token exists.
        - Saves the token for future runs.
        """
        creds = None

        try:
            # Get credentials if they already exist
            if os.path.exists(config.TOKEN_PATH):
                creds = Credentials.from_authorized_user_file(
                    config.TOKEN_PATH, config.SCOPES
                )

            if not creds or not creds.valid:
                # Refresh credentials if possible
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Run flow to get new credentials
                    flow = InstalledAppFlow.from_client_secrets_file(
                        config.CLIENT_SECRET_PATH, config.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

            # Save new credentials
            with open(config.TOKEN_PATH, "w") as token:
                token.write(creds.to_json())

        except HttpError as error:
            print(f"An error occurred: {error}")

        return creds

    def find_events_by_time_and_summary(
        self,
        start_time: datetime,
        end_time: datetime,
        summary: str,
        calendar_id: str = "primary",
    ):
        """
        Searches for events that match a summary within a specific time window.
        Useful for checking if a class event already exists before creating it.
        """
        # Use self.service.events().list(...)
        #   - calendarId='primary'
        #   - timeMin=start_time in ISO format
        #   - timeMax=end_time in ISO format
        #   - q=summary  (This is the text search parameter)
        #   - singleEvents=True
        # Execute the request.
        # RETURN the list of matching events found.

        try:
            # Make time
            local_tz = pytz.timezone("Europe/Madrid")
            aware_start_time = local_tz.localize(start_time)
            aware_end_time = local_tz.localize(end_time)

            # Fetch ALL events within the specified time window.
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=aware_start_time.isoformat(),
                    timeMax=aware_end_time.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            all_events_in_window = events_result.get("items", [])

            if not all_events_in_window:
                return []

            # Filter results
            matching_events = []
            for event in all_events_in_window:
                if event.get("summary") == summary:
                    matching_events.append(event)

            return matching_events

        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def delete_lectures_from_calendar(
        self,
        lectures: Union[ScheduledLecture, List[ScheduledLecture]],
        calendar_id: str = "primary",
    ):
        if not isinstance(lectures, list):
            lectures = [lectures]

        for lecture in lectures:
            try:
                summary = f"{lecture.course_id} - {lecture.course_name} ({lecture.lecture_type.value[0]})"

                old_events = self.find_events_by_time_and_summary(
                    start_time=lecture.start_time,
                    end_time=lecture.end_time,
                    summary=summary,
                    calendar_id=calendar_id,
                )

                if len(old_events) > 0:
                    print(f"Found {len(old_events)} events with the same information.")
                    for old in old_events:
                        self.service.events().delete(
                            calendarId=calendar_id, eventId=old.get("id")
                        ).execute()
            except HttpError as error:
                print(f"An error occurred: {error}")

    def add_lectures_to_calendar(
        self,
        lectures: Union[ScheduledLecture, List[ScheduledLecture]],
        calendar_id: str = "primary",
        auto_update: bool = True,
    ):
        """
        Creates new Google Calendar events from one or more ScheduledLecture objects.
        Accepts a single ScheduledLecture or a list of them.
        """
        if not isinstance(lectures, list):
            lectures = [lectures]

        for lecture in lectures:
            try:
                summary = f"{lecture.course_id} - {lecture.course_name} ({lecture.lecture_type.value[0]})"

                event = {
                    "summary": summary,
                    "location": lecture.classroom,
                    "description": f"{lecture.lecture_type.value} - Group {lecture.group_num}",
                    "start": {
                        "dateTime": lecture.start_time.isoformat(),
                        "timeZone": "Europe/Madrid",
                    },
                    "end": {
                        "dateTime": lecture.end_time.isoformat(),
                        "timeZone": "Europe/Madrid",
                    },
                }

                old_events = self.find_events_by_time_and_summary(
                    start_time=lecture.start_time,
                    end_time=lecture.end_time,
                    summary=summary,
                    calendar_id=calendar_id,
                )

                if len(old_events) > 0:
                    print(f"Found {len(old_events)} events with the same information.")
                    if auto_update:
                        print("Updating events...")
                        for old in old_events:
                            self.service.events().delete(
                                calendarId=calendar_id, eventId=old.get("id")
                            ).execute()

                event = (
                    self.service.events()
                    .insert(calendarId=calendar_id, body=event)
                    .execute()
                )
                print("Event created: %s" % (event.get("htmlLink")))
            except HttpError as error:
                print(f"An error occurred: {error}")

    def list_user_calendars(self):
        """
        Prints the user's calendars from their calendar list.
        """
        print("Getting the list of user calendars...")
        try:
            calendar_list_result = self.service.calendarList().list().execute()
            calendars = calendar_list_result.get("items", [])

            if not calendars:
                print("No calendars found.")
                return

            print("Your calendars:")
            for calendar_item in calendars:
                # Each item is a dictionary with details about the calendar
                summary = calendar_item["summary"]
                calendar_id = calendar_item["id"]
                is_primary = calendar_item.get(
                    "primary", False
                )  # .get() is safer for optional fields
                role = calendar_item["accessRole"]

                print(f"- Summary: {summary}")
                print(f"  ID: {calendar_id}")
                print(f"  Access Role: {role}")
                if is_primary:
                    print("  (This is your primary calendar)")
                print("-" * 20)

        except HttpError as error:
            print(f"An error occurred: {error}")
