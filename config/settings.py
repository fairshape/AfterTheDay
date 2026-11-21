import re
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore", hide_input_in_errors=True)

    bot_token: SecretStr = SecretStr("")
    webapp_url: str = ""
    bot_username: str = ""
    anniversary_sticker_id: str = ""
    assembly_sticker_id: str = ""
    welcome_sticker_id: str = ""
    first_save_sticker_id: str = ""
    demo_mode: bool = False
    voice_directory: Path = ROOT / "var" / "voices"
    voice_one_model: str = Field(default="ru_RU-irina-medium", pattern=r"^[a-zA-Z0-9_-]+$")
    voice_two_model: str = Field(default="ru_RU-denis-medium", pattern=r"^[a-zA-Z0-9_-]+$")
    speech_timeout: float = Field(default=75, gt=0, le=180)
    music_storefront: str = Field(default="KZ", pattern=r"^[A-Z]{2}$")
    catalogue_timeout: float = Field(default=4, gt=0, le=10)
    app_timezone: str = "Asia/Almaty"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    data_dir: Path = Path("var")
    auto_migrate: bool = True

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (KeyError, ValueError) as exc:
            raise ValueError("APP_TIMEZONE must be an IANA timezone") from exc
        return value

    @field_validator("bot_token")
    @classmethod
    def validate_token(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() and not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", value.get_secret_value()):
            raise ValueError("BOT_TOKEN must be the token issued by BotFather")
        return value

    @field_validator("bot_username")
    @classmethod
    def validate_bot_username(cls, value: str) -> str:
        value = value.strip().removeprefix("@")
        if value and not re.fullmatch(r"[A-Za-z0-9_]{5,32}", value):
            raise ValueError("BOT_USERNAME must be a Telegram username")
        return value

    @field_validator("webapp_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if value:
            parsed = urlsplit(value)
            port = parsed.port
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                    or (port is not None and port == 0) or any(character.isspace() for character in value)
                    or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
                raise ValueError("WEBAPP_URL must be a public HTTPS origin such as https://journal.example.com")
        return value.rstrip("/")

    @property
    def private_enabled(self) -> bool:
        return not self.demo_mode and bool(self.bot_token.get_secret_value() and self.webapp_url)

    @property
    def storage(self) -> Path:
        return ROOT / self.data_dir / ("private" if self.private_enabled else "demo")
