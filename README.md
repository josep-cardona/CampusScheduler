# CampusScheduler

A simple and powerful command-line tool to sync your UPF schedule directly to your Google Calendar or export it as a universal `.ics` file.

Stop wasting time manually adding every class. Run one command and get your schedule organized.

## About The Project

This tool automates the process of transferring a student's class schedule from the university web portal to a personal calendar. It provides a fast, reliable alternative to manually entering dozens of class events.

### Features

*   **Google Calendar Integration:** Automatically creates, updates, and deletes calendar events to match the official schedule.
*   **Universal `.ics` Export:** Generates a standard calendar file compatible with Apple Calendar, Outlook, and other applications.
*   **Secure Credential Storage:** User passwords are encrypted and stored in the native OS keychain (macOS Keychain, Windows Credential Manager) via the `keyring` library.
*   **Efficient Syncing:** Uses batch API requests to perform all calendar operations in a single, efficient transaction.
*   **User-Friendly CLI:** Built with Typer and Rich for a clean interface, progress bars, and clear feedback.


## Getting Started
Follow these steps to install and configure the tool.

### Prerequisites
1.  **Python 3.10+**
2.  **Google Cloud `client_secret.json` File**
    *   This is required only for Google Calendar synchronization. It allows the application to securely access the Google Calendar API on your behalf.
    *   Please follow the **[Google API Credentials Setup Guide](/GOOGLE_API_GUIDE.md)** to generate this file.


### Installation

The recommended installation method is via `pipx`, which installs and runs Python applications in isolated environments.

1.  **Install pipx (if you don't have it already):**
    ```bash
    pip install --user pipx
    pipx ensurepath
    ```
    *(You may need to restart your terminal after this step.)*

2.  **Install CampusScheduler:**
    ```bash
    pipx install git+https://github.com/JosepCardonaUPF/CampusScheduler.git
    ```

## Usage

### 1. Initial Configuration

Before first use, run the interactive setup wizard. This command will prompt for your credentials and guide you through Google Account authorization.

**Security is the top priority.** This tool runs entirely on your machine. Your university password is never stored in plain text; it's encrypted and stored securely in your operating system's native keychain (like macOS Keychain or Windows Credential Manager) using the `keyring` library.

```bash
campsched config
```

*   To skip the Google Calendar setup (for `.ics` export only), use the `--no-calendar` flag:
    ```bash
    campsched config --no-calendar
    ```

### 2. Command Reference

All commands and their options can be explored by using the `--help` flag.

```bash
# Get help for the main application
campsched --help

# Get help for a specific command
campsched sync --help
```

Once configured, you can use the following commands.

*   **`sync`**: Synchronize the schedule with Google Calendar.
    ```bash
    # Sync the next 14 days (default)
    campsched sync

    # Sync a specific date range (DD-MM-YYYY)
    campsched sync --start-date 01-12-2025 --end-date 31-12-2025
    # or
    campsched sync -s 01-12-2025 -e 31-12-2025
    ```

*   **`export`**: Export the schedule to an `.ics` file.
    ```bash
    # Export to the default `schedule.ics` file
    campsched export

    # Export to a custom output file
    campsched export --output my-classes.ics
    ```

*   **`delete`**: Remove events created by this tool from Google Calendar.
    ```bash
    # Delete events within a specific date range
    campsched delete --start-date 01-12-2025 --end-date 31-12-2025
    # or
    campsched delete -s 01-12-2025 -e 31-12-2025

    ```

*   **`clean`**: Remove all local configuration and credentials.
    ```bash
    campsched clean
    ```

## Technology Stack

This project utilizes several modern Python libraries and tools:

*   **Web Automation:** [Playwright](https://playwright.dev/python/) is used for robustly scraping the schedule from the university's JavaScript-rendered web portal.
*   **CLI Framework:** [Typer](https://typer.tiangolo.com/) provides the command-line interface structure, argument parsing, and help text generation.
*   **Rich TUI:** [Rich](https://rich.readthedocs.io/en/latest/) is used for creating beautiful and informative terminal output, including tables, progress bars, and formatted text.
*   **API Integration:** The official [Google API Python Client](https://github.com/googleapis/google-api-python-client) handles all communication with the Google Calendar API.
*   **Security:** [Keyring](https://keyring.readthedocs.io/en/latest/) provides a secure, cross-platform method for storing user passwords in the system's native credential manager.
*   **Dependency Management:** The project is packaged with `setuptools` and uses `uv` to manage a `requirements.txt` lock file for reproducible development environments.
