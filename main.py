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

    target_calendar_id = "primary"
    all_calendars = calendar.get_calendar_list()
    if all_calendars:
        print("\nPlease choose a calendar to sync your schedule to:")
        for i, cal in enumerate(all_calendars):
            print(f"  [{i + 1}] {cal['summary']}")

        while True:
            try:
                choice = int(
                    input(
                        f"Enter number (1-{len(all_calendars)}), or press Enter for primary: "
                    )
                    or 1
                )
                if 1 <= choice <= len(all_calendars):
                    target_calendar_id = all_calendars[choice - 1]["id"]
                    print(
                        f"Selected calendar: {all_calendars[choice - 1]['summary']}\n"
                    )
                    break
                else:
                    print("Invalid number, please try again.")
            except ValueError:
                print("Invalid input, please enter a number.")

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
                raw_rows, date(2025, 9, 20), date(2025, 9, 25)
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
    calendar.sync_lectures(scheduled_classes, target_calendar_id, only_delete=False)


if __name__ == "__main__":
    main()
