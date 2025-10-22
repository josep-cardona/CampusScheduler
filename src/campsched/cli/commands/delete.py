from datetime import date, datetime, time

import typer
from rich.console import Console

from campsched.services.calendar_client import CalendarClient
from campsched.utils.enumerators import ContextEnum


def delete_range_command(
    start_date: date, end_date: date, ctx: typer.Context, console: Console
):
    console.print(
        f"   [dim]Deleting events from {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}[/dim]\n"
    )

    calendar_client = ctx.obj[ContextEnum.CALENDAR]
    assert isinstance(calendar_client, CalendarClient)
    calendar_client.delete_lectures(
        datetime.combine(start_date, time.min),
        datetime.combine(end_date, time.max),
        ctx.obj[ContextEnum.CONFIG].get_default_calendar(),
    )
