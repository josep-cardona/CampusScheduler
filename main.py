from playwright.sync_api import sync_playwright

from src.core.parser import parse_schedule_rows
from src.core.scraper import ScheduleScraper


def main():
    """Main function to run the scraper and print the schedule."""
    with sync_playwright() as p:
        scraper = ScheduleScraper(p)
        try:
            raw_rows = scraper.get_schedule_rows()
            if not raw_rows:
                print("No schedule data found.")
                return

            scheduled_classes = parse_schedule_rows(raw_rows)

            print(f"\nSuccessfully scraped {len(scheduled_classes)} classes.\n")
            for lecture in scheduled_classes:
                print(lecture)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            scraper.close()
            print("\nBrowser closed.")


if __name__ == "__main__":
    main()