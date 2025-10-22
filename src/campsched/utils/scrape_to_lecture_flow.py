import time
from datetime import date

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from campsched.core.parser import parse_schedule_rows
from campsched.core.scraper import ScheduleScraper


def scrape_lectures_flow(
    dni: str, password: str, start_date: date, end_date: date, console: Console
):
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[bold blue]{task.completed} of {task.total}"),
        TimeElapsedColumn(),
        transient=True,  # Cleans up the progress bar on exit
    )

    with progress:
        # --- Stage 1: Scraping ---
        scraping_task = progress.add_task("[bold green]Scraping...", total=3)

        with sync_playwright() as p:
            scraper = ScheduleScraper(p, dni, password)
            scheduled_classes = None
            try:
                raw_rows = scraper.get_classes_within_date_range(
                    start_date=start_date,
                    end_date=end_date,
                    progress=progress,
                    task_id=scraping_task,
                )
                if not raw_rows:
                    print("No schedule data found.")
                    return

                scheduled_classes = parse_schedule_rows(raw_rows, start_date, end_date)

                progress.print(
                    f"\n[bold]🔍 Found {len(scheduled_classes)} classes.[/bold]"
                )
                # for lecture in scheduled_classes:
                #     print(lecture)

            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                scraper.close()
        time.sleep(3)

        assert scheduled_classes is not None
        return scheduled_classes
