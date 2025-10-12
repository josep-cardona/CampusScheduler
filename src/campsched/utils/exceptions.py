class CampSchedError(Exception):
    """Base exception for all errors in the campsched application."""

    pass


class ConfigurationError(CampSchedError):
    """Raised when there is a problem with the user's configuration."""

    pass


class ScraperAuthenticationError(CampSchedError):
    """Raised when the scraper fails to log in to the university website."""

    pass


class GoogleAPIError(CampSchedError):
    """Raised when there is an error communicating with the Google Calendar API."""

    pass
