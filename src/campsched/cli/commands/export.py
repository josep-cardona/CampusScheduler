from datetime import date

import typer
from ics import Calendar, Event
from rich.console import Console

from campsched.config import ConfigManager
from campsched.utils.enumerators import ContextEnum
from campsched.utils.scrape_to_lecture_flow import scrape_lectures_flow


def export_command(
    start_date: date,
    end_date: date,
    ctx: typer.Context,
    output_file: str,
    console: Console,
):
    console.print(
        f"   [dim]Exporting from {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}[/dim]\n"
    )

    config: ConfigManager = ctx.obj[ContextEnum.CONFIG]
    dni = config.get_dni()
    password = config.get_password()

    scheduled_classes = scrape_lectures_flow(
        dni, password, start_date, end_date, console
    )
    if not scheduled_classes:
        console.print("[bold yellow]No classes found to export.[/bold yellow]")
        raise typer.Exit()

    with console.status("[bold blue]📄 Creating .ics file...", spinner="dots"):
        cal = Calendar()

        for lecture in scheduled_classes:
            event = Event()
            event.name = f"{lecture.course_id} - {lecture.course_name}"
            event.begin = lecture.start_time
            event.end = lecture.end_time
            event.location = lecture.classroom
            event.description = (
                f"{lecture.lecture_type.value}\nGroup: {lecture.group_num}"
            )

            cal.events.add(event)

        with open(output_file, "w") as f:
            f.writelines(cal.serialize_iter())

    console.print(
        f"\n[bold green]✅ Successfully exported {len(scheduled_classes)} classes to '{output_file}'![/bold green]"
    )
