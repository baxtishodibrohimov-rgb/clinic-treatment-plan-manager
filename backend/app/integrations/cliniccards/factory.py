from app.config import Settings, get_settings
from app.integrations.cliniccards.base import CliniccardsAdapter
from app.integrations.cliniccards.http_provider import HttpCliniccardsAdapter
from app.integrations.cliniccards.mock_provider import MockCliniccardsAdapter


def get_cliniccards_adapter(settings: Settings | None = None) -> CliniccardsAdapter:
    """Returns the Cliniccards adapter to use. Real credentials
    (CLINICCARDS_API_URL + CLINICCARDS_API_KEY) switch this to the HTTP
    adapter automatically. Set CLINICCARDS_MODE=mock to force mock data even
    if credentials are present (useful for demos/staging)."""
    settings = settings or get_settings()
    has_creds = bool(settings.cliniccards_api_url and settings.cliniccards_api_key)
    if settings.cliniccards_mode == "mock" or not has_creds:
        return MockCliniccardsAdapter()
    return HttpCliniccardsAdapter(settings)
