import os

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Credentials
DNI = os.getenv("DNI")
PASSWORD = os.getenv("PASSWORD")

# URLs
BASE_URL = "https://secretariavirtual.upf.edu"

# Scraper Settings
HEADLESS_BROWSER = False  # Set to True for production
BROWSER_LOCALE = "en-US"
NAVIGATION_TIMEOUT = 5000  # milliseconds

# OAuth Client Secret Configuration

# Centralize the permissions we are requesting from the user.
# For this test, we only need to read events.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
]


# Build a path relative to the project's root directory
# This makes the code work no matter where you run it from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define the path to the credentials directory.
CREDENTIALS_DIR = os.path.join(PROJECT_ROOT, "credentials")

# Define the full path to your client secret file.
CLIENT_SECRET_PATH = os.path.join(CREDENTIALS_DIR, "client_secret.json")

# Define the full path for storing the user's token.
# This file will be created after the first successful login.
TOKEN_PATH = os.path.join(CREDENTIALS_DIR, "token.json")

# General Settings
TIMEZONE = "Europe/Madrid"
