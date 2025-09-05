import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Credentials
DNI = os.getenv("DNI")
PASSWORD = os.getenv("PASSWORD")

# URLs
BASE_URL = "https://secretariavirtual.upf.edu"

# Scraper Settings
HEADLESS_BROWSER = False # Set to True for production
BROWSER_LOCALE = "en-US"
NAVIGATION_TIMEOUT = 5000 # milliseconds