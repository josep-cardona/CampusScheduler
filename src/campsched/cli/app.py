import time
from datetime import date, datetime, timedelta

import typer
from prompt_toolkit import prompt
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from campsched.cli.commands.delete import delete_range_command
from campsched.cli.commands.export import export_command
from campsched.cli.commands.sync import sync_command
from campsched.config import (
    ConfigManager,
)
from campsched.services.calendar_client import CalendarClient
from campsched.utils.enumerators import ContextEnum

app = typer.Typer(pretty_exceptions_show_locals=False)
console = Console()


@app.command()
def export(
    ctx: typer.Context,
    start_date: str = typer.Option(
        None, "--start-date", "-s", help="Start date in DD-MM-YYYY format"
    ),
    end_date: str = typer.Option(
        None, "--end-date", "-e", help="End date in DD-MM-YYYY format"
    ),
    output_file: str = typer.Option(
        None, "--output", "-o", help="Name of the output file."
    ),
):
    """
    Exports your university schedule into a universal .ics calendar file. (no Google Calendar integration needed)
    """
    if not start_date:
        start_dt = date.today()
    else:
        try:
            start_dt = datetime.strptime(start_date, "%d-%m-%Y").date()
        except ValueError:
            raise typer.BadParameter("start_date must be in DD-MM-YYYY format")
    if not end_date:
        end_dt = start_dt + timedelta(days=14)
    else:
        try:
            end_dt = datetime.strptime(end_date, "%d-%m-%Y").date()
        except ValueError:
            raise typer.BadParameter("end_date must be in DD-MM-YYYY format")

    if start_dt > end_dt:
        raise typer.BadParameter("start_date must be before or equal to end_date")

    if not output_file:
        config: ConfigManager = ctx.obj[ContextEnum.CONFIG]
        output_file = config.exported_schedule_path

    export_command(start_dt, end_dt, ctx, output_file, console)


@app.command()
def sync(
    ctx: typer.Context,
    start_date: str = typer.Option(
        None, "--start-date", "-s", help="Start date in DD-MM-YYYY format"
    ),
    end_date: str = typer.Option(
        None, "--end-date", "-e", help="End date in DD-MM-YYYY format"
    ),
):
    """
    Synchronises classes in Google Calendar in the specified range
    """
    if not start_date:
        start_dt = date.today()
    else:
        try:
            start_dt = datetime.strptime(start_date, "%d-%m-%Y").date()
        except ValueError:
            raise typer.BadParameter("start_date must be in DD-MM-YYYY format")
    if not end_date:
        end_dt = start_dt + timedelta(days=14)
    else:
        try:
            end_dt = datetime.strptime(end_date, "%d-%m-%Y").date()
        except ValueError:
            raise typer.BadParameter("end_date must be in DD-MM-YYYY format")

    if start_dt > end_dt:
        raise typer.BadParameter("start_date must be before or equal to end_date")

    sync_command(start_dt, end_dt, ctx, console)


@app.command()
def delete(
    ctx: typer.Context,
    start_date: str = typer.Option(
        None, "--start-date", "-s", help="Start date in DD-MM-YYYY format"
    ),
    end_date: str = typer.Option(
        None, "--end-date", "-e", help="End date in DD-MM-YYYY format"
    ),
):
    """
    Deletes Google Calendar events created by CampusScheduler in the specified range
    """
    if not (start_date and end_date):
        raise typer.BadParameter(
            "Provide both --start-date and --end-date for range delete"
        )
    try:
        start_dt = datetime.strptime(start_date, "%d-%m-%Y").date()
        end_dt = datetime.strptime(end_date, "%d-%m-%Y").date()
    except ValueError:
        raise typer.BadParameter("Dates must be in DD-MM-YYYY format")

    if start_dt > end_dt:
        raise typer.BadParameter("start_date must be before or equal to end_date")

    delete_range_command(start_dt, end_dt, ctx, console)


@app.command()
def config(
    ctx: typer.Context,
    calendar: bool = typer.Option(True, help=""),
):
    """
    Guides the user through setting up CampusScheduler for the first time.
    """
    console.print(
        Panel.fit(
            "[bold cyan]Welcome to the CampusScheduler Setup Wizard! ✨[/bold cyan]"
        )
    )
    console.print("Let's get you set up in a few simple steps.\n")

    time.sleep(1)  # Give user some time to read

    security_message = Text.from_markup(
        "• [bold green]Required Credentials:[/bold green] Your university credentials are needed so CampusScheduler can access your schedule on the university platform.\n"
        "• [bold green]Completely Local:[/bold green] This program runs entirely on your machine. Your credentials are never sent to any third-party servers.\n"
        "• [bold green]Secure Storage:[/bold green] Your university password is encrypted and stored securely in your operating system's native keychain (macOS Keychain, Windows Credential Manager)."
    )
    console.print(
        Panel(
            security_message,
            title="[bold]🔒 Security Overview[/bold]",
            border_style="yellow",
            padding=(1, 2),
        )
    )
    console.print()

    console.print("[u bold]Step 1: University Credentials[/u bold]")
    dni = typer.prompt("   👤 DNI")
    password = prompt("   🔑 PASSWORD: ", is_password=True)
    console.print("✅ Credentials entered.\n")

    calendar_id = "primary"

    if calendar:
        console.print("[u bold]Step 2: Google Calendar Authorization[/u bold]")
        with console.status(
            "Waiting for Google login in your browser...", spinner="earth"
        ):
            ctx.obj[ContextEnum.CALENDAR] = authenticate_calendar()
        console.print("✅ Google Account connected successfully!\n")
        calendar_client: CalendarClient = ctx.obj[ContextEnum.CALENDAR]

        console.print("[u bold]Step 3: Select Your Destination Calendar[/u bold]")
        console.print("Choose the calendar where your schedule will be synced:")

        with console.status("Fetching user calendars ...", spinner="point"):
            all_calendars = calendar_client.get_calendar_list()

        if all_calendars:
            for i, cal in enumerate(all_calendars):
                console.print(
                    f"   [{i + 1}] {cal['summary']}" + (" (default)" if i == 0 else "")
                )

            while True:
                try:
                    option = int(
                        typer.prompt(
                            f"Enter number (1-{len(all_calendars)}), or press Enter for primary",
                            default=1,
                        )
                    )
                    if 1 <= option <= len(all_calendars):
                        calendar_id = all_calendars[option - 1]["id"]
                        console.print(
                            f"✅ Selected calendar: {all_calendars[option - 1]['summary']}\n"
                        )
                        break
                    else:
                        console.print(
                            "[bold red]Invalid number, please try again.[/bold red]"
                        )
                except Exception:
                    console.print(
                        "[bold red]Invalid number, please try again.[/bold red]"
                    )

    with console.status("[bold green]Saving configuration securely...", spinner="dots"):
        ConfigManager().save(dni, password, calendar_id)
        # Add a small delay for effect jeje

        time.sleep(1)
    console.print("✅ Configuration saved!")
    console.print(
        "\n[bold green]🎉 All done! You can now run `campsched sync`.[/bold green]"
    )


@app.command()
def clean():
    """
    Deletes all stored user data, including saved credentials and tokens.
    """
    confirm_message = Text.from_markup(
        "[bold yellow]This will delete all stored user data, including:[/bold yellow]\n"
        "• Your saved password from the system keychain.\n"
        "• Your saved configuration (DNI, default calendar).\n"
        "• Your Google Authentication token."
    )

    console.print(
        Panel(
            confirm_message,
            title="[bold]WARNING[/bold]",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    if (
        not console.input(
            "\n[bold red]Are you sure you want to continue? (y/N): [/bold red]"
        ).lower()
        == "y"
    ):
        console.print("[green]Cleanup aborted by user.[/green]")
        return

    if ConfigManager().is_configured():
        config_manager = ConfigManager().load()
        config_manager.clean(console)
    else:
        ConfigManager().clean(console)
    console.print("\n[bold green]✅ Cleanup complete.[/bold green]")


def authenticate_calendar():
    try:
        cal = CalendarClient(console)
    except Exception as e:
        console.print(f"❌ {e}")
        raise typer.Abort()
    return cal


@app.callback()
def main_callback(ctx: typer.Context):
    """
    CampusScheduler: A CLI to sync your university schedule with Google Calendar.
    """
    ctx.ensure_object(dict)

    # Skip setup if running the config command
    if ctx.invoked_subcommand == "config" or ctx.invoked_subcommand == "clean":
        return

    config = ConfigManager().load()

    if not ConfigManager().is_configured():
        console.print(
            "[bold red]Configuration not found. Please run 'campsched config' first.[/bold red]"
        )
        raise typer.Exit(code=1)

    if ctx.invoked_subcommand != "export":
        ctx.obj[ContextEnum.CALENDAR] = authenticate_calendar()
    ctx.obj[ContextEnum.CONFIG] = config


if __name__ == "__main__":
    app()
