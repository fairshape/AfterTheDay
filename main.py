import logging

import uvicorn
from pydantic import ValidationError

from app.infrastructure.audio.speech import PiperSpeech
from app.infrastructure.db.database import open_database
from app.infrastructure.media.storage import MediaStore
from app.services.diary import Diary
from app.services.narration import Narration
from app.web.application import create_app
from config.settings import ROOT, Settings
from demo.seed import populate

logger = logging.getLogger("after_the_day")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # A transport exception can contain a bot API URL. Application logs use error types.
    logging.getLogger("aiogram").setLevel(logging.CRITICAL)
    try:
        settings = Settings()
    except ValidationError as exc:
        for error in exc.errors(include_input=False, include_context=False, include_url=False):
            logger.error("Check %s in .env. %s", error["loc"][0].upper(), error["msg"])
        raise SystemExit(2) from None

    sessions = open_database(settings.storage, settings.auto_migrate or not settings.private_enabled)
    media = MediaStore(settings.storage / "media")
    speech = PiperSpeech(ROOT / settings.voice_directory,
                        {"irina": settings.voice_one_model, "denis": settings.voice_two_model},
                        settings.speech_timeout)
    diary = Diary(sessions, media, settings.app_timezone, Narration(media, speech))
    if not settings.private_enabled:
        if settings.demo_mode:
            logger.info("DEMO_MODE=true. Starting the fictional web-only diary.")
        else:
            if not settings.bot_token.get_secret_value():
                logger.info("Set BOT_TOKEN in .env to the token issued by BotFather to enable Telegram.")
            if not settings.webapp_url:
                logger.info("Set WEBAPP_URL in .env to the public HTTPS origin of this service to enable Telegram.")
            logger.info("Starting the fictional web-only diary.")
        populate(diary)
    uvicorn.run(create_app(settings, diary), host=settings.host, port=settings.port, access_log=False)


if __name__ == "__main__":
    main()
