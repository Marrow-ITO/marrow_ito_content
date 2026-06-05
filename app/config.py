import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db: str
    flask_host: str
    flask_port: int
    flask_debug: bool


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


settings = Settings(
    mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
    mongo_db=os.getenv("MONGO_DB", "marrow_ito_search"),
    flask_host=os.getenv("FLASK_HOST", "0.0.0.0"),
    flask_port=int(os.getenv("FLASK_PORT", "5001")),
    flask_debug=_env_bool("FLASK_DEBUG", True),
)
