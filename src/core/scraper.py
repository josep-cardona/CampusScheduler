import time
from playwright.sync_api import Playwright

from src import config

class ScheduleScraper:
    def __init__(self, playwright: Playwright):
        self.browser = playwright.chromium.launch(headless=config.HEADLESS_BROWSER)
        self.context = self.browser.new_context(
            base_url=config.BASE_URL,
            locale=config.BROWSER_LOCALE
        )
        self.page = self.context.new_page()

    def login(self):
        """Logs into the virtual secretary."""
        print("Navigating to login page...")
        self.page.goto("/")
        print("Entering credentials...")
        self.page.get_by_role("textbox", name="Dni").fill(config.DNI)
        self.page.get_by_role("textbox", name="Contrasenya").fill(config.PASSWORD)
        self.page.get_by_role("button", name="Entrar").click()
        self.page.wait_for_url("/cosmos/Controlador/*")
        print("Login successful.")

    def navigate_to_schedule(self):
        """Navigates from the main dashboard to the schedule agenda view."""
        print("Navigating to schedule...")
        self.page.get_by_role("link", name="Horaris de classe").click()
        self.page.wait_for_url("/pds/control/*")
        self.page.get_by_role("link", name="Veure Calendari").click()
        self.page.get_by_role("button", name="Setmana").wait_for(timeout=config.NAVIGATION_TIMEOUT)
        self.page.get_by_role("button", name="Agenda").click()
        print("On schedule page.")

    def find_first_week_with_classes(self):
        """Finds the first week that contains scheduled classes."""
        print("Searching for the first week with classes...")
        while self.page.get_by_text("No hi ha esdeveniments per").is_visible():
            self.page.get_by_role("button", name="SegÃ¼ent").click()
            time.sleep(0.5)
        time.sleep(3) # Wait for content to be fully loaded
        print("Found a week with classes.")

    def get_schedule_rows(self) -> list:
        """Fetches all the table rows containing schedule information."""
        self.login()
        self.navigate_to_schedule()
        self.find_first_week_with_classes()
        return self.page.query_selector_all("tbody tr")

    def close(self):
        """Closes the browser instance."""
        self.browser.close()