import time
from datetime import date, datetime
from typing import List

from playwright.sync_api import ElementHandle, Playwright
from rich.progress import (
    Progress,
)

from campsched import config


class ScheduleScraper:
    def __init__(self, playwright: Playwright, dni: str, password: str):
        self.dni = dni
        self.password = password
        self.browser = playwright.chromium.launch(headless=config.HEADLESS_BROWSER)
        self.context = self.browser.new_context(
            base_url=config.BASE_URL, locale=config.BROWSER_LOCALE
        )
        self.page = self.context.new_page()

    def login(self):
        """Logs into the virtual secretary."""
        self.page.goto("/")
        self.page.get_by_role("textbox", name="Dni").fill(self.dni)
        self.page.get_by_role("textbox", name="Contrasenya").fill(self.password)
        self.page.get_by_role("button", name="Entrar").click()
        self.page.wait_for_url("/cosmos/Controlador/*")

    def navigate_to_schedule(self):
        """Navigates from the main dashboard to the schedule agenda view."""
        self.page.get_by_role("link", name="Horaris de classe").click()
        self.page.wait_for_url("/pds/control/*")
        self.page.get_by_role("link", name="Veure Calendari").click()
        self.page.get_by_role("button", name="Setmana").wait_for(
            timeout=config.NAVIGATION_TIMEOUT
        )
        self.page.get_by_role("button", name="Agenda").click()

    def find_first_week_with_classes(self):
        """Finds the first week that contains scheduled classes."""
        while self.page.get_by_text("No hi ha esdeveniments per").is_visible():
            self.page.query_selector(".fc-next-button").click()
            time.sleep(0.5)
        time.sleep(1)  # Wait for content to be fully loaded

    def get_schedule_rows(self) -> List[ElementHandle]:
        """Fetches all the table rows containing schedule information."""
        return self.page.query_selector_all("tbody tr")

    def get_classes_within_date_range(
        self, start_date: date, end_date: date, progress: Progress, task_id
    ):
        """Fetches all rows within a date range"""

        if end_date >= start_date:
            progress.update(task_id, description="[green]🔐 Authenticating...")
            self.login()
            progress.advance(task_id)

            progress.update(task_id, description="[green]🌍 Navigating to schedule...")
            self.navigate_to_schedule()
            progress.advance(task_id)

            progress.update(task_id, description="[green]🔍 Fetching class data...")

            total_days = (end_date - start_date).days + 1

            scraping_days_task = progress.add_task(
                "[cyan]Scraping Days...", total=total_days
            )

            # Go to beginning of month
            start_month = (
                f"{start_date.strftime('%m').lstrip('0')}/{start_date.strftime('%Y')}"
            )
            self.page.locator("#comboMesesAnyos").select_option(start_month)

            self.find_first_week_with_classes()

            all_row_data = []

            while True:
                new_rows = self.get_schedule_rows()
                for row in new_rows:
                    event_title_elem = row.query_selector(".fc-event-title")
                    event_time_elem = row.query_selector(".fc-list-event-time")
                    row_data = {
                        "class": row.get_attribute("class"),
                        "details": event_title_elem.inner_text()
                        if event_title_elem
                        else "",
                        "event_time": event_time_elem.inner_text()
                        if event_time_elem
                        else "",
                        "data_date": row.get_attribute("data-date"),
                    }
                    all_row_data.append(row_data)

                # Get all fc-list-day row dates
                fc_list_day_rows = [
                    row
                    for row in new_rows
                    if "fc-list-day" in (row.get_attribute("class") or "")
                ]
                if not fc_list_day_rows:
                    break
                day_dates = [
                    datetime.strptime(row.get_attribute("data-date"), "%Y-%m-%d").date()
                    for row in fc_list_day_rows
                ]
                max_date = max(day_dates)
                days_scraped = (max_date - start_date).days
                progress.update(
                    scraping_days_task,
                    completed=days_scraped,
                    description=f"[cyan]Scraped until {min(max_date, end_date).strftime('%d-%m-%Y')}",
                )
                if max_date > end_date:
                    progress.update(scraping_days_task, completed=total_days)
                    break
                self.page.query_selector(".fc-next-button").click()
                time.sleep(0.5)
            progress.update(
                task_id, description="[green]✔ Scraping complete", completed=3
            )
            return all_row_data
        else:
            print("End date should be after start date.")
            return []

    def close(self):
        """Closes the browser instance."""
        self.browser.close()
