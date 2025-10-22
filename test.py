# 2-custom-columns.py
import time

from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

with (
    Progress(
        # Here are the columns we want, in the order we want them
        TextColumn("[bold cyan]{task.description}", justify="right"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",  # A simple text column for percentage
        TimeElapsedColumn(),
        "ETA:",
        TimeRemainingColumn(),
    ) as progress
):
    task1 = progress.add_task("[green]Processing...", total=1000)
    task2 = progress.add_task("[magenta]Scraping...", total=500)

    while not progress.finished:
        progress.update(task1, advance=5)
        progress.update(task2, advance=2.5)
        time.sleep(0.01)
