import configparser
import json
from pathlib import Path

import keyring
from platformdirs import user_config_dir

from campsched.utils.exceptions import ConfigurationError

APP_NAME = "CampusScheduler"

# URLs
BASE_URL = "https://secretariavirtual.upf.edu"

# Scraper Settings
HEADLESS_BROWSER = True  # Set to True for production
BROWSER_LOCALE = "en-US"
NAVIGATION_TIMEOUT = 15000  # milliseconds

# OAuth Client Secret Configuration

# Centralize the permissions we are requesting from the user.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
]

# General Settings
TIMEZONE = "Europe/Madrid"


class ConfigManager:
    def __init__(self):
        self.config_dir = user_config_dir(appname=APP_NAME)
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

        config_dir_path = Path(self.config_dir)
        self.config_file = config_dir_path / "config.ini"
        self.token_path = config_dir_path / "token.json"
        self.client_secret_path = config_dir_path / "client_secret.json"
        self.exported_schedule_path = config_dir_path / "schedule.ics"

        self._config: configparser.ConfigParser | None = None

    def save(self, dni: str, password: str, calendar_id: str):
        """Saves the user's configuration to the config file."""

        config = configparser.ConfigParser()

        config.add_section("USER")
        config.set("USER", "DNI", dni)

        keyring.set_password(APP_NAME, dni, password)

        config.add_section("CALENDAR")
        config.set("CALENDAR", "DEFAULT_CALENDAR_ID", calendar_id)

        with open(self.config_file, "w") as configfile:
            config.write(configfile)

    def load(self):
        """Loads the user's configuration."""
        if not Path(self.config_file).exists():
            return None

        config = configparser.ConfigParser()
        config.read(self.config_file)

        dni = config.get("USER", "DNI", fallback=None)
        if dni:
            password_str = keyring.get_password(APP_NAME, dni)
            if password_str:
                if not config.has_section("SECRETS"):
                    config.add_section("SECRETS")
                config.set("SECRETS", "PASSWORD", password_str)

        self._config = config
        return self

    def get_dni(self):
        dni = self._config.get("USER", "DNI", fallback=None)

        if not dni:
            return None
        return dni

    def get_default_calendar(self):
        calendar_id = self._config.get("CALENDAR", "DEFAULT_CALENDAR_ID", fallback=None)

        if not calendar_id:
            return None
        return calendar_id

    def get_password(self):
        password_str = self._config.get("SECRETS", "PASSWORD", fallback=None)

        if not password_str:
            return None
        return password_str

    def clean(self, console):
        """Deletes all stored user data."""

        if self._config:
            # Delete password
            dni = self.get_dni()
            try:
                keyring.delete_password(APP_NAME, dni)
                console.print(f"🗑️ Password for user '{dni}' removed from keychain.")
            except keyring.errors.NoKeyringError:
                console.print(
                    "[yellow]Could not access system keychain to delete password.[/yellow]"
                )
            except Exception:
                # Catches PasswordNotFoundError and others gracefully
                console.print(
                    f"[yellow]No password for user '{dni}' found in keychain to delete.[/yellow]"
                )
        else:
            console.print(
                "[yellow]No configuration found, skipping password deletion.[/yellow]"
            )

        if Path(self.config_file).exists():
            Path(self.config_file).unlink()
            console.print(f"🗑️ Configuration file deleted: {Path(self.config_file)}")
        else:
            console.print("[yellow]No configuration file found to delete.[/yellow]")

        if Path(self.token_path).exists():
            Path(self.token_path).unlink()
            console.print(f"🗑️ Google Auth token deleted: {Path(self.token_path)}")
        else:
            console.print("[yellow]No Google Auth token found to delete.[/yellow]")

    def validate_config(self):
        if not Path(self.config_file).exists():
            raise ConfigurationError("Config file not found.")

        config = configparser.ConfigParser()
        config.read(self.config_file)

        if not config.has_section("USER") or not config.has_section("CALENDAR"):
            raise ConfigurationError("Config file has incorrect format.")

        if not config.get("USER", "DNI", fallback=None) or not config.get(
            "CALENDAR", "DEFAULT_CALENDAR_ID", fallback=None
        ):
            raise ConfigurationError("Config has empty fields.")

    def is_configured(self):
        if not Path(self.config_file).exists():
            return False
        self.validate_config()
        return True

    def validate_token(self):
        if not Path(self.token_path).exists():
            raise ConfigurationError("Google Auth Token not found.")

        try:
            with open(Path(self.token_path), "r") as t:
                token_file = json.load(t)
        except json.JSONDecodeError:
            raise ConfigurationError(
                f'Google Auth Token file is corrupted or invalid JSON.\n Please delete "{self.token_path}" and run [yellow bold]campsched config[/yellow bold] again.'
            )

        required_keys = [
            "token",
            "refresh_token",
            "token_uri",
            "client_id",
            "client_secret",
            "scopes",
            "universe_domain",
        ]
        missing_keys = [key for key in required_keys if not token_file.get(key)]

        if missing_keys:
            raise ConfigurationError(
                f'Google Auth Token file is missing required keys: {", ".join(missing_keys)}.\n Please delete "{self.token_path}" and run [yellow bold]campsched config[/yellow bold] again.'
            )

    def validate_client_secret(self):
        if not Path(self.client_secret_path).exists():
            raise ConfigurationError("Google Clout Client Secret not found.")

        try:
            with open(Path(self.client_secret_path), "r") as s:
                secret_file = json.load(s)
        except json.JSONDecodeError:
            raise ConfigurationError(
                f'Google Clout Client Secret file is corrupted or invalid JSON.\n Please delete "{self.client_secret_path}" and configure it again.'
            )

        if not secret_file.get("installed"):
            raise ConfigurationError(
                f'Google Clout Client Secret file is corrupted or invalid JSON.\n Please delete "{self.client_secret_path}" and configure it again.'
            )

        required_keys = [
            "client_id",
            "project_id",
            "auth_uri",
            "token_uri",
            "auth_provider_x509_cert_url",
            "client_secret",
            "redirect_uris",
        ]

        secret_file_installed = secret_file["installed"]

        missing_keys = [
            key for key in required_keys if not secret_file_installed.get(key)
        ]

        if missing_keys:
            raise ConfigurationError(
                f'Google Clout Client Secret file is missing required keys: {", ".join(missing_keys)}.\n Please delete "{self.token_path}" and configure it again.'
            )


if __name__ == "__main__":
    configman = ConfigManager()
