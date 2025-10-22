from datetime import date

import typer
from rich.console import Console

from campsched.config import ConfigManager
from campsched.services.calendar_client import CalendarClient
from campsched.utils.enumerators import ContextEnum
from campsched.utils.scrape_to_lecture_flow import scrape_lectures_flow


def sync_command(
    start_date: date, end_date: date, ctx: typer.Context, console: Console
):
    console.print(
        f"   [dim]Syncing from {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}[/dim]\n"
    )
    calendar_client = ctx.obj[ContextEnum.CALENDAR]
    assert isinstance(calendar_client, CalendarClient)

    config: ConfigManager = ctx.obj[ContextEnum.CONFIG]
    dni = config.get_dni()
    password = config.get_password()

    scheduled_classes = scrape_lectures_flow(
        dni, password, start_date, end_date, console
    )

    calendar_client.sync_lectures(
        scheduled_classes,
        config.get_default_calendar(),
        only_delete=False,
    )
