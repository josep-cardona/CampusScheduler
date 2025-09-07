from datetime import date

from playwright.sync_api import sync_playwright

from src.core.parser import parse_schedule_rows
from src.core.scraper import ScheduleScraper
from src.services.calendar_client import CalendarClient


def main():
    """Main function to run the scraper and print the schedule."""

    print("Connecting to Google Calendar...")
    calendar = CalendarClient()
    print("Successfully connected.")

    with sync_playwright() as p:
        scraper = ScheduleScraper(p)
        scheduled_classes = None
        try:
            raw_rows = scraper.get_classes_within_date_range(
                date(2025, 9, 20), date(2025, 9, 29)
            )
            if not raw_rows:
                print("No schedule data found.")
                return

            scheduled_classes = parse_schedule_rows(
                raw_rows, date(2025, 9, 20), date(2025, 9, 29)
            )

            print(f"\nSuccessfully scraped {len(scheduled_classes)} classes.\n")
            for lecture in scheduled_classes:
                print(lecture)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            scraper.close()
            print("\nBrowser closed.")

    assert scheduled_classes is not None
    calendar.add_lectures_to_calendar(scheduled_classes)


if __name__ == "__main__":
    main()
