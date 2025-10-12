import os.path
from datetime import datetime
from typing import List, Union

import pytz
import typer
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from rich.console import Console
from rich.table import Table

from campsched import config
from campsched.config import ConfigManager
from campsched.models.schedule import ScheduledLecture


class CalendarClient:
    """
    A client for interacting with the Google Calendar API.

    Handles authentication and provides methods for calendar operations.
    """

    def __init__(self, console: Console):
        """
        Initializes the CalendarClient by authenticating the user
        and building the API service object.
        """
        self.console = console

        # Get valid user credentials
        self.credentials = self._get_credentials()

        # Raise exception if authentication failed.
        if not self.credentials:
            raise Exception("Could not authenticate with Google Calendar.")

        # Use credentials to build calendar service object
        self.service = build("calendar", "v3", credentials=self.credentials)

    def delete_lectures(
        self,
        start_date: datetime,
        end_date: datetime,
        calendar_id: str,
    ):
        """
        Deletes events created by CampusScheduler on the specified range.
        """
        with self.console.status(
            "[bold yellow]🔍 Searching for events to delete...", spinner="dots"
        ):
            existing_events = self._get_managed_events_in_range(
                start_date, end_date, calendar_id
            )
        if not existing_events:
            self.console.print(
                "[bold green]✅ No events managed by campsched found in this date range. Nothing to do![/bold green]"
            )
            raise typer.Exit()

        self.console.print(f"Found {len(existing_events)} events to delete.")

        existing_events_map = {}
        for event in existing_events:
            scheduler_id = (
                event.get("extendedProperties", {})
                .get("private", {})
                .get("scheduler_id")
            )
            if scheduler_id:
                existing_events_map[scheduler_id] = event

        batch = self.service.new_batch_http_request(callback=self._batch_callback)

        # --- PREPARE DELETIONS (ORPHANED EVENTS) ---
        ops_to_delete = 0
        for orphaned_event in existing_events_map.values():
            request = self.service.events().delete(
                calendarId=calendar_id, eventId=orphaned_event["id"]
            )
            batch.add(request, request_id=f"delete_{orphaned_event.get('id')}")
            ops_to_delete += 1

        if not typer.confirm("Proceed with deletion?"):
            self.console.print("[red]Aborted by user.[/red]")
            raise typer.Exit()

        try:
            with self.console.status(
                f"[bold red]🗑️ Deleting {len(existing_events)} events...",
                spinner="earth",
            ):
                batch.execute()
            self.console.print(
                f"\n[bold green]✅ Successfully deleted {len(existing_events)} events from your calendar.[/bold green]"
            )
        except HttpError as error:
            self.console.print(
                f"[bold red] An error occurred during batch request: {error} [/bold red]"
            )

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
        if not self.console:
            self.console = Console()  # Fallback if not provided

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

        with self.console.status("🔍 Analyzing your Google Calendar..."):
            existing_events = self._get_managed_events_in_range(
                min_start_time, max_end_time, calendar_id
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
                with self.console.status(
                    "[bold green]Executing batch sync...", spinner="dots"
                ):
                    batch.execute()
                self.console.print(
                    "\n[bold green]✨ Sync complete! Your calendar is now up to date.[/bold green]"
                )
            except HttpError as error:
                self.console.print(
                    f"[bold red] An error occurred during batch request: {error} [/bold red]"
                )

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
            self.console.print(
                f"[bold red]An error occurred while fetching the calendar list: {error} [/bold red]"
            )
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
            if os.path.exists(ConfigManager().token_path):
                ConfigManager().validate_token()
                creds = Credentials.from_authorized_user_file(
                    ConfigManager().token_path, config.SCOPES
                )

            if not creds or not creds.valid:
                # Refresh credentials if possible
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as refresh_error:
                        print(f"Failed to refresh token: {refresh_error}")
                        # If refresh fails, fall through to re-authentication
                        creds = None  # Ensure we re-authenticate

                if (
                    not creds
                ):  # This block will run for first-time auth or failed refresh
                    ConfigManager().validate_client_secret()
                    flow = InstalledAppFlow.from_client_secrets_file(
                        ConfigManager().client_secret_path, config.SCOPES
                    )

                    # Make the manual authentication step very clear for the user.
                    print("\n--- Google Authentication Required ---")
                    print(
                        "A browser window should open for you to log in and grant permissions."
                    )
                    print(
                        "If it doesn't, please copy the URL printed below and open it manually in your browser."
                    )
                    print("------------------------------------\n")

                    creds = flow.run_local_server(
                        port=0
                    )  # Use port=0 to find a free port

            # Save new credentials
            with open(ConfigManager().token_path, "w") as token:
                token.write(creds.to_json())

        except FileNotFoundError:
            self.console.print(
                "\n[bold red]The 'client_secret.json' file was not found in the 'credentials' directory.[/bold red]"
            )
            self.console.print(
                f"Please follow the setup instructions in the README.md to obtain this file from the Google Cloud Console and place it in: {ConfigManager().config_dir}\n"
            )
            self.console.print(
                "[bold]If you don't want to use Google Calendar integration run: [yellow] campsched config --no-calendar [/yellow] [/bold]"
            )
            return None  # Return None to indicate failure
        except Exception as error:
            raise error
            self.console.print(
                f"[bold red]An unexpected error occurred during authentication: {error}[/bold red]"
            )
            return None

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

    def _get_managed_events_in_range(
        self, min_start_time: datetime, max_end_time: datetime, calendar_id: str
    ):
        local_tz = pytz.timezone(config.TIMEZONE)
        aware_min_start = local_tz.localize(min_start_time)
        aware_max_end = local_tz.localize(max_end_time)

        # Check for existing events
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
            "summary": f"{lecture.course_name} - {lecture.lecture_type.value}",
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
            self.console.print(
                "\n[bold green]✅ Your calendar is already up to date. No changes needed.[/bold green]"
            )
            return False

        self.console.print()
        table = Table(title="📊 Sync Plan", show_header=False, padding=(0, 2))
        table.add_column(style="green")
        table.add_column(style="bold")
        table.add_column(style="cyan")

        table.add_row("Create ➕", f"{to_create}", "new events")
        table.add_row("Update 🔄", f"{to_update}", "existing events")
        table.add_row("Delete ➖", f"{to_delete}", "orphaned events")

        self.console.print(table)

        if not typer.confirm("Proceed with these changes?"):
            self.console.print("[bold red]Sync cancelled by user.[/bold red]")
            return False
        return True
