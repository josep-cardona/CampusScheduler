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

    def sync_lectures(
        self,
        lectures: Union[ScheduledLecture, List[ScheduledLecture]],
        calendar_id: str = "primary",
        only_delete: bool = False,
    ):
        """
        Synchronizes a list of lectures with Google Calendar using a batch request.
        This is a full sync operation: it creates, updates, and deletes events as needed.
        """
        if not isinstance(lectures, list):
            lectures = [lectures]

        if not lectures:
            print(
                "No lectures to sync. If you expected lectures, the scraper might have found none in the given range."
            )
            return

        # --- FETCH EXISTING STATE ---
        min_start_time = min(lec.start_time for lec in lectures)
        max_end_time = max(lec.end_time for lec in lectures)

        # Use the helper function we discussed to keep this clean
        existing_events = self._get_managed_events_in_range(
            min_start_time, max_end_time, calendar_id
        )
        print(
            f"Found {len(existing_events)} existing events managed by this scheduler in the target time window."
        )

        existing_events_map = {}
        for event in existing_events:
            scheduler_id = (
                event.get("extendedProperties", {})
                .get("private", {})
                .get("scheduler_id")
            )
            if scheduler_id:
                existing_events_map[scheduler_id] = event

        # --- PREPARE THE BATCH PLAN ---
        batch = self.service.new_batch_http_request(callback=self._batch_callback)
        ops_to_create = 0
        ops_to_update = 0
        if not only_delete:
            for lecture in lectures:
                unique_id = self._get_unique_event_id(lecture)
                event_body = self._build_event_body(lecture)

                existing_event = existing_events_map.get(unique_id)
                if existing_event:
                    request = self.service.events().update(
                        calendarId=calendar_id,
                        eventId=existing_event["id"],
                        body=event_body,
                    )
                    # This is the brilliant part of your logic: remove it from the map.
                    existing_events_map.pop(unique_id)
                    ops_to_update += 1
                else:
                    request = self.service.events().insert(
                        calendarId=calendar_id, body=event_body
                    )
                    ops_to_create += 1

                batch.add(request, request_id=f"sync_{unique_id}")

        # --- PREPARE DELETIONS (ORPHANED EVENTS) ---
        ops_to_delete = 0
        for orphaned_event in existing_events_map.values():
            request = self.service.events().delete(
                calendarId=calendar_id, eventId=orphaned_event["id"]
            )
            batch.add(request, request_id=f"delete_{orphaned_event.get('id')}")
            ops_to_delete += 1

        should_execute = self._confirm_sync_plan(
            ops_to_create, ops_to_update, ops_to_delete
        )
        if should_execute:
            try:
                batch.execute()
                print("Batch sync complete.")
            except HttpError as error:
                print(f"An error occurred during batch request: {error}")

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
        It now correctly parses the string request_id.
        """
        # Use split('_', 1) to safely split only on the first underscore.
        # This handles cases where the event ID itself might contain an underscore.
        try:
            operation_type, item_id = request_id.split("_", 1)
        except ValueError:
            # If the split fails for some reason, handle it gracefully
            operation_type = "unknown"
            item_id = request_id

        if exception:
            print(
                f"Operation '{operation_type}' for ID '{item_id}' failed: {exception}"
            )
        else:
            if operation_type == "delete":
                print(f"Successfully deleted event '{item_id}'.")
            elif operation_type == "sync":
                print(
                    f"Successfully synced (created/updated) event '{item_id}'. Link: {response.get('htmlLink')}"
                )
            else:
                # Fallback for any other case
                print(f"Successfully completed operation for ID '{item_id}'.")

    def _get_managed_events_in_range(
        self, min_start_time: datetime, max_end_time: datetime, calendar_id: str
    ):
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
            return existing_events
        except HttpError as error:
            print(f"An error occurred during event listing: {error}")
            return []

    def _get_unique_event_id(self, lecture: ScheduledLecture) -> str:
        """Creates a stable, unique identifier for a lecture event."""
        # We use a timestamp to ensure uniqueness across different times
        start_timestamp = int(lecture.start_time.timestamp())
        return f"upfScheduler{lecture.course_id}g{lecture.group_num}t{start_timestamp}"

    def _build_event_body(self, lecture):
        # (New helper)
        unique_id = self._get_unique_event_id(lecture)
        event_body = {
            "summary": f"{lecture.course_id} - {lecture.course_name} ({lecture.lecture_type.value[0]})",
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
        return event_body

    def _confirm_sync_plan(self, to_create, to_update, to_delete) -> bool:
        # --- EXECUTE WITH CONFIRMATION (THE DRY RUN) ---
        if to_create == 0 and to_update == 0 and to_delete == 0:
            print("\nCalendar is already up to date. No changes needed.")
            return False

        print("\n--- SYNC PLAN ---")
        print(f"Create: {to_create} new events")
        print(f"Update: {to_update} existing events")
        print(f"Delete: {to_delete} orphaned events")
        print("--------------------")

        confirm = input("Proceed with these changes? (y/n): ").lower()
        if confirm == "y":
            print("Executing batch sync...")
            return True
        else:
            print("Sync cancelled by user.")
            return False
