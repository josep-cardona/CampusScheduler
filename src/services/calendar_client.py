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

    def _batch_callback(self, request_id, response, exception):
        """
        Handles responses for each request in a batch.
        It now correctly handles empty responses from delete operations.
        """
        if exception:
            print(f"Request ID '{request_id}' failed: {exception}")
        else:
            # A successful 'delete' operation returns an empty response.
            # A successful 'insert' or 'update' returns the event resource dictionary.
            if response:
                # This block will only run for inserts and updates
                print(f"Request ID '{request_id}' (Create/Update) was successful.")
                print(f"  Event Link: {response.get('htmlLink')}")
            else:
                # This block will run for deletes
                print(f"Request ID '{request_id}' (Delete) was successful.")

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
            local_tz = pytz.timezone(config.TIMEZONE)
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
        """Deletes Google Calendar events from ScheduledLecture objects."""
        batch = self.service.new_batch_http_request(callback=self._batch_callback)

        if not lectures:
            print("No lectures to delete")
            return

        if not isinstance(lectures, list):
            lectures = [lectures]

        min_start_time = min(lec.start_time for lec in lectures)
        max_end_time = max(lec.end_time for lec in lectures)
        local_tz = pytz.timezone(config.TIMEZONE)
        aware_min_start = local_tz.localize(min_start_time)
        aware_max_end = local_tz.localize(max_end_time)

        # Check for existing events
        print(
            f"Checking for existing events between {aware_min_start} and {aware_max_end}..."
        )
        try:
            existing_events = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=aware_min_start.isoformat(),
                    timeMax=aware_max_end.isoformat(),
                    privateExtendedProperty=["managedBy=campusScheduler"],
                    singleEvents=True,
                )
                .execute()
                .get("items", [])
            )
        except HttpError as error:
            print(f"An error occurred during event listing: {error}")
        print(
            f"Found {len(existing_events)} existing events managed by this scheduler."
        )

        for lecture in existing_events:
            try:
                request = self.service.events().delete(
                    calendarId=calendar_id, eventId=lecture.get("id")
                )

                batch.add(request, request_id=lecture.get("id"))

            except HttpError as error:
                print(f"An error occurred: {error}")

        try:
            print("Executing batch request...")
            batch.execute()
            print("Batch execution complete.")
        except HttpError as error:
            print(f"An error occurred: {error}")

    def _get_unique_event_id(self, lecture: ScheduledLecture) -> str:
        """Creates a stable, unique identifier for a lecture event."""
        # We use a timestamp to ensure uniqueness across different times
        start_timestamp = int(lecture.start_time.timestamp())
        return f"upfScheduler{lecture.course_id}g{lecture.group_num}t{start_timestamp}"

    def add_lectures_to_calendar(
        self,
        lectures: Union[ScheduledLecture, List[ScheduledLecture]],
        calendar_id: str = "primary",
    ):
        """
        Creates or updates Google Calendar events from ScheduledLecture objects.
        The process is idempotent: it checks for an existing event using a unique ID
        and updates it if found, otherwise it creates a new one.
        """
        batch = self.service.new_batch_http_request(callback=self._batch_callback)

        if not lectures:
            print("No lectures to sync.")
            return

        if not isinstance(lectures, list):
            lectures = [lectures]

        # Extract the time window information
        min_start_time = min(lec.start_time for lec in lectures)
        max_end_time = max(lec.end_time for lec in lectures)
        local_tz = pytz.timezone(config.TIMEZONE)
        aware_min_start = local_tz.localize(min_start_time)
        aware_max_end = local_tz.localize(max_end_time)

        # Check for existing events
        print(
            f"Checking for existing events between {aware_min_start} and {aware_max_end}..."
        )
        try:
            existing_events = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=aware_min_start.isoformat(),
                    timeMax=aware_max_end.isoformat(),
                    privateExtendedProperty="managedBy=campusScheduler",
                    singleEvents=True,
                )
                .execute()
                .get("items", [])
            )
        except HttpError as error:
            print(f"An error occurred during event listing: {error}")
        print(
            f"Found {len(existing_events)} existing events managed by this scheduler."
        )

        # Create a lookup table
        existing_events_map = {
            event["extendedProperties"]["private"]["scheduler_id"]: event
            for event in existing_events
            if "extendedProperties" in event
            and "private" in event["extendedProperties"]
            and "scheduler_id" in event["extendedProperties"]["private"]
        }

        for lecture in lectures:
            unique_id = self._get_unique_event_id(lecture)

            summary = f"{lecture.course_id} - {lecture.course_name} ({lecture.lecture_type.value[0]})"

            event_body = {
                "summary": summary,
                "location": lecture.classroom,
                "description": f"{lecture.lecture_type.value} - Group {lecture.group_num}",
                "start": {
                    "dateTime": lecture.start_time.isoformat(),
                    "timeZone": config.TIMEZONE,
                },
                "end": {
                    "dateTime": lecture.end_time.isoformat(),
                    "timeZone": config.TIMEZONE,
                },
                "extendedProperties": {
                    "private": {
                        "scheduler_id": unique_id,
                        "managedBy": "campusScheduler",
                    }
                },
            }

            existing_event = existing_events_map.get(unique_id)

            if existing_event:
                # If it exists, UPDATE it.
                request = self.service.events().update(
                    calendarId=calendar_id,
                    eventId=existing_event["id"],
                    body=event_body,
                )
            else:
                # If it does not exist, INSERT it.
                request = self.service.events().insert(
                    calendarId=calendar_id, body=event_body
                )

            batch.add(request, request_id=unique_id)

        # Run the batch request
        try:
            print("Executing batch request...")
            batch.execute()
            print("Batch execution complete.")
        except HttpError as error:
            print(f"An error occurred during batch execution: {error}")

    def get_calendar_list(self):
        """
        Retrieves the list of all calendars the user has access to.
        Returns a list of calendar resource dictionaries.
        """
        try:
            calendar_list_result = (
                self.service.calendarList().list(minAccessRole="writer").execute()
            )
            return calendar_list_result.get("items", [])
        except HttpError as error:
            print(f"An error occurred while fetching the calendar list: {error}")
            return None  # Return None or an empty list to indicate failure
