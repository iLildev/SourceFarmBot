import os
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
_raw_db_url: str = os.environ.get("DATABASE_URL", "")

LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")


def _build_async_db_url(url: str) -> tuple[str, dict]:
    """Convert any postgres:// URL to postgresql+asyncpg:// and strip sslmode."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    ssl_mode = params.pop("sslmode", ["disable"])[0]

    connect_args: dict = {}
    if ssl_mode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True

    new_query = urlencode({k: v[0] for k, v in params.items()})
    clean = parsed._replace(query=new_query)
    return urlunparse(clean), connect_args


DATABASE_URL, DB_CONNECT_ARGS = _build_async_db_url(_raw_db_url)
