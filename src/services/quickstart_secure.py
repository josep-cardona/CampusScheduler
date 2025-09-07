import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# MODIFICATION: Import our centralized configuration
from src import config

def main():
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  creds = None
  
  # MODIFICATION: Use the TOKEN_PATH from config.py
  # This safely stores the user's token in the ignored 'credentials' folder.
  if os.path.exists(config.TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(config.TOKEN_PATH, config.SCOPES)

  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      # MODIFICATION: Use the CLIENT_SECRET_PATH from config.py
      # This safely loads your application's secret from the ignored folder.
      flow = InstalledAppFlow.from_client_secrets_file(
          config.CLIENT_SECRET_PATH, config.SCOPES
      )
      creds = flow.run_local_server(port=0)
      
    # MODIFICATION: Save the credentials for the next run to the secure TOKEN_PATH
    with open(config.TOKEN_PATH, "w") as token:
      token.write(creds.to_json())

  try:
    service = build("calendar", "v3", credentials=creds)

    # Call the Calendar API
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    print("Getting the upcoming 10 events")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
      print("No upcoming events found.")
      return

    # Prints the start and name of the next 10 events
    for event in events:
      start = event["start"].get("dateTime", event["start"].get("date"))
      print(start, event["summary"])

  except HttpError as error:
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()